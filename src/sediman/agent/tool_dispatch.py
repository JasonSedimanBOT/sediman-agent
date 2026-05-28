from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

import structlog

from sediman.llm.provider import LLMProvider, LLMResponse, ToolDefinition

logger = structlog.get_logger()


@dataclass
class ToolResult:
    success: bool
    output: str
    data: dict[str, Any] | None = None


ToolHandler = Callable[..., Awaitable[ToolResult]]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, ToolHandler] = {}

    def register(
        self,
        definition: ToolDefinition,
        handler: ToolHandler,
    ) -> None:
        self._tools[definition.name] = definition
        self._handlers[definition.name] = handler

    def get_definitions(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def get_openai_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self._tools.values()
        ]

    async def dispatch(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        handler = self._handlers.get(tool_name)
        if not handler:
            return ToolResult(success=False, output=f"Unknown tool: {tool_name}")
        try:
            result = await handler(**arguments)
            logger.info("tool_dispatched", tool=tool_name, success=result.success)
            return result
        except Exception as e:
            logger.warning("tool_dispatch_failed", tool=tool_name, error=str(e))
            return ToolResult(success=False, output=f"Tool error: {e}")

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def get_definition(self, name: str) -> ToolDefinition:
        return self._tools[name]


class ToolLoop:
    def __init__(self, llm: LLMProvider, registry: ToolRegistry, max_rounds: int = 10):
        self.llm = llm
        self.registry = registry
        self.max_rounds = max_rounds

    async def run(
        self,
        messages: list[dict[str, Any]],
        system: str | None = None,
        on_tool_call: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> LLMResponse:
        all_messages: list[dict[str, Any]] = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        tools = self.registry.get_openai_tools()

        for _round in range(self.max_rounds):
            response = await self.llm.chat(
                messages=all_messages,
                tools=self.registry.get_definitions(),
            )

            if not response.tool_calls:
                return response

            all_messages.append({
                "role": "assistant",
                "content": response.text or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in response.tool_calls
                ],
            })

            for tc in response.tool_calls:
                if on_tool_call:
                    on_tool_call(tc.name, tc.arguments)

                result = await self.registry.dispatch(tc.name, tc.arguments)

                all_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result.output,
                })

        return response
