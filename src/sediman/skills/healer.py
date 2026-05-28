from __future__ import annotations

from typing import Any

import structlog

from sediman.agent.prompts.builder import PromptBuilder
from sediman.browser.session import BrowserSession, run_browser_task
from sediman.llm.provider import LLMProvider
from sediman.skills.engine import SkillEngine

logger = structlog.get_logger()


async def heal_skill(
    skill: dict[str, Any],
    error_context: str,
    browser_session: BrowserSession,
    llm: LLMProvider,
) -> dict[str, Any] | None:
    name = skill["name"]
    steps = skill.get("steps", [])

    logger.info("skill_healing_start", skill=name)

    healer_system = PromptBuilder.get_healer_prompt()

    steps_text = "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))

    messages = [
        {
            "role": "system",
            "content": healer_system,
        },
        {
            "role": "user",
            "content": f"""Skill name: "{name}"

Original steps:
{steps_text}

Error context:
{error_context}

Please analyze the failure and provide updated steps.""",
        },
    ]

    try:
        response = await llm.chat(messages=messages, tools=[])
        if not response.text:
            logger.warning("heal_no_response", skill=name)
            return None

        import json

        text = response.text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        data = json.loads(text.strip())

        if "error" in data:
            logger.warning("heal_unfixable", skill=name, reason=data.get("error", data.get("reasoning", "unknown")))
            return None

        new_steps = data.get("steps", [])
        if not new_steps:
            logger.warning("heal_empty_steps", skill=name)
            return None

        confidence = data.get("confidence", "medium")
        reasoning = data.get("reasoning", "unknown")

        engine = SkillEngine()
        patched = engine.patch(name, {"steps": new_steps})

        if patched:
            logger.info(
                "skill_healed",
                skill=name,
                old_version=skill.get("version", 1),
                new_version=patched["version"],
                confidence=confidence,
                reason=reasoning,
            )

        return patched

    except Exception as e:
        logger.warning("heal_failed", skill=name, error=str(e))
        return None
