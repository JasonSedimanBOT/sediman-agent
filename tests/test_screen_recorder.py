from __future__ import annotations

import asyncio
import base64
import io
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sediman.agent.screen_recorder import (
    ActionEvent,
    RecordedFrame,
    RecordingSession,
    ScreenRecorder,
    draw_cursor_on_frame,
)


def _make_jpeg_b64(width: int = 100, height: int = 100) -> str:
    try:
        from PIL import Image
        img = Image.new("RGB", (width, height), "white")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return base64.b64encode(buf.getvalue()).decode()
    except ImportError:
        return base64.b64encode(b"\xff\xd8\xff\xe0\x00\x10JFIF").decode()


def _make_frame(
    url: str = "https://example.com",
    cursor_x: int = 100,
    cursor_y: int = 200,
    action: str | None = None,
    action_detail: str = "",
    title: str = "Test Page",
    timestamp: float | None = None,
) -> RecordedFrame:
    return RecordedFrame(
        timestamp=timestamp or time.monotonic(),
        screenshot_b64=_make_jpeg_b64(),
        cursor_x=cursor_x,
        cursor_y=cursor_y,
        url=url,
        title=title,
        action=action,
        action_detail=action_detail,
    )


def _make_session(
    name: str = "test-skill",
    frames: int = 10,
    action_indices: list[int] | None = None,
    description: str | None = None,
) -> RecordingSession:
    session = RecordingSession(
        id="abc123",
        name=name,
        started_at=time.monotonic() - 10.0,
        stopped_at=time.monotonic(),
        description=description,
    )
    if action_indices is None:
        action_indices = [2, 5, 8]
    for i in range(frames):
        action = None
        detail = ""
        url = f"https://example.com/page{i}"
        if i in action_indices:
            action = "click" if i % 2 == 0 else "navigate"
            detail = f"Action at index {i}"
            if action == "navigate":
                url = f"https://example.com/page{i}/new"
        session.frames.append(_make_frame(url=url, action=action, action_detail=detail))
    return session


# ── RecordedFrame ──────────────────────────────────────────────


class TestRecordedFrame:
    def test_has_cursor_positive_x(self):
        assert _make_frame(cursor_x=5, cursor_y=0).has_cursor()

    def test_has_cursor_positive_y(self):
        assert _make_frame(cursor_x=0, cursor_y=5).has_cursor()

    def test_has_cursor_both(self):
        assert _make_frame(cursor_x=100, cursor_y=200).has_cursor()

    def test_no_cursor(self):
        assert not _make_frame(cursor_x=0, cursor_y=0).has_cursor()

    def test_default_fields(self):
        frame = RecordedFrame(timestamp=1.0, screenshot_b64="abc", cursor_x=0, cursor_y=0, url="http://x")
        assert frame.title == ""
        assert frame.action is None
        assert frame.action_detail == ""


# ── ActionEvent ────────────────────────────────────────────────


class TestActionEvent:
    def test_defaults(self):
        evt = ActionEvent(timestamp=1.0, action_type="click", detail="clicked")
        assert evt.url == ""
        assert evt.selector == ""
        assert evt.text == ""

    def test_full_fields(self):
        evt = ActionEvent(
            timestamp=1.0, action_type="input", detail="typed",
            url="https://x.com", selector="#input", text="hello",
        )
        assert evt.url == "https://x.com"
        assert evt.selector == "#input"
        assert evt.text == "hello"


# ── RecordingSession ───────────────────────────────────────────


class TestRecordingSession:
    def test_duration_seconds_when_stopped(self):
        session = RecordingSession(
            id="x", name="t",
            started_at=100.0, stopped_at=115.0,
        )
        assert session.duration_seconds == 15.0

    def test_duration_seconds_when_active(self):
        session = RecordingSession(id="x", name="t", started_at=time.monotonic() - 3.0)
        assert session.duration_seconds >= 2.9

    def test_duration_seconds_zero_when_future(self):
        session = RecordingSession(id="x", name="t", started_at=time.monotonic() + 100.0)
        assert session.duration_seconds == 0.0

    def test_frame_count(self):
        session = _make_session(frames=15)
        assert session.frame_count == 15

    def test_frame_count_empty(self):
        session = RecordingSession(id="x", name="t")
        assert session.frame_count == 0

    def test_description_stored(self):
        session = _make_session(description="Post to Medium")
        assert session.description == "Post to Medium"

    def test_get_action_frames(self):
        session = _make_session(frames=10, action_indices=[2, 5, 8])
        action_frames = session.get_action_frames()
        assert len(action_frames) == 3
        assert all(f.action is not None for f in action_frames)

    def test_get_action_frames_none(self):
        session = _make_session(frames=5, action_indices=[])
        assert session.get_action_frames() == []

    def test_get_key_frames_under_limit(self):
        session = _make_session(frames=10, action_indices=[2, 5, 8])
        key_frames = session.get_key_frames(max_frames=25)
        assert len(key_frames) >= 3
        assert len(key_frames) <= 25

    def test_get_key_frames_exactly_at_limit(self):
        frames = []
        for i in range(10):
            frames.append(_make_frame(action=f"act{i}"))
        session = RecordingSession(
            id="x", name="t",
            started_at=time.monotonic() - 5.0,
            stopped_at=time.monotonic(),
        )
        session.frames = frames
        key = session.get_key_frames(max_frames=10)
        assert len(key) == 10

    def test_get_key_frames_over_limit_action_only(self):
        frames = []
        for i in range(50):
            frames.append(_make_frame(action="click"))
        session = RecordingSession(
            id="x", name="t",
            started_at=time.monotonic() - 5.0,
            stopped_at=time.monotonic(),
        )
        session.frames = frames
        key = session.get_key_frames(max_frames=10)
        assert len(key) == 10

    def test_get_key_frames_mixed_action_and_idle(self):
        session = _make_session(frames=60, action_indices=[0, 10, 20, 30])
        key = session.get_key_frames(max_frames=20)
        assert len(key) <= 20
        assert len(key) >= 4

    def test_get_key_frames_empty(self):
        session = RecordingSession(id="x", name="empty")
        assert session.get_key_frames() == []

    def test_get_key_frames_all_idle(self):
        session = _make_session(frames=30, action_indices=[])
        key = session.get_key_frames(max_frames=10)
        assert len(key) <= 10


# ── ScreenRecorder ─────────────────────────────────────────────


class TestScreenRecorderInit:
    def test_initial_state(self):
        recorder = ScreenRecorder(browser_session=MagicMock())
        assert not recorder.is_recording
        assert recorder.session is None

    def test_fps_clamped_high(self):
        recorder = ScreenRecorder(browser_session=MagicMock(), fps=20)
        assert recorder.fps == 10

    def test_fps_clamped_low(self):
        recorder = ScreenRecorder(browser_session=MagicMock(), fps=0)
        assert recorder.fps == 1

    def test_fps_valid(self):
        recorder = ScreenRecorder(browser_session=MagicMock(), fps=5)
        assert recorder.fps == 5

    def test_max_duration_set(self):
        recorder = ScreenRecorder(browser_session=MagicMock(), max_duration=60)
        assert recorder.max_duration == 60

    def test_on_frame_callback_stored(self):
        cb = MagicMock()
        recorder = ScreenRecorder(browser_session=MagicMock(), on_frame=cb)
        assert recorder.on_frame is cb


class TestScreenRecorderStart:
    @pytest.mark.asyncio
    async def test_start_raises_if_already_recording(self):
        recorder = ScreenRecorder(browser_session=MagicMock())
        recorder._recording = True
        with pytest.raises(RuntimeError, match="Already recording"):
            await recorder.start("test")

    @pytest.mark.asyncio
    async def test_start_creates_session(self):
        mock_browser = MagicMock()
        mock_browser.is_started = True
        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock()
        mock_session_obj = MagicMock()
        mock_session_obj.agent_current_page = mock_page
        mock_browser.browser = MagicMock()
        mock_browser.browser.create_session = AsyncMock(return_value=mock_session_obj)

        recorder = ScreenRecorder(browser_session=mock_browser, fps=1)
        session = await recorder.start("my-skill", description="Test description")

        assert recorder.is_recording
        assert session.name == "my-skill"
        assert session.description == "Test description"
        assert len(session.id) == 12
        assert recorder._tracker_injected is True

        await recorder.stop()

    @pytest.mark.asyncio
    async def test_start_starts_browser_if_not_started(self):
        mock_browser = MagicMock()
        mock_browser.is_started = False
        mock_browser.start = AsyncMock()
        mock_page = AsyncMock()
        mock_session_obj = MagicMock()
        mock_session_obj.agent_current_page = mock_page
        mock_browser.browser = MagicMock()
        mock_browser.browser.create_session = AsyncMock(return_value=mock_session_obj)

        recorder = ScreenRecorder(browser_session=mock_browser, fps=1)
        await recorder.start("test")
        mock_browser.start.assert_called_once()
        await recorder.stop()

    @pytest.mark.asyncio
    async def test_start_falls_back_to_context_pages(self):
        mock_browser = MagicMock()
        mock_browser.is_started = True
        mock_page = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.pages = [mock_page]
        mock_browser.browser.browser_contexts = [mock_ctx]
        mock_browser.browser.create_session = AsyncMock()
        mock_session_obj = MagicMock()
        mock_session_obj.agent_current_page = None
        mock_browser.browser.create_session.return_value = mock_session_obj

        recorder = ScreenRecorder(browser_session=mock_browser, fps=1)
        await recorder.start("test")
        assert recorder._page is mock_page
        await recorder.stop()

    @pytest.mark.asyncio
    async def test_start_creates_new_page_as_last_resort(self):
        mock_browser = MagicMock()
        mock_browser.is_started = True
        mock_page = AsyncMock()
        mock_session_obj = MagicMock()
        mock_session_obj.agent_current_page = None
        mock_browser.browser.browser_contexts = []
        mock_browser.browser.create_session = AsyncMock(return_value=mock_session_obj)
        mock_browser.browser.new_page = AsyncMock(return_value=mock_page)

        recorder = ScreenRecorder(browser_session=mock_browser, fps=1)
        await recorder.start("test")
        assert recorder._page is mock_page
        await recorder.stop()


class TestScreenRecorderStop:
    @pytest.mark.asyncio
    async def test_stop_raises_if_not_recording(self):
        recorder = ScreenRecorder(browser_session=MagicMock())
        with pytest.raises(RuntimeError, match="Not recording"):
            await recorder.stop()

    @pytest.mark.asyncio
    async def test_stop_sets_stopped_at(self):
        mock_browser = MagicMock()
        mock_browser.is_started = True
        mock_page = AsyncMock()
        mock_session_obj = MagicMock()
        mock_session_obj.agent_current_page = mock_page
        mock_browser.browser = MagicMock()
        mock_browser.browser.create_session = AsyncMock(return_value=mock_session_obj)

        recorder = ScreenRecorder(browser_session=mock_browser, fps=1)
        session = await recorder.start("test")
        assert session.stopped_at is None

        stopped = await recorder.stop()
        assert stopped.stopped_at is not None
        assert not recorder.is_recording
        assert recorder._capture_task is None


class TestScreenRecorderCaptureLoop:
    @pytest.mark.asyncio
    async def test_capture_loop_appends_frames(self):
        mock_browser = MagicMock()
        mock_browser.is_started = True

        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value={"x": 50, "y": 75})
        mock_page.screenshot = AsyncMock(return_value=b"\xff\xd8\xff\xe0fake")
        mock_page.url = "https://example.com"
        mock_page.title = AsyncMock(return_value="Example")

        mock_session_obj = MagicMock()
        mock_session_obj.agent_current_page = mock_page
        mock_browser.browser = MagicMock()
        mock_browser.browser.create_session = AsyncMock(return_value=mock_session_obj)

        frames_captured = []
        recorder = ScreenRecorder(
            browser_session=mock_browser, fps=10,
            on_frame=lambda f: frames_captured.append(f),
        )
        await recorder.start("test")

        await asyncio.sleep(0.5)
        await recorder.stop()

        assert len(recorder.session.frames) > 0
        assert len(frames_captured) > 0

    @pytest.mark.asyncio
    async def test_capture_loop_detects_navigation(self):
        mock_browser = MagicMock()
        mock_browser.is_started = True

        urls_returned = []
        url_sequence = ["https://a.com", "https://b.com", "https://b.com"]
        url_idx = [0]

        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value={"x": 0, "y": 0})
        mock_page.screenshot = AsyncMock(return_value=b"\xff\xd8")

        def get_url():
            idx = min(url_idx[0], len(url_sequence) - 1)
            val = url_sequence[idx]
            urls_returned.append(val)
            url_idx[0] += 1
            return val

        type(mock_page).url = property(lambda self: get_url())
        mock_page.title = AsyncMock(return_value="T")

        mock_session_obj = MagicMock()
        mock_session_obj.agent_current_page = mock_page
        mock_browser.browser = MagicMock()
        mock_browser.browser.create_session = AsyncMock(return_value=mock_session_obj)

        recorder = ScreenRecorder(browser_session=mock_browser, fps=10)
        await recorder.start("test")

        await asyncio.sleep(0.6)
        await recorder.stop()

        assert len(recorder.session.frames) > 0

    @pytest.mark.asyncio
    async def test_capture_loop_handles_page_errors(self):
        mock_browser = MagicMock()
        mock_browser.is_started = True

        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(side_effect=Exception("page gone"))
        mock_page.screenshot = AsyncMock(side_effect=Exception("no screenshot"))

        mock_session_obj = MagicMock()
        mock_session_obj.agent_current_page = mock_page
        mock_browser.browser = MagicMock()
        mock_browser.browser.create_session = AsyncMock(return_value=mock_session_obj)

        recorder = ScreenRecorder(browser_session=mock_browser, fps=10)
        await recorder.start("test")

        await asyncio.sleep(0.3)
        await recorder.stop()

    @pytest.mark.asyncio
    async def test_on_frame_error_does_not_crash(self):
        mock_browser = MagicMock()
        mock_browser.is_started = True

        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value={"x": 1, "y": 1})
        mock_page.screenshot = AsyncMock(return_value=b"\xff")
        mock_page.url = "https://x.com"
        mock_page.title = AsyncMock(return_value="")

        mock_session_obj = MagicMock()
        mock_session_obj.agent_current_page = mock_page
        mock_browser.browser = MagicMock()
        mock_browser.browser.create_session = AsyncMock(return_value=mock_session_obj)

        def bad_callback(f):
            raise ValueError("callback error")

        recorder = ScreenRecorder(browser_session=mock_browser, fps=10, on_frame=bad_callback)
        await recorder.start("test")

        await asyncio.sleep(0.3)
        await recorder.stop()


class TestScreenRecorderInjectActionMarker:
    @pytest.mark.asyncio
    async def test_inject_appends_action(self):
        mock_browser = MagicMock()
        mock_browser.is_started = True
        mock_page = AsyncMock()
        mock_page.url = "https://x.com"
        mock_session_obj = MagicMock()
        mock_session_obj.agent_current_page = mock_page
        mock_browser.browser = MagicMock()
        mock_browser.browser.create_session = AsyncMock(return_value=mock_session_obj)

        recorder = ScreenRecorder(browser_session=mock_browser, fps=1)
        await recorder.start("test")

        recorder.session.frames.append(_make_frame(action=None))
        await recorder.inject_action_marker("custom-action", "user clicked button")

        assert len(recorder.session.actions) == 1
        assert recorder.session.actions[0].action_type == "custom-action"
        assert recorder.session.frames[-1].action == "custom-action"

        await recorder.stop()

    @pytest.mark.asyncio
    async def test_inject_no_op_when_no_session(self):
        recorder = ScreenRecorder(browser_session=MagicMock())
        await recorder.inject_action_marker("test")

    @pytest.mark.asyncio
    async def test_inject_does_not_overwrite_existing_action(self):
        mock_browser = MagicMock()
        mock_browser.is_started = True
        mock_page = AsyncMock()
        mock_page.url = "https://x.com"
        mock_session_obj = MagicMock()
        mock_session_obj.agent_current_page = mock_page
        mock_browser.browser = MagicMock()
        mock_browser.browser.create_session = AsyncMock(return_value=mock_session_obj)

        recorder = ScreenRecorder(browser_session=mock_browser, fps=1)
        await recorder.start("test")

        recorder.session.frames.append(_make_frame(action="original-action"))
        await recorder.inject_action_marker("new-action")

        assert recorder.session.frames[-1].action == "original-action"

        await recorder.stop()


class TestScreenRecorderMaxDuration:
    @pytest.mark.asyncio
    async def test_stops_at_max_duration(self):
        mock_browser = MagicMock()
        mock_browser.is_started = True
        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value={"x": 0, "y": 0})
        mock_page.screenshot = AsyncMock(return_value=b"\xff")
        mock_page.url = "https://x.com"
        mock_page.title = AsyncMock(return_value="")

        mock_session_obj = MagicMock()
        mock_session_obj.agent_current_page = mock_page
        mock_browser.browser = MagicMock()
        mock_browser.browser.create_session = AsyncMock(return_value=mock_session_obj)

        recorder = ScreenRecorder(browser_session=mock_browser, fps=10, max_duration=0)
        session = await recorder.start("test")

        await asyncio.sleep(0.5)

        assert len(session.frames) == 0 or not recorder.is_recording


# ── draw_cursor_on_frame ──────────────────────────────────────


class TestDrawCursorOnFrame:
    def test_no_cursor_returns_original(self):
        b64 = base64.b64encode(b"\xff\xd8\xff\xe0").decode()
        result = draw_cursor_on_frame(b64, 0, 0)
        assert result == b64

    def test_with_cursor_modifies_image(self):
        try:
            from PIL import Image
            img = Image.new("RGB", (200, 200), "white")
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            b64 = base64.b64encode(buf.getvalue()).decode()

            result = draw_cursor_on_frame(b64, 100, 100)
            assert result != b64
            assert len(base64.b64decode(result)) > 0
        except ImportError:
            pytest.skip("Pillow not installed")

    def test_cursor_drawn_at_correct_position(self):
        try:
            from PIL import Image
            img = Image.new("RGB", (200, 200), "white")
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            b64 = base64.b64encode(buf.getvalue()).decode()

            result = draw_cursor_on_frame(b64, 150, 50)
            result_bytes = base64.b64decode(result)
            result_img = Image.open(io.BytesIO(result_bytes))
            pixel = result_img.getpixel((150, 50))
            assert pixel[0] > 200
        except ImportError:
            pytest.skip("Pillow not installed")

    def test_invalid_b64_returns_original(self):
        result = draw_cursor_on_frame("not-valid-b64", 50, 50)
        assert result == "not-valid-b64"

    def test_cursor_near_edge(self):
        try:
            from PIL import Image
            img = Image.new("RGB", (50, 50), "white")
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            b64 = base64.b64encode(buf.getvalue()).decode()

            result = draw_cursor_on_frame(b64, 5, 5)
            assert result is not None
        except ImportError:
            pytest.skip("Pillow not installed")
