from __future__ import annotations

import json
from typing import Any

import structlog

from sediman.agent.prompts.builder import _load_template
from sediman.agent.screen_recorder import (
    RecordedFrame,
    RecordingSession,
    draw_cursor_on_frame,
)
from sediman.llm.provider import LLMProvider

logger = structlog.get_logger()


class TraceToSkill:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def convert(
        self,
        session: RecordingSession,
        max_frames: int = 25,
    ) -> dict[str, Any] | None:
        if len(session.frames) < 3:
            logger.debug("trace_too_short", frames=len(session.frames))
            return None

        key_frames = session.get_key_frames(max_frames=max_frames)
        if not key_frames:
            return None

        system_prompt = _load_template("trace_to_skill.md")
        if not system_prompt:
            logger.warning("trace_to_skill_template_missing")
            return None

        user_message = self._build_user_message(session, key_frames)

        messages = [
            {"role": "system", "content": system_prompt},
            user_message,
        ]

        try:
            response = await self.llm.chat(messages=messages, tools=[])
            if not response.text:
                return None

            return self._parse_response(response.text)
        except Exception as e:
            logger.warning("trace_to_skill_failed", error=str(e))
            return None

    def _build_user_message(
        self,
        session: RecordingSession,
        key_frames: list[RecordedFrame],
    ) -> dict[str, Any]:
        content_parts: list[dict[str, Any]] = []

        header = (
            f"Screen Recording: \"{session.name}\"\n"
            f"Duration: {session.duration_seconds:.1f}s\n"
            f"Total frames captured: {session.frame_count}\n"
            f"Actions detected: {len(session.actions)}\n"
        )

        if session.description:
            header += f"User-provided description: {session.description}\n"

        header += "\n--- Frame Sequence ---\n\n"

        content_parts.append({"type": "text", "text": header})

        for i, frame in enumerate(key_frames, 1):
            elapsed = frame.timestamp - session.started_at

            frame_text = f"\n[Frame {i}] t={elapsed:.1f}s"
            frame_text += f"\nURL: {frame.url or '(no URL)'}"
            if frame.title:
                frame_text += f"\nPage title: {frame.title}"
            if frame.has_cursor():
                frame_text += f"\nCursor position: ({frame.cursor_x}, {frame.cursor_y})"
            if frame.action:
                frame_text += f"\nAction: {frame.action}"
                if frame.action_detail:
                    frame_text += f" — {frame.action_detail}"
            frame_text += "\nScreenshot:\n"

            content_parts.append({"type": "text", "text": frame_text})

            frame_b64 = draw_cursor_on_frame(
                frame.screenshot_b64, frame.cursor_x, frame.cursor_y
            )

            content_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{frame_b64}",
                    "detail": "low",
                },
            })

        content_parts.append({
            "type": "text",
            "text": "\n--- End of Recording ---\n\n"
            "Analyze the recording above and extract a reusable skill.",
        })

        return {"role": "user", "content": content_parts}

    def _parse_response(self, text: str) -> dict[str, Any] | None:
        text = text.strip()

        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        text = text.strip()

        if not text.startswith("{"):
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                text = text[start : end + 1]
            else:
                return None

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.debug("trace_to_skill_json_parse_failed", text=text[:200])
            return None

        if not isinstance(data, dict):
            return None

        if not data.get("should_learn"):
            reason = data.get("reason", "Not worth learning")
            logger.info("trace_to_skill_skipped", reason=reason)
            return None

        required = ["skill_name", "description", "steps"]
        for field in required:
            if field not in data:
                logger.debug("trace_to_skill_missing_field", field=field)
                return None

        if not isinstance(data["steps"], list) or len(data["steps"]) < 2:
            logger.debug("trace_to_skill_too_few_steps")
            return None

        return data
