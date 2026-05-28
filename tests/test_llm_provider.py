from __future__ import annotations

from unittest.mock import patch

import pytest

from sediman.llm.provider import (
    LLMResponse,
    ToolCall,
    ToolDefinition,
    create_provider,
    PROVIDERS,
)


class TestLLMResponse:
    def test_has_tool_calls_true(self):
        resp = LLMResponse(tool_calls=[ToolCall(id="1", name="f", arguments={})])
        assert resp.has_tool_calls is True

    def test_has_tool_calls_false(self):
        resp = LLMResponse(text="hello")
        assert resp.has_tool_calls is False

    def test_done_default_false(self):
        resp = LLMResponse(text="done")
        assert resp.done is False

    def test_done_set_explicitly(self):
        resp = LLMResponse(text="done", done=True)
        assert resp.done is True

    def test_done_false_when_tool_calls(self):
        resp = LLMResponse(
            text="",
            tool_calls=[ToolCall(id="1", name="f", arguments={})],
        )
        assert resp.done is False

    def test_default_values(self):
        resp = LLMResponse()
        assert resp.text is None
        assert resp.tool_calls == []
        assert resp.done is False


class TestToolCall:
    def test_attributes(self):
        tc = ToolCall(id="abc", name="my_func", arguments={"x": 1})
        assert tc.id == "abc"
        assert tc.name == "my_func"
        assert tc.arguments == {"x": 1}


class TestToolDefinition:
    def test_attributes(self):
        td = ToolDefinition(name="t", description="desc", parameters={"type": "object"})
        assert td.name == "t"


class TestCreateProvider:
    def test_creates_openai_provider(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            provider = create_provider("openai")
        assert provider.model == "gpt-4o"

    def test_creates_ollama_provider(self):
        provider = create_provider("ollama")
        assert provider.model == "qwen3"
        assert provider.base_url == "http://localhost:11434/v1"

    def test_custom_model_overrides_default(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            provider = create_provider("openai", model="gpt-3.5-turbo")
        assert provider.model == "gpt-3.5-turbo"

    def test_custom_base_url_overrides_default(self):
        provider = create_provider("ollama", base_url="http://custom:1234/v1")
        assert provider.base_url == "http://custom:1234/v1"

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            create_provider("nonexistent")

    def test_providers_registry_has_openai_and_ollama(self):
        assert "openai" in PROVIDERS
        assert "ollama" in PROVIDERS
