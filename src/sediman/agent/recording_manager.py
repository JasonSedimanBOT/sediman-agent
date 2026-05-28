from __future__ import annotations

from typing import Any

import structlog

from sediman.agent.screen_recorder import RecordingSession, ScreenRecorder
from sediman.browser.session import BrowserSession

logger = structlog.get_logger()


class RecordingManager:
    _instance: RecordingManager | None = None

    def __init__(self) -> None:
        self._recorders: dict[str, ScreenRecorder] = {}
        self._sessions: dict[str, RecordingSession] = {}

    @classmethod
    def get_instance(cls) -> RecordingManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start_recording(
        self,
        name: str,
        browser: BrowserSession,
        description: str | None = None,
        fps: int = 3,
        max_duration: int = 300,
        on_frame: Any | None = None,
    ) -> RecordingSession:
        if name in self._recorders and self._recorders[name].is_recording:
            raise ValueError(f"Already recording '{name}'. Stop it first.")

        recorder = ScreenRecorder(
            browser_session=browser,
            fps=fps,
            max_duration=max_duration,
            on_frame=on_frame,
        )

        session = await recorder.start(name=name, description=description)

        self._recorders[name] = recorder
        self._sessions[session.id] = session

        logger.info("recording_manager_started", name=name, session_id=session.id)
        return session

    async def stop_recording(self, name: str) -> RecordingSession:
        recorder = self._recorders.get(name)
        if not recorder or not recorder.is_recording:
            raise ValueError(f"No active recording for '{name}'.")

        session = await recorder.stop()
        self._sessions[session.id] = session

        logger.info(
            "recording_manager_stopped",
            name=name,
            session_id=session.id,
            frames=session.frame_count,
        )
        return session

    async def stop_by_session_id(self, session_id: str) -> RecordingSession:
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session '{session_id}' not found.")

        recorder = self._recorders.get(session.name)
        if not recorder or not recorder.is_recording:
            raise ValueError(f"No active recorder for session '{session_id}'.")

        return await self.stop_recording(session.name)

    def get_session(self, session_id: str) -> RecordingSession | None:
        return self._sessions.get(session_id)

    def get_active_sessions(self) -> list[RecordingSession]:
        active = []
        for recorder in self._recorders.values():
            if recorder.is_recording and recorder.session:
                active.append(recorder.session)
        return active

    def is_recording(self, name: str | None = None) -> bool:
        if name:
            recorder = self._recorders.get(name)
            return recorder is not None and recorder.is_recording
        return any(r.is_recording for r in self._recorders.values())

    def get_recorder(self, name: str) -> ScreenRecorder | None:
        return self._recorders.get(name)

    def cleanup(self, name: str) -> None:
        self._recorders.pop(name, None)
