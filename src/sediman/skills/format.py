from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SkillData:
    name: str
    description: str
    steps: list[str] = field(default_factory=list)
    category: str = "general"
    version: int = 1
    variables: list[str] = field(default_factory=list)
    schedule: str | None = None
    author: str | None = None
    license: str | None = None
    compatibility: str | None = None
    source: str = "local"
    created_at: str | None = None
    updated_at: str | None = None
    body: str = ""
    when_to_use: str | None = None
    pitfalls: list[str] = field(default_factory=list)
    use_count: int = 0
    last_used_at: str | None = None
    verification: str | None = None

    def to_json(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "steps": self.steps,
            "category": self.category,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.variables:
            d["variables"] = self.variables
        if self.schedule:
            d["schedule"] = self.schedule
        if self.author:
            d["author"] = self.author
        if self.source != "local":
            d["source"] = self.source
        if self.when_to_use:
            d["when_to_use"] = self.when_to_use
        if self.pitfalls:
            d["pitfalls"] = self.pitfalls
        if self.use_count > 0:
            d["use_count"] = self.use_count
        if self.last_used_at:
            d["last_used_at"] = self.last_used_at
        if self.verification:
            d["verification"] = self.verification
        return d

    def to_skill_md(self) -> str:
        lines = ["---"]
        lines.append(f"name: {self.name}")
        lines.append(f"description: \"{self.description}\"")
        if self.license:
            lines.append(f"license: {self.license}")
        if self.compatibility:
            lines.append(f"compatibility: {self.compatibility}")
        meta_parts = []
        if self.category != "general":
            meta_parts.append(f"  category: {self.category}")
        if self.author:
            meta_parts.append(f"  author: {self.author}")
        if self.version != 1:
            meta_parts.append(f"  version: \"{self.version}\"")
        if self.variables:
            meta_parts.append(f"  variables: {json.dumps(self.variables)}")
        if self.schedule:
            meta_parts.append(f"  schedule: \"{self.schedule}\"")
        if self.source != "local":
            meta_parts.append(f"  source: {self.source}")
        if meta_parts:
            lines.append("metadata:")
            lines.extend(meta_parts)
        lines.append("---")
        lines.append("")
        lines.append(f"# {self.name}")
        lines.append("")
        lines.append(self.description)
        if self.steps:
            lines.append("")
            lines.append("## Steps")
            for i, step in enumerate(self.steps, 1):
                lines.append(f"{i}. {step}")
        if self.variables:
            lines.append("")
            lines.append("## Variables")
            for var in self.variables:
                lines.append(f"- `{var}`")
        if self.schedule:
            lines.append("")
            lines.append(f"## Schedule")
            lines.append(f"Recommended: `{self.schedule}`")
        if self.when_to_use:
            lines.append("")
            lines.append("## When to Use")
            lines.append(self.when_to_use)
        if self.pitfalls:
            lines.append("")
            lines.append("## Pitfalls")
            for pitfall in self.pitfalls:
                lines.append(f"- {pitfall}")
        if self.verification:
            lines.append("")
            lines.append("## Verification")
            lines.append(self.verification)
        return "\n".join(lines) + "\n"


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)", re.DOTALL)


def parse_skill_md(content: str) -> SkillData | None:
    m = _FRONTMATTER_RE.match(content)
    if not m:
        return None

    frontmatter_text = m.group(1)
    body = m.group(2).strip()

    try:
        import yaml
        meta = yaml.safe_load(frontmatter_text)
    except ImportError:
        meta = _parse_simple_yaml(frontmatter_text)

    if not isinstance(meta, dict) or "name" not in meta or "description" not in meta:
        return None

    metadata = meta.get("metadata", {}) or {}

    category = meta.get("category") or metadata.get("category", "general")
    version = meta.get("version") or metadata.get("version", 1)
    variables = meta.get("variables") or metadata.get("variables", [])
    if isinstance(variables, str):
        try:
            variables = json.loads(variables)
        except json.JSONDecodeError:
            variables = [v.strip() for v in variables.split(",")]
    schedule = meta.get("schedule") or metadata.get("schedule")
    author = meta.get("author") or metadata.get("author")
    source = meta.get("source") or metadata.get("source", "local")

    return SkillData(
        name=meta["name"],
        description=meta["description"],
        steps=_extract_steps_from_body(body),
        category=category,
        version=int(version) if version else 1,
        variables=variables or [],
        schedule=str(schedule) if schedule else None,
        author=author,
        license=meta.get("license"),
        compatibility=meta.get("compatibility"),
        source=source,
        body=body,
    )


def parse_skill_json(content: str) -> SkillData | None:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict) or "name" not in data or "description" not in data:
        return None

    return SkillData(
        name=data["name"],
        description=data["description"],
        steps=data.get("steps", []),
        category=data.get("category", "general"),
        version=data.get("version", 1),
        variables=data.get("variables", []),
        schedule=data.get("schedule"),
        author=data.get("author"),
        source=data.get("source", "local"),
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
        when_to_use=data.get("when_to_use"),
        pitfalls=data.get("pitfalls", []),
        use_count=data.get("use_count", 0),
        last_used_at=data.get("last_used_at"),
        verification=data.get("verification"),
    )


def load_skill(skill_dir: Path) -> SkillData | None:
    skill_json = skill_dir / "skill.json"
    if skill_json.exists():
        parsed = parse_skill_json(skill_json.read_text())
        if parsed:
            if not parsed.created_at:
                import os
                stat = skill_json.stat()
                from datetime import datetime, timezone
                parsed.created_at = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat()
            return parsed

    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        parsed = parse_skill_md(skill_md.read_text())
        if parsed:
            if not parsed.created_at:
                import os
                stat = skill_md.stat()
                from datetime import datetime, timezone
                parsed.created_at = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat()
            return parsed

    return None


def _extract_steps_from_body(body: str) -> list[str]:
    steps = []
    for line in body.split("\n"):
        stripped = line.strip()
        m = re.match(r"^\d+\.\s+(.+)", stripped)
        if m:
            steps.append(m.group(1))
    return steps


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    current_key: str | None = None
    current_indent = 0

    for line in text.split("\n"):
        stripped = line.rstrip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())

        if indent == 0 and ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()
            if val:
                result[key] = _yaml_value(val)
            else:
                result[key] = {}
                current_key = key
                current_indent = 0
        elif current_key and indent > 0:
            stripped_inner = stripped.lstrip()
            if ":" in stripped_inner and not stripped_inner.startswith("-"):
                key, _, val = stripped_inner.partition(":")
                key = key.strip()
                val = val.strip()
                if isinstance(result.get(current_key), dict):
                    result[current_key][key] = _yaml_value(val)

    return result


def _yaml_value(val: str) -> Any:
    if val.startswith('"') and val.endswith('"'):
        return val[1:-1]
    if val.startswith("'") and val.endswith("'"):
        return val[1:-1]
    if val.startswith("["):
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            return val
    if val.lower() == "true":
        return True
    if val.lower() == "false":
        return False
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val
