from __future__ import annotations

from typing import Any

import structlog

from sediman.agent.prompts.builder import PromptBuilder
from sediman.browser.session import BrowserSession, run_browser_task
from sediman.errors import looks_like_error
from sediman.llm.provider import LLMProvider
from sediman.skills.healer import heal_skill

logger = structlog.get_logger()


def _looks_like_error(text: str) -> bool:
    return looks_like_error(text)


async def execute_skill(
    skill: dict[str, Any],
    browser_session: BrowserSession,
    llm: LLMProvider,
    max_retries: int = 1,
    flash_mode: bool = True,
) -> str:
    name = skill["name"]
    description = skill.get("description", "")
    steps = skill.get("steps", [])
    verification = skill.get("verification")

    builder = PromptBuilder(flash_mode=flash_mode)
    task = builder.build_skill_executor_prompt(
        skill_name=name,
        description=description,
        steps=steps,
        verification=verification,
    )

    logger.info("skill_execution_start", skill=name)

    for attempt in range(max_retries + 1):
        try:
            result_text, _actions = await run_browser_task(
                task=task,
                browser_session=browser_session,
                llm=llm.get_browser_use_llm(),
                flash_mode=flash_mode,
            )

            if result_text and not _looks_like_error(result_text):
                logger.info("skill_execution_done", skill=name, attempt=attempt)
                return result_text

            if attempt < max_retries:
                logger.info("skill_retry_with_healing", skill=name, attempt=attempt)
                healed = await heal_skill(
                    skill=skill,
                    error_context=result_text or "unknown error",
                    browser_session=browser_session,
                    llm=llm,
                )
                if healed:
                    skill = healed
                    steps = skill.get("steps", [])
                    task = builder.build_skill_executor_prompt(
                        skill_name=name,
                        description=description,
                        steps=steps,
                    )
                    continue

            return result_text or "Skill execution completed with no output"

        except Exception as e:
            if attempt < max_retries:
                logger.info("skill_error_retry", skill=name, error=str(e))
                healed = await heal_skill(
                    skill=skill,
                    error_context=str(e),
                    browser_session=browser_session,
                    llm=llm,
                )
                if healed:
                    skill = healed
                    continue

            logger.error("skill_execution_failed", skill=name, error=str(e))
            return f"Skill '{name}' failed: {e}"
