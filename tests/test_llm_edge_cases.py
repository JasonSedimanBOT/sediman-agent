"""Edge-case tests for llm/provider.py — failover, provider config, API key resolution."""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sediman.llm.provider import (
    LLMResponse,
    ToolCall,
    ToolDefinition,
    LLMProvider,
    OpenAICompatibleProvider,
    create_provider,
    PROVIDERS,
)


class TestLLMResponseEdgeCases:
    def test_text_none_with_tool_calls(self):
        resp = LLMResponse(
            text=None,
            tool_calls=[ToolCall(id="1", name="f", arguments={})],
        )
        assert resp.has_tool_calls is True
        assert resp.text is None

    def test_empty_tool_calls_list(self):
        resp = LLMResponse(text="hello", tool_calls=[])
        assert resp.has_tool_calls is False

    def test_multiple_tool_calls(self):
        resp = LLMResponse(tool_calls=[
            ToolCall(id="1", name="f1", arguments={"a": 1}),
            ToolCall(id="2", name="f2", arguments={"b": 2}),
        ])
        assert resp.has_tool_calls is True
        assert len(resp.tool_calls) == 2

    def test_done_true_explicitly(self):
        resp = LLMResponse(text="finished", done=True)
        assert resp.done is True


class TestToolCallEdgeCases:
    def test_complex_arguments(self):
        tc = ToolCall(
            id="1",
            name="create_skill",
            arguments={
                "name": "my-skill",
                "description": "A complex skill",
                "steps": ["step 1", "step 2", "step 3"],
            },
        )
        assert len(tc.arguments["steps"]) == 3

    def test_empty_arguments(self):
        tc = ToolCall(id="1", name="f", arguments={})
        assert tc.arguments == {}


class TestCreateProviderEdgeCases:
    def test_api_key_from_env(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-123"}):
            provider = create_provider("openai")
        assert provider.api_key == "sk-test-123"

    def test_api_key_parameter_overrides_env(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "from-env"}):
            provider = create_provider("openai", api_key="from-param")
        assert provider.api_key == "from-param"

    def test_ollama_no_api_key_needed(self):
        provider = create_provider("ollama")
        # Ollama uses placeholder key
        assert provider.api_key is not None

    def test_custom_model_with_custom_base_url(self):
        provider = create_provider(
            "openai",
            model="gpt-4o-mini",
            base_url="https://api.custom.com/v1",
        )
        assert provider.model == "gpt-4o-mini"
        assert provider.base_url == "https://api.custom.com/v1"

    def test_provider_registry_immutable(self):
        # PROVIDERS should have expected keys
        assert "openai" in PROVIDERS
        assert "ollama" in PROVIDERS
        assert PROVIDERS["openai"]["model"] == "gpt-4o"
        assert PROVIDERS["ollama"]["model"] == "qwen3"

    def test_unknown_provider_error_message(self):
        with pytest.raises(ValueError) as exc_info:
            create_provider("anthropic")
        assert "Unknown provider" in str(exc_info.value)
        assert "openai" in str(exc_info.value)
        assert "ollama" in str(exc_info.value)

    def test_base_url_none_when_not_specified_openai(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test"}):
            provider = create_provider("openai")
        assert provider.base_url is None


class TestLLMProviderAbstract:
    def test_abstract_cannot_instantiate(self):
        with pytest.raises(TypeError):
            LLMProvider()

    def test_subclass_must_implement_chat(self):
        class IncompleteProvider(LLMProvider):
            pass

        with pytest.raises(TypeError):
            IncompleteProvider()


class TestOpenAICompatibleProviderInit:
    def test_default_model(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test"}):
            provider = OpenAICompatibleProvider()
        assert provider.model == "gpt-4o"

    def test_custom_model(self):
        provider = OpenAICompatibleProvider(model="gpt-3.5-turbo", api_key="test")
        assert provider.model == "gpt-3.5-turbo"

    def test_raises_when_no_env_and_no_base_url(self):
        with patch.dict("os.environ", {}, clear=True):
            os.environ.pop("OPENAI_API_KEY", None)
            with pytest.raises(ValueError, match="No API key"):
                OpenAICompatibleProvider()


class TestLLMResponseDoneLogic:
    def test_done_true_no_tool_calls(self):
        resp = LLMResponse(text="hello", done=True)
        assert resp.done is True

    def test_done_false_default(self):
        resp = LLMResponse()
        assert resp.done is False

    def test_done_true_with_text(self):
        resp = LLMResponse(text="response", done=True)
        assert resp.done is True
        assert resp.text == "response"


class TestChatWithFailover:
    @pytest.mark.asyncio
    async def test_fails_over_on_error(self):
        primary = MagicMock(spec=LLMProvider)
        primary.chat = AsyncMock(side_effect=RuntimeError("primary down"))

        fallback = MagicMock(spec=LLMProvider)
        fallback.chat = AsyncMock(return_value=LLMResponse(text="from fallback"))

        provider = OpenAICompatibleProvider(api_key="test")
        result = await provider.chat_with_failover(
            messages=[{"role": "user", "content": "test"}],
            tools=[],
            fallback_provider=fallback,
        )

        assert result.text == "from fallback"
        fallback.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_when_no_fallback(self):
        provider = OpenAICompatibleProvider(api_key="test")
        provider.chat = AsyncMock(side_effect=RuntimeError("fail"))

        with pytest.raises(RuntimeError, match="fail"):
            await provider.chat_with_failover(
                messages=[{"role": "user", "content": "test"}],
                tools=[],
                fallback_provider=None,
            )

    @pytest.mark.asyncio
    async def test_no_failover_on_success(self):
        fallback = MagicMock(spec=LLMProvider)
        fallback.chat = AsyncMock(return_value=LLMResponse(text="fallback"))

        provider = OpenAICompatibleProvider(api_key="test")
        provider.chat = AsyncMock(return_value=LLMResponse(text="primary"))

        result = await provider.chat_with_failover(
            messages=[{"role": "user", "content": "test"}],
            tools=[],
            fallback_provider=fallback,
        )

        assert result.text == "primary"
        fallback.chat.assert_not_called()
