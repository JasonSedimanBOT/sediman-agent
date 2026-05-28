from __future__ import annotations

from typing import Any

import structlog

from sediman.agent.manager import ManagerPlan

logger = structlog.get_logger()


class SkillRecorder:
    def should_record(
        self,
        task: str,
        plan: ManagerPlan,
        browser_actions: list[dict[str, Any]],
    ) -> bool:
        if not plan.skill_name:
            return False
        if len(browser_actions) < 2:
            return False
        return True

    def record(
        self,
        task: str,
        plan: ManagerPlan,
        browser_result: str,
        browser_actions: list[dict[str, Any]],
    ) -> str | None:
        if not self.should_record(task, plan, browser_actions):
            return None

        from sediman.skills.engine import SkillEngine
        engine = SkillEngine()

        existing = engine.read(plan.skill_name)
        if existing:
            logger.debug("skill_already_exists", name=plan.skill_name)
            return None

        steps = self._build_steps(task, plan, browser_actions)

        description = plan.skill_description or task[:100]
        engine.create(
            name=plan.skill_name,
            description=description,
            steps=steps,
            category="auto-recorded",
        )

        logger.info(
            "skill_recorded",
            name=plan.skill_name,
            steps=len(steps),
            source="recorder",
        )
        return plan.skill_name

    def _build_steps(
        self,
        task: str,
        plan: ManagerPlan,
        browser_actions: list[dict[str, Any]],
    ) -> list[str]:
        steps = []

        if plan.browser_task and plan.browser_task != task:
            steps.append(f"Task: {plan.browser_task}")

        for action in browser_actions:
            action_type = self._summarize_action(action)
            if action_type:
                steps.append(action_type)

        if plan.schedule:
            steps.append(
                f"Schedule: {plan.schedule.cron} — {plan.schedule.task}"
            )

        return steps if steps else [task[:200]]

    def _summarize_action(self, action: dict[str, Any]) -> str | None:
        action_name = action.get("action", "")
        if not action_name:
            action_name = action.get("type", "")

        if not action_name:
            return None

        if action_name == "navigate":
            url = action.get("url", action.get("arguments", {}).get("url", ""))
            return f"Navigate to {url}" if url else "Navigate to URL"

        if action_name == "click":
            idx = action.get("index", action.get("arguments", {}).get("index", ""))
            return f"Click element {idx}" if idx else "Click element"

        if action_name == "input":
            text = action.get("text", action.get("arguments", {}).get("text", ""))
            return f"Type: {text[:50]}" if text else "Type text"

        if action_name == "extract":
            return "Extract data from page"

        if action_name == "scroll":
            return "Scroll page"

        if action_name == "search":
            query = action.get("query", action.get("arguments", {}).get("query", ""))
            return f"Search: {query}" if query else "Search"

        if action_name == "done":
            return None

        return str(action)[:100]
