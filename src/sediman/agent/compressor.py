from __future__ import annotations

from typing import Any

import structlog

from sediman.agent.prompts.builder import _load_template

logger = structlog.get_logger()

COMPRESS_THRESHOLD = 20
PROTECT_TAIL = 10
PROTECT_HEAD = 2


class ContextCompressor:
    def __init__(self, llm: Any):
        self._llm = llm
        self._previous_summary: str | None = None

    def should_compress(self, messages: list[dict[str, str]]) -> bool:
        return len(messages) >= COMPRESS_THRESHOLD * 2

    async def compress(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        if len(messages) <= PROTECT_HEAD + PROTECT_TAIL * 2:
            return messages

        head = messages[:PROTECT_HEAD]
        tail = messages[-(PROTECT_TAIL * 2):]
        middle = messages[PROTECT_HEAD:-(PROTECT_TAIL * 2)]

        if not middle:
            return messages

        summary_text = await self._generate_summary(middle)
        if summary_text is None:
            cut = messages[-(COMPRESS_THRESHOLD * 2):]
            logger.info("context_compressed_no_summary", removed=len(middle), kept=len(cut))
            return cut

        summary_msg = {
            "role": "system",
            "content": f"[CONTEXT COMPACTION] Earlier conversation was summarized:\n\n{summary_text}",
        }

        self._previous_summary = summary_text
        compressed = head + [summary_msg] + tail
        logger.info(
            "context_compressed",
            before=len(messages),
            after=len(compressed),
            middle_removed=len(middle),
        )
        return compressed

    async def _generate_summary(self, messages: list[dict[str, str]]) -> str | None:
        from sediman.utils import format_conversation_context
        conversation_text = format_conversation_context(messages, limit=len(messages), max_chars=500)
        system_prompt = _load_template("compression.md")

        if self._previous_summary:
            user_prompt = (
                "Update the following summary with new information from the conversation below. "
                "Keep the same format. Add new progress, update in-progress items, remove completed items.\n\n"
                f"Previous summary:\n{self._previous_summary}\n\n"
                f"New conversation:\n{conversation_text}"
            )
        else:
            user_prompt = f"Conversation to summarize:\n\n{conversation_text}"

        try:
            response = await self._llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                tools=[],
            )
            if response.text:
                return response.text.strip()
        except Exception as e:
            logger.debug("compression_summary_failed", error=str(e))

        return None
