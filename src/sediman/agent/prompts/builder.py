from __future__ import annotations

from pathlib import Path

import structlog

logger = structlog.get_logger()

TEMPLATES_DIR = Path(__file__).parent / "templates"

SOUL_FILE = Path.home() / ".sediman" / "SOUL.md"
CONTEXT_FILE = Path.home() / ".sediman" / "CONTEXT.md"


def _load_template(name: str) -> str:
    path = TEMPLATES_DIR / name
    if path.exists():
        return path.read_text()
    logger.warning("template_not_found", name=name)
    return ""


def load_soul() -> str:
    if SOUL_FILE.exists():
        return SOUL_FILE.read_text()
    return _load_template("identity.md")


def load_project_context() -> str:
    if CONTEXT_FILE.exists():
        return CONTEXT_FILE.read_text()
    agents_md = Path.cwd() / "AGENTS.md"
    if agents_md.exists():
        return agents_md.read_text()
    return ""


class PromptBuilder:
    def __init__(
        self,
        flash_mode: bool = False,
        soul_override: str | None = None,
        project_context: str | None = None,
    ):
        self.flash_mode = flash_mode
        self._soul_override = soul_override
        self._project_context = project_context
        self._template_name = "system_flash.md" if flash_mode else "system_full.md"

    def build_system_prompt(
        self,
        skill_summaries: str | None = None,
        memory_context: str | None = None,
    ) -> str:
        sections: list[str] = []

        template = _load_template(self._template_name)
        sections.append(template)

        soul = self._soul_override or load_soul()
        if soul.strip():
            sections.append(f"<persona>\n{soul.strip()}\n</persona>")

        if memory_context and memory_context.strip():
            sections.append(memory_context.strip())

        ctx = self._project_context or load_project_context()
        if ctx.strip():
            sections.append(f"<project_context>\n{ctx.strip()}\n</project_context>")

        if skill_summaries and skill_summaries.strip():
            sections.append(f"<available_skills>\n{skill_summaries.strip()}\n</available_skills>")

        return "\n\n".join(sections)

    def build_skill_executor_prompt(
        self,
        skill_name: str,
        description: str,
        steps: list[str],
        verification: str | None = None,
    ) -> str:
        template = _load_template("skill_executor.md")
        steps_text = "\n".join(f"{i}. {step}" for i, step in enumerate(steps, 1))
        return template.format(
            skill_name=skill_name,
            description=description,
            steps=steps_text,
            verification=verification or "The expected outcome described in the skill was achieved.",
        )

    @staticmethod
    def get_healer_prompt() -> str:
        return _load_template("healer.md")

    @staticmethod
    def get_skill_eval_prompt() -> str:
        return _load_template("skill_eval.md")
