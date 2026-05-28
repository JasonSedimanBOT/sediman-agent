from __future__ import annotations

import asyncio
import base64
import io
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

import structlog

logger = structlog.get_logger()

_MOUSE_TRACKER_JS = """
(window.__sediman_cursor = {x: 0, y: 0, ts: 0});
document.addEventListener('mousemove', function(e) {
    window.__sediman_cursor = {x: e.clientX, y: e.clientY, ts: Date.now()};
});
document.addEventListener('click', function(e) {
    window.__sediman_cursor = {x: e.clientX, y: e.clientY, ts: Date.now()};
});
"""

_GET_CURSOR_JS = """
(() => {
    try { return window.__sediman_cursor || {x: 0, y: 0}; }
    catch(e) { return {x: 0, y: 0}; }
})()
"""

_SCROLL_TRACKER_JS = """
document.addEventListener('scroll', function(e) {
    if (!window.__sediman_scroll_events) window.__sediman_scroll_events = [];
    window.__sediman_scroll_events.push({
        x: window.scrollX,
        y: window.scrollY,
        ts: Date.now()
    });
    if (window.__sediman_scroll_events.length > 100) {
        window.__sediman_scroll_events = window.__sediman_scroll_events.slice(-50);
    }
});
"""

_CURSOR_OVERLAY_JS = """
(cursorX, cursorY) => {
    const el = document.getElementById('__sediman_cursor_dot');
    if (el) el.remove();
    if (cursorX === 0 && cursorY === 0) return;
    const dot = document.createElement('div');
    dot.id = '__sediman_cursor_dot';
    dot.style.cssText = `
        position: fixed;
        left: ${cursorX}px;
        top: ${cursorY}px;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background: rgba(255, 0, 0, 0.6);
        border: 3px solid rgba(255, 255, 255, 0.9);
        transform: translate(-50%, -50%);
        pointer-events: none;
        z-index: 2147483647;
        box-shadow: 0 0 8px rgba(255,0,0,0.8);
    `;
    document.body.appendChild(dot);
}
"""

_REMOVE_OVERLAY_JS = """
(() => {
    const el = document.getElementById('__sediman_cursor_dot');
    if (el) el.remove();
})()
"""


@dataclass
class RecordedFrame:
    timestamp: float
    screenshot_b64: str
    cursor_x: int
    cursor_y: int
    url: str
    title: str = ""
    action: str | None = None
    action_detail: str = ""

    def has_cursor(self) -> bool:
        return self.cursor_x > 0 or self.cursor_y > 0


@dataclass
class ActionEvent:
    timestamp: float
    action_type: str
    detail: str
    url: str = ""
    selector: str = ""
    text: str = ""


@dataclass
class RecordingSession:
    id: str
    name: str
    frames: list[RecordedFrame] = field(default_factory=list)
    actions: list[ActionEvent] = field(default_factory=list)
    started_at: float = 0.0
    stopped_at: float | None = None
    description: str | None = None

    @property
    def duration_seconds(self) -> float:
        end = self.stopped_at or time.monotonic()
        return max(0.0, end - self.started_at)

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    def get_action_frames(self) -> list[RecordedFrame]:
        return [f for f in self.frames if f.action is not None]

    def get_key_frames(self, max_frames: int = 25) -> list[RecordedFrame]:
        action_frames = self.get_action_frames()
        action_indices = {id(f) for f in action_frames}

        if len(action_frames) >= max_frames:
            step = len(action_frames) / max_frames
            return [action_frames[int(i * step)] for i in range(max_frames)]

        idle_frames = [f for f in self.frames if id(f) not in action_indices]
        remaining = max_frames - len(action_frames)

        sampled_idle: list[RecordedFrame] = []
        if idle_frames and remaining > 0:
            step = max(1, len(idle_frames) // remaining)
            for i in range(0, len(idle_frames), step):
                if len(sampled_idle) < remaining:
                    sampled_idle.append(idle_frames[i])

        result = []
        action_idx = 0
        idle_idx = 0
        for f in self.frames:
            if id(f) in action_indices:
                result.append(f)
            elif idle_idx < len(sampled_idle) and id(f) == id(sampled_idle[idle_idx]):
                result.append(f)
                idle_idx += 1
            if len(result) >= max_frames:
                break

        return result[:max_frames]


class ScreenRecorder:
    FPS = 3
    MAX_DURATION_SECONDS = 300

    def __init__(
        self,
        browser_session: Any,
        fps: int = 3,
        max_duration: int = 300,
        on_frame: Callable[[RecordedFrame], None] | None = None,
    ):
        self.browser = browser_session
        self.fps = min(max(fps, 1), 10)
        self.max_duration = max_duration
        self.on_frame = on_frame
        self._session: RecordingSession | None = None
        self._recording = False
        self._capture_task: asyncio.Task | None = None
        self._page: Any = None
        self._tracker_injected = False

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def session(self) -> RecordingSession | None:
        return self._session

    async def start(self, name: str, description: str | None = None) -> RecordingSession:
        if self._recording:
            raise RuntimeError("Already recording. Stop the current session first.")

        if not self.browser.is_started:
            await self.browser.start()

        browser = self.browser.browser
        session = await browser.create_session()
        self._page = session.agent_current_page

        if not self._page:
            contexts = browser.browser_contexts if hasattr(browser, 'browser_contexts') else []
            if contexts:
                ctx = contexts[0]
                pages = ctx.pages if hasattr(ctx, 'pages') else []
                if pages:
                    self._page = pages[-1]

        if not self._page:
            self._page = await browser.new_page()

        self._session = RecordingSession(
            id=str(uuid.uuid4())[:12],
            name=name,
            started_at=time.monotonic(),
            description=description,
        )

        await self._inject_trackers()

        self._recording = True
        self._capture_task = asyncio.create_task(self._capture_loop())

        logger.info(
            "screen_recording_started",
            session_id=self._session.id,
            name=name,
            fps=self.fps,
        )
        return self._session

    async def stop(self) -> RecordingSession:
        if not self._recording or not self._session:
            raise RuntimeError("Not recording.")

        self._recording = False

        if self._capture_task:
            self._capture_task.cancel()
            try:
                await self._capture_task
            except asyncio.CancelledError:
                pass
            self._capture_task = None

        await self._remove_overlay()

        self._session.stopped_at = time.monotonic()

        logger.info(
            "screen_recording_stopped",
            session_id=self._session.id,
            frames=len(self._session.frames),
            actions=len(self._session.actions),
            duration=self._session.duration_seconds,
        )
        return self._session

    async def _inject_trackers(self) -> None:
        if not self._page:
            return
        try:
            await self._page.evaluate(_MOUSE_TRACKER_JS)
            await self._page.evaluate(_SCROLL_TRACKER_JS)
            self._tracker_injected = True
        except Exception as e:
            logger.debug("tracker_inject_failed", error=str(e))

    async def _remove_overlay(self) -> None:
        if not self._page:
            return
        try:
            await self._page.evaluate(_REMOVE_OVERLAY_JS)
        except Exception:
            pass

    async def _capture_loop(self) -> None:
        interval = 1.0 / self.fps
        last_url = ""

        while self._recording:
            try:
                start = time.monotonic()

                if self._session and self._session.duration_seconds > self.max_duration:
                    logger.info("recording_max_duration_reached", max=self.max_duration)
                    break

                frame = await self._capture_frame(last_url)
                if frame and self._session:
                    self._session.frames.append(frame)
                    last_url = frame.url

                    if frame.action:
                        self._session.actions.append(ActionEvent(
                            timestamp=frame.timestamp,
                            action_type=frame.action,
                            detail=frame.action_detail,
                            url=frame.url,
                        ))

                    if self.on_frame:
                        try:
                            self.on_frame(frame)
                        except Exception:
                            pass

                elapsed = time.monotonic() - start
                sleep_time = max(0.0, interval - elapsed)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug("capture_frame_error", error=str(e))
                await asyncio.sleep(interval)

    async def _capture_frame(self, last_url: str) -> RecordedFrame | None:
        if not self._page:
            return None

        try:
            cursor = {"x": 0, "y": 0}
            try:
                cursor = await self._page.evaluate(_GET_CURSOR_JS)
            except Exception:
                pass

            try:
                await self._page.evaluate(
                    f"({_CURSOR_OVERLAY_JS})({cursor.get('x', 0)}, {cursor.get('y', 0)})"
                )
            except Exception:
                pass

            screenshot_bytes = await self._page.screenshot(type="jpeg", quality=60)
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

            try:
                await self._page.evaluate(_REMOVE_OVERLAY_JS)
            except Exception:
                pass

            url = ""
            try:
                url = self._page.url or ""
            except Exception:
                pass

            title = ""
            try:
                title = await self._page.title() or ""
            except Exception:
                pass

            action = None
            action_detail = ""
            if url != last_url and last_url:
                action = "navigate"
                action_detail = f"Navigated to {url[:100]}"

            return RecordedFrame(
                timestamp=time.monotonic(),
                screenshot_b64=screenshot_b64,
                cursor_x=int(cursor.get("x", 0)),
                cursor_y=int(cursor.get("y", 0)),
                url=url,
                title=title,
                action=action,
                action_detail=action_detail,
            )

        except Exception as e:
            logger.debug("frame_capture_failed", error=str(e))
            return None

    async def inject_action_marker(self, action_type: str, detail: str = "") -> None:
        if not self._session or not self._page:
            return

        self._session.actions.append(ActionEvent(
            timestamp=time.monotonic(),
            action_type=action_type,
            detail=detail,
            url=self._page.url if self._page else "",
        ))

        if self._session.frames:
            last_frame = self._session.frames[-1]
            if not last_frame.action:
                last_frame.action = action_type
                last_frame.action_detail = detail


def draw_cursor_on_frame(screenshot_b64: str, cursor_x: int, cursor_y: int) -> str:
    if cursor_x == 0 and cursor_y == 0:
        return screenshot_b64

    try:
        from PIL import Image, ImageDraw

        img_bytes = base64.b64decode(screenshot_b64)
        img = Image.open(io.BytesIO(img_bytes))
        draw = ImageDraw.Draw(img)

        radius = 10
        bbox = [
            cursor_x - radius,
            cursor_y - radius,
            cursor_x + radius,
            cursor_y + radius,
        ]
        draw.ellipse(bbox, fill=(255, 50, 50, 180), outline=(255, 255, 255, 230), width=3)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=60)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except ImportError:
        return screenshot_b64
    except Exception:
        return screenshot_b64
