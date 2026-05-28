from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sediman.browser.session import extract_result, BrowserSession


class TestExtractResult:
    def test_returns_none_as_no_result(self):
        result = extract_result(None)
        assert "could not extract" in result

    def test_extracts_string_directly(self):
        assert extract_result("Hello world") == "Hello world"

    def test_extracts_from_object_with_final_result(self):
        raw = MagicMock()
        raw.final_result = "task done"
        result = extract_result(raw)
        assert isinstance(result, str)

    def test_extracts_from_all_results(self):
        raw = MagicMock(spec=[])
        raw.final_result = None
        r1 = MagicMock()
        r1.extracted_content = "content 1"
        r2 = MagicMock()
        r2.extracted_content = None
        r2.long_term_memory = "memory 2"
        raw.all_results = [r1, r2]

        result = extract_result(raw)
        assert "content 1" in result
        assert "memory 2" in result

    def test_extracts_from_all_model_outputs(self):
        raw = MagicMock(spec=[])
        raw.final_result = None
        raw.all_results = []
        raw.all_model_outputs = [{"action": "click"}]

        result = extract_result(raw)
        assert "click" in result

    def test_returns_no_result_when_nothing_found(self):
        raw = MagicMock(spec=[])
        raw.final_result = None
        raw.all_results = []
        raw.all_model_outputs = []

        result = extract_result(raw)
        assert "could not extract" in result

    def test_extracts_empty_string_as_no_result(self):
        result = extract_result("")
        assert "could not extract" in result


class TestBrowserSessionInit:
    def test_default_headless_false(self):
        session = BrowserSession()
        assert session.headless is False

    def test_headless_true(self):
        session = BrowserSession(headless=True)
        assert session.headless is True

    def test_custom_user_data_dir(self):
        session = BrowserSession(user_data_dir="/tmp/test-profile")
        assert session.user_data_dir == "/tmp/test-profile"

    def test_default_user_data_dir(self):
        session = BrowserSession()
        assert session.user_data_dir is not None
        assert "browser-profile" in session.user_data_dir

    def test_not_started_initially(self):
        session = BrowserSession()
        assert session._started is False

    def test_on_screenshot_callback(self):
        callback = MagicMock()
        session = BrowserSession(on_screenshot=callback)
        assert session.on_screenshot is callback

    def test_no_screenshot_callback_by_default(self):
        session = BrowserSession()
        assert session.on_screenshot is None

    def test_browser_is_none_initially(self):
        session = BrowserSession()
        assert session.browser is None


class TestBrowserSessionStop:
    @pytest.mark.asyncio
    async def test_stop_when_not_started(self):
        session = BrowserSession()
        # Should not raise
        await session.stop()

    @pytest.mark.asyncio
    async def test_stop_sets_started_false(self):
        session = BrowserSession()
        session._started = True
        # _browser must be truthy for stop to clear _started
        mock_browser = MagicMock()
        mock_browser.close = AsyncMock()
        session._browser = mock_browser
        await session.stop()
        assert session._started is False

    @pytest.mark.asyncio
    async def test_stop_clears_browser(self):
        session = BrowserSession()
        session._started = True
        session._browser = MagicMock()
        session._browser.close = AsyncMock()
        await session.stop()
        assert session._browser is None
        assert session._started is False

    @pytest.mark.asyncio
    async def test_stop_handles_close_exception(self):
        session = BrowserSession()
        session._started = True
        mock_browser = MagicMock()
        mock_browser.close = AsyncMock(side_effect=RuntimeError("close failed"))
        session._browser = mock_browser
        await session.stop()
        assert session._browser is None


class TestBrowserSessionScreenshot:
    @pytest.mark.asyncio
    async def test_screenshot_when_not_started(self):
        session = BrowserSession()
        result = await session.take_screenshot()
        assert result is None

    @pytest.mark.asyncio
    async def test_screenshot_handles_exception(self):
        session = BrowserSession()
        session._started = True
        mock_browser = MagicMock()
        mock_browser.create_session = AsyncMock(side_effect=RuntimeError("no session"))
        session._browser = mock_browser

        result = await session.take_screenshot()
        assert result is None
