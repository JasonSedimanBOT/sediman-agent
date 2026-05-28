from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen, Request

import structlog

from sediman.skills.format import SkillData
from sediman.skills.validator import validate_skill

logger = structlog.get_logger()

DEFAULT_REGISTRY_URL = "https://raw.githubusercontent.com/sediman/skills-hub/main"

_HUB_CACHE: dict[str, Any] | None = None
_CACHE_KEY: str = ""
_CACHE_TS: float = 0.0
_CACHE_TTL: float = 300.0  # 5 minutes


@dataclass
class HubSkillSummary:
    name: str
    description: str
    category: str
    author: str | None = None
    version: int = 1
    installs: int = 0
    trust: str = "community"
    variables: list[str] | None = None
    schedule: str | None = None


class HubClient:
    def __init__(self, registry_url: str | None = None):
        url = (registry_url or DEFAULT_REGISTRY_URL).rstrip("/")
        parsed = urlparse(url)
        if parsed.scheme not in ("https", "http"):
            raise ValueError(f"Invalid hub URL scheme: {parsed.scheme}. Use https:// or http://")
        self.registry_url = url

    def _fetch_json(self, path: str) -> Any:
        url = f"{self.registry_url}/{path}"
        req = Request(url, headers={"User-Agent": "sediman-browse/0.1.0"})
        try:
            with urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except (URLError, OSError, json.JSONDecodeError) as e:
            logger.warning("hub_fetch_failed", url=url, error=str(e))
            return None

    def _fetch_text(self, path: str) -> str | None:
        url = f"{self.registry_url}/{path}"
        req = Request(url, headers={"User-Agent": "sediman-browse/0.1.0"})
        try:
            with urlopen(req, timeout=10) as resp:
                return resp.read().decode()
        except (URLError, OSError) as e:
            logger.warning("hub_fetch_failed", url=url, error=str(e))
            return None

    def _get_index(self) -> list[dict[str, Any]]:
        global _HUB_CACHE, _CACHE_KEY, _CACHE_TS

        cache_key = self.registry_url
        if _HUB_CACHE is not None and _CACHE_KEY == cache_key and (time.monotonic() - _CACHE_TS) < _CACHE_TTL:
            return _HUB_CACHE

        data = self._fetch_json("index.json")
        if isinstance(data, list):
            _HUB_CACHE = data
            _CACHE_KEY = cache_key
            _CACHE_TS = time.monotonic()
            return data
        return []

    def browse(self, category: str | None = None) -> list[HubSkillSummary]:
        index = self._get_index()
        results = []
        for entry in index:
            if category and entry.get("category") != category:
                continue
            results.append(HubSkillSummary(
                name=entry.get("name", ""),
                description=entry.get("description", ""),
                category=entry.get("category", "general"),
                author=entry.get("author"),
                version=entry.get("version", 1),
                installs=entry.get("installs", 0),
                trust=entry.get("trust", "community"),
                variables=entry.get("variables"),
                schedule=entry.get("schedule"),
            ))
        return results

    def search(self, query: str) -> list[HubSkillSummary]:
        query_lower = query.lower()
        index = self._get_index()
        results = []
        for entry in index:
            searchable = f"{entry.get('name', '')} {entry.get('description', '')} {entry.get('category', '')}".lower()
            if query_lower in searchable:
                results.append(HubSkillSummary(
                    name=entry.get("name", ""),
                    description=entry.get("description", ""),
                    category=entry.get("category", "general"),
                    author=entry.get("author"),
                    version=entry.get("version", 1),
                    installs=entry.get("installs", 0),
                    trust=entry.get("trust", "community"),
                    variables=entry.get("variables"),
                    schedule=entry.get("schedule"),
                ))
        return results

    def get_skill(self, name: str) -> SkillData | None:
        skill_json_text = self._fetch_text(f"skills/{name}/skill.json")
        if not skill_json_text:
            skill_md_text = self._fetch_text(f"skills/{name}/SKILL.md")
            if skill_md_text:
                from sediman.skills.format import parse_skill_md
                parsed = parse_skill_md(skill_md_text)
                if parsed:
                    parsed.source = "hub"
                return parsed
            return None

        from sediman.skills.format import parse_skill_json
        parsed = parse_skill_json(skill_json_text)
        if parsed:
            parsed.source = "hub"
            return parsed

        skill_md_text = self._fetch_text(f"skills/{name}/SKILL.md")
        if skill_md_text:
            from sediman.skills.format import parse_skill_md
            parsed = parse_skill_md(skill_md_text)
            if parsed:
                parsed.source = "hub"
            return parsed

        return None

    def install(self, name: str, engine: Any, force: bool = False) -> tuple[bool, str]:
        from sediman.skills.engine import SkillEngine
        if not isinstance(engine, SkillEngine):
            return False, "Invalid engine"

        existing = engine.read(name)
        if existing and not force:
            return False, f"Skill '{name}' already exists. Use --force to overwrite."

        skill = self.get_skill(name)
        if not skill:
            return False, f"Skill '{name}' not found in hub."

        result = validate_skill(skill)
        if not result.valid:
            return False, f"Skill validation failed: {'; '.join(result.errors)}"

        if result.warnings and not force:
            return False, f"Warnings: {'; '.join(result.warnings)}. Use --force to install anyway."

        if existing and force:
            engine.delete(name)

        skill.source = "hub"
        engine.install(skill)

        logger.info("skill_installed_from_hub", name=name)
        return True, f"Installed {name} (v{skill.version}, {result.trust_level})"

    def info(self, name: str) -> dict[str, Any] | None:
        skill = self.get_skill(name)
        if not skill:
            return None
        result = validate_skill(skill)
        return {
            "name": skill.name,
            "description": skill.description,
            "category": skill.category,
            "version": skill.version,
            "author": skill.author,
            "variables": skill.variables,
            "schedule": skill.schedule,
            "steps": skill.steps,
            "license": skill.license,
            "trust": result.trust_level,
            "warnings": result.warnings,
        }

    def publish(self, skill_data: SkillData) -> tuple[bool, str]:
        result = validate_skill(skill_data)
        if not result.valid:
            return False, f"Validation failed: {'; '.join(result.errors)}"

        logger.info("skill_publish", name=skill_data.name, trust=result.trust_level)
        return True, (
            f"Skill '{skill_data.name}' validated ({result.trust_level}). "
            "Publish to hub by opening a PR at https://github.com/sediman/skills-hub"
        )
