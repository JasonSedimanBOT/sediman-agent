from __future__ import annotations

import json
from typing import Any

import structlog

from sediman.llm.provider import LLMProvider

logger = structlog.get_logger()


class SkillLearnerAgent:
    """Sub-agent that reviews task execution and extracts reusable skills.

    Hermes-style self-learning loop:
    - Front-end: browser agent can create skills via create_skill tool
    - Back-end: this agent reviews execution traces asynchronously
    - Only resets the iteration counter when a skill is actually created
    """

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def review_and_learn(
        self,
        task: str,
        browser_actions: list[dict[str, Any]],
        result: str,
        success: bool,
        existing_skills: list[dict[str, str]],
        conversation: list[dict[str, str]] | None = None,
    ) -> str | None:
        """Analyze execution, maybe create or patch a skill.

        Returns skill name if created/updated, None otherwise.
        """
        if not browser_actions or not result:
            return None

        from sediman.agent.prompts.builder import _load_template

        system_prompt = _load_template("skill_review.md")
        if not system_prompt:
            logger.debug("skill_review_template_missing")
            return None

        actions_text = self._format_actions(browser_actions)
        skills_text = self._format_skills(existing_skills)
        conversation_text = self._format_conversation(conversation) if conversation else ""

        user_content = (
            f"Task: {task}\n\n"
            f"Success: {'yes' if success else 'no'}\n\n"
            f"Browser actions taken:\n{actions_text}\n\n"
            f"Result:\n{result[:2000]}\n\n"
            f"Existing skills:\n{skills_text}"
        )
        if conversation_text:
            user_content += f"\n\nConversation history:\n{conversation_text}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        try:
            response = await self.llm.chat(messages=messages, tools=[])
            if not response.text:
                return None

            evaluation = self._parse_response(response.text)
            if not evaluation:
                return None

            if not evaluation.get("should_learn"):
                logger.debug("skill_review_nothing_to_save", task=task[:60])
                return None

            return await self._apply_evaluation(evaluation)

        except Exception as e:
            logger.warning("skill_learner_failed", error=str(e))
            return None

    def _format_actions(self, actions: list[dict[str, Any]]) -> str:
        lines = []
        for i, action in enumerate(actions, 1):
            action_type = action.get("action", action.get("type", "unknown"))
            detail = self._action_detail(action)
            lines.append(f"{i}. [{action_type}] {detail}")
        return "\n".join(lines) if lines else "No actions recorded"

    def _action_detail(self, action: dict[str, Any]) -> str:
        action_type = action.get("action", action.get("type", ""))
        args = action.get("arguments", action)

        if action_type == "navigate":
            url = args.get("url", "")
            return f"Navigate to {url}" if url else "Navigate"

        if action_type == "click":
            idx = args.get("index", "")
            text = args.get("text", args.get("label", ""))
            parts = []
            if idx:
                parts.append(f"element {idx}")
            if text:
                parts.append(f'"{text}"')
            return f"Click {' '.join(parts)}" if parts else "Click"

        if action_type == "input":
            text = args.get("text", "")
            field = args.get("selector", args.get("label", ""))
            parts = []
            if field:
                parts.append(f"in {field}")
            if text:
                parts.append(f'"{text[:50]}"')
            return f"Type {' '.join(parts)}" if parts else "Type text"

        if action_type == "extract":
            return "Extract data from page"

        if action_type == "scroll":
            direction = args.get("direction", "")
            return f"Scroll {direction}" if direction else "Scroll"

        if action_type == "search":
            query = args.get("query", "")
            return f"Search: {query}" if query else "Search"

        if action_type == "done":
            return "Task complete"

        return str(action)[:100]

    def _format_skills(self, skills: list[dict[str, str]]) -> str:
        if not skills:
            return "No existing skills."
        lines = [f"- {s['name']}: {s.get('description', '')}" for s in skills]
        return "\n".join(lines)

    def _format_conversation(self, conversation: list[dict[str, str]]) -> str:
        recent = conversation[-20:] if len(conversation) > 20 else conversation
        lines = []
        for msg in recent:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if content:
                lines.append(f"[{role}] {content[:300]}")
        return "\n".join(lines) if lines else "No conversation context."

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
            logger.debug("skill_learner_json_parse_failed", text=text[:200])
            return None

        if not isinstance(data, dict):
            return None

        if not data.get("should_learn"):
            return {"should_learn": False}

        required = ["skill_name", "description", "steps"]
        for field in required:
            if field not in data:
                logger.debug("skill_learner_missing_field", field=field)
                return None

        if not isinstance(data["steps"], list) or len(data["steps"]) < 2:
            return None

        return data

    async def _apply_evaluation(self, evaluation: dict[str, Any]) -> str | None:
        from sediman.skills.engine import SkillEngine
        from sediman.memory.security import scan_content

        engine = SkillEngine()
        name = evaluation["skill_name"]
        description = evaluation["description"]
        steps = evaluation["steps"]
        category = evaluation.get("category", "auto-learned")
        when_to_use = evaluation.get("when_to_use")
        pitfalls = evaluation.get("pitfalls", [])
        verification = evaluation.get("verification")

        all_text = f"{name} {description} {' '.join(steps)} {' '.join(pitfalls)}"
        threats = scan_content(all_text)
        if threats:
            logger.warning(
                "skill_rejected_security",
                name=name,
                threats=threats,
            )
            return None

        if evaluation.get("should_patch"):
            existing = engine.read(name)
            if existing:
                updates: dict[str, Any] = {
                    "description": description,
                    "steps": steps,
                }
                if when_to_use:
                    updates["when_to_use"] = when_to_use
                if pitfalls:
                    updates["pitfalls"] = pitfalls
                if verification:
                    updates["verification"] = verification
                patched = engine.patch(name, updates)
                if patched:
                    logger.info(
                        "skill_learned_patch",
                        name=name,
                        steps=len(steps),
                        new_version=patched.get("version"),
                    )
                    return name

        existing = engine.read(name)
        if existing:
            logger.debug("skill_already_exists", name=name)
            return None

        similar = engine.find_similar(name, description)
        if similar:
            logger.info(
                "skill_similar_found",
                new_name=name,
                similar_to=similar.get("name"),
                action="merging_into_similar",
            )
            updates = {
                "description": description,
                "steps": steps,
            }
            if when_to_use:
                updates["when_to_use"] = when_to_use
            if pitfalls:
                updates["pitfalls"] = pitfalls
            if verification:
                updates["verification"] = verification
            patched = engine.patch(similar["name"], updates)
            if patched:
                return similar["name"]

        engine.create(
            name=name,
            description=description,
            steps=steps,
            category=category,
            when_to_use=when_to_use,
            pitfalls=pitfalls,
            verification=verification,
        )
        logger.info(
            "skill_learned_create",
            name=name,
            steps=len(steps),
            category=category,
        )
        return name
