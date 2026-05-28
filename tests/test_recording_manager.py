from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sediman.agent.recording_manager import RecordingManager
from sediman.agent.screen_recorder import (
    ActionEvent,
    RecordedFrame,
    RecordingSession,
    ScreenRecorder,
)


def _make_mock_browser():
    mock_browser = MagicMock()
    mock_browser.is_started = True
    mock_page = AsyncMock()
    mock_page.evaluate = AsyncMock(return_value={"x": 0, "y": 0})
    mock_page.screenshot = AsyncMock(return_value=b"\xff\xd8\xff")
    mock_page.url = "https://example.com"
    mock_page.title = AsyncMock(return_value="Test")
    mock_session_obj = MagicMock()
    mock_session_obj.agent_current_page = mock_page
    mock_browser.browser = MagicMock()
    mock_browser.browser.create_session = AsyncMock(return_value=mock_session_obj)
    return mock_browser


def _make_stopped_session(name: str = "test-skill") -> RecordingSession:
    session = RecordingSession(
        id="session-abc",
        name=name,
        started_at=time.monotonic() - 5.0,
        stopped_at=time.monotonic(),
    )
    session.frames.append(RecordedFrame(
        timestamp=time.monotonic(), screenshot_b64="abc",
        cursor_x=10, cursor_y=20, url="http://x",
    ))
    return session


# ── Singleton ──────────────────────────────────────────────────


class TestRecordingManagerSingleton:
    def setup_method(self):
        RecordingManager._instance = None

    def teardown_method(self):
        RecordingManager._instance = None

    def test_get_instance_creates(self):
        mgr = RecordingManager.get_instance()
        assert isinstance(mgr, RecordingManager)

    def test_get_instance_returns_same(self):
        mgr1 = RecordingManager.get_instance()
        mgr2 = RecordingManager.get_instance()
        assert mgr1 is mgr2

    def test_get_instance_after_manual_clear(self):
        mgr1 = RecordingManager.get_instance()
        RecordingManager._instance = None
        mgr2 = RecordingManager.get_instance()
        assert mgr1 is not mgr2


# ── start_recording() ──────────────────────────────────────────


class TestRecordingManagerStart:
    def setup_method(self):
        RecordingManager._instance = None

    def teardown_method(self):
        RecordingManager._instance = None

    @pytest.mark.asyncio
    async def test_start_creates_session(self):
        mgr = RecordingManager()
        mock_browser = _make_mock_browser()

        session = await mgr.start_recording("my-skill", mock_browser)
        assert session.name == "my-skill"
        assert session.id is not None
        assert mgr.is_recording("my-skill")

    @pytest.mark.asyncio
    async def test_start_with_description(self):
        mgr = RecordingManager()
        mock_browser = _make_mock_browser()

        session = await mgr.start_recording(
            "desc-skill", mock_browser, description="Post to Medium"
        )
        assert session.description == "Post to Medium"

    @pytest.mark.asyncio
    async def test_start_with_custom_fps(self):
        mgr = RecordingManager()
        mock_browser = _make_mock_browser()

        session = await mgr.start_recording("fps-skill", mock_browser, fps=5)
        recorder = mgr.get_recorder("fps-skill")
        assert recorder.fps == 5

    @pytest.mark.asyncio
    async def test_start_stores_session(self):
        mgr = RecordingManager()
        mock_browser = _make_mock_browser()

        session = await mgr.start_recording("store-test", mock_browser)
        assert mgr.get_session(session.id) is session

    @pytest.mark.asyncio
    async def test_start_duplicate_name_raises(self):
        mgr = RecordingManager()
        mock_browser = _make_mock_browser()

        await mgr.start_recording("dup", mock_browser)
        with pytest.raises(ValueError, match="Already recording"):
            await mgr.start_recording("dup", mock_browser)

        recorder = mgr.get_recorder("dup")
        await recorder.stop()

    @pytest.mark.asyncio
    async def test_start_multiple_different_names(self):
        mgr = RecordingManager()
        mock_browser1 = _make_mock_browser()
        mock_browser2 = _make_mock_browser()

        s1 = await mgr.start_recording("skill-a", mock_browser1)
        s2 = await mgr.start_recording("skill-b", mock_browser2)
        assert s1.name != s2.name
        assert mgr.is_recording("skill-a")
        assert mgr.is_recording("skill-b")

        r1 = mgr.get_recorder("skill-a")
        r2 = mgr.get_recorder("skill-b")
        await r1.stop()
        await r2.stop()


# ── stop_recording() ───────────────────────────────────────────


class TestRecordingManagerStop:
    def setup_method(self):
        RecordingManager._instance = None

    def teardown_method(self):
        RecordingManager._instance = None

    @pytest.mark.asyncio
    async def test_stop_returns_session(self):
        mgr = RecordingManager()
        mock_browser = _make_mock_browser()

        await mgr.start_recording("stop-test", mock_browser)
        session = await mgr.stop_recording("stop-test")

        assert session.name == "stop-test"
        assert session.stopped_at is not None
        assert not mgr.is_recording("stop-test")

    @pytest.mark.asyncio
    async def test_stop_unknown_name_raises(self):
        mgr = RecordingManager()
        with pytest.raises(ValueError, match="No active recording"):
            await mgr.stop_recording("nonexistent")

    @pytest.mark.asyncio
    async def test_stop_already_stopped_raises(self):
        mgr = RecordingManager()
        mock_browser = _make_mock_browser()

        await mgr.start_recording("stopped", mock_browser)
        await mgr.stop_recording("stopped")

        with pytest.raises(ValueError, match="No active recording"):
            await mgr.stop_recording("stopped")


# ── stop_by_session_id() ───────────────────────────────────────


class TestRecordingManagerStopBySessionId:
    def setup_method(self):
        RecordingManager._instance = None

    def teardown_method(self):
        RecordingManager._instance = None

    @pytest.mark.asyncio
    async def test_stop_by_session_id(self):
        mgr = RecordingManager()
        mock_browser = _make_mock_browser()

        session = await mgr.start_recording("sid-test", mock_browser)
        result = await mgr.stop_by_session_id(session.id)
        assert result.name == "sid-test"
        assert result.stopped_at is not None

    @pytest.mark.asyncio
    async def test_stop_unknown_session_id_raises(self):
        mgr = RecordingManager()
        with pytest.raises(ValueError, match="not found"):
            await mgr.stop_by_session_id("fake-id")


# ── get_active_sessions() ──────────────────────────────────────


class TestRecordingManagerActiveSessions:
    def setup_method(self):
        RecordingManager._instance = None

    def teardown_method(self):
        RecordingManager._instance = None

    @pytest.mark.asyncio
    async def test_no_active_sessions(self):
        mgr = RecordingManager()
        assert mgr.get_active_sessions() == []

    @pytest.mark.asyncio
    async def test_one_active_session(self):
        mgr = RecordingManager()
        mock_browser = _make_mock_browser()

        await mgr.start_recording("active", mock_browser)
        active = mgr.get_active_sessions()
        assert len(active) == 1
        assert active[0].name == "active"

        await mgr.stop_recording("active")

    @pytest.mark.asyncio
    async def test_stopped_not_in_active(self):
        mgr = RecordingManager()
        mock_browser = _make_mock_browser()

        await mgr.start_recording("stopped-active", mock_browser)
        await mgr.stop_recording("stopped-active")
        assert mgr.get_active_sessions() == []


# ── is_recording() ──────────────────────────────────────────────


class TestRecordingManagerIsRecording:
    def setup_method(self):
        RecordingManager._instance = None

    def teardown_method(self):
        RecordingManager._instance = None

    def test_not_recording_anything(self):
        mgr = RecordingManager()
        assert not mgr.is_recording()
        assert not mgr.is_recording("anything")

    @pytest.mark.asyncio
    async def test_recording_specific_name(self):
        mgr = RecordingManager()
        mock_browser = _make_mock_browser()

        await mgr.start_recording("specific", mock_browser)
        assert mgr.is_recording("specific")
        assert not mgr.is_recording("other")

        await mgr.stop_recording("specific")

    @pytest.mark.asyncio
    async def test_recording_any(self):
        mgr = RecordingManager()
        mock_browser = _make_mock_browser()

        await mgr.start_recording("any-test", mock_browser)
        assert mgr.is_recording()

        await mgr.stop_recording("any-test")


# ── get_recorder() ──────────────────────────────────────────────


class TestRecordingManagerGetRecorder:
    def setup_method(self):
        RecordingManager._instance = None

    def teardown_method(self):
        RecordingManager._instance = None

    @pytest.mark.asyncio
    async def test_get_existing_recorder(self):
        mgr = RecordingManager()
        mock_browser = _make_mock_browser()

        await mgr.start_recording("get-rec", mock_browser)
        recorder = mgr.get_recorder("get-rec")
        assert isinstance(recorder, ScreenRecorder)

        await mgr.stop_recording("get-rec")

    def test_get_nonexistent_recorder(self):
        mgr = RecordingManager()
        assert mgr.get_recorder("nothing") is None


# ── cleanup() ──────────────────────────────────────────────────


class TestRecordingManagerCleanup:
    def setup_method(self):
        RecordingManager._instance = None

    def teardown_method(self):
        RecordingManager._instance = None

    @pytest.mark.asyncio
    async def test_cleanup_removes_recorder(self):
        mgr = RecordingManager()
        mock_browser = _make_mock_browser()

        await mgr.start_recording("cleanup-test", mock_browser)
        await mgr.stop_recording("cleanup-test")

        assert mgr.get_recorder("cleanup-test") is not None
        mgr.cleanup("cleanup-test")
        assert mgr.get_recorder("cleanup-test") is None

    def test_cleanup_nonexistent_is_noop(self):
        mgr = RecordingManager()
        mgr.cleanup("nothing")

    @pytest.mark.asyncio
    async def test_session_still_accessible_after_cleanup(self):
        mgr = RecordingManager()
        mock_browser = _make_mock_browser()

        session = await mgr.start_recording("persist-test", mock_browser)
        await mgr.stop_recording("persist-test")
        mgr.cleanup("persist-test")

        assert mgr.get_session(session.id) is session
