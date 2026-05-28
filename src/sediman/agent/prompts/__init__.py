from sediman.agent.prompts.builder import PromptBuilder

__all__ = ["PromptBuilder", "build_system_prompt", "load_memory"]


def build_system_prompt(
    skill_summaries: str | None = None,
    memory_context: str | None = None,
) -> str:
    builder = PromptBuilder()
    return builder.build_system_prompt(
        skill_summaries=skill_summaries,
        memory_context=memory_context,
    )


def load_memory() -> str:
    from sediman.memory.prompt import load_memory as _load_memory
    return _load_memory()
