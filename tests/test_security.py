from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from sediman.skills.engine import SkillEngine, _validate_safe_name


class TestPathTraversal:
    def test_rejects_dotdot(self):
        with pytest.raises(ValueError, match="Invalid skill name"):
            _validate_safe_name("../../etc/passwd")

    def test_rejects_absolute_path(self):
        with pytest.raises(ValueError, match="Invalid skill name"):
            _validate_safe_name("/etc/passwd")

    def test_rejects_dot(self):
        with pytest.raises(ValueError, match="Invalid skill name"):
            _validate_safe_name(".")

    def test_rejects_dotdot_prefix(self):
        with pytest.raises(ValueError, match="Invalid skill name"):
            _validate_safe_name("../secret")

    def test_rejects_slash_in_name(self):
        with pytest.raises(ValueError, match="Invalid skill name"):
            _validate_safe_name("foo/bar")

    def test_rejects_null_byte(self):
        with pytest.raises(ValueError, match="Invalid skill name"):
            _validate_safe_name("foo\x00bar")

    def test_rejects_empty(self):
        with pytest.raises(ValueError, match="Invalid skill name"):
            _validate_safe_name("")

    def test_rejects_too_long(self):
        with pytest.raises(ValueError, match="Invalid skill name"):
            _validate_safe_name("a" * 65)

    def test_accepts_valid_name(self):
        _validate_safe_name("my-skill")

    def test_accepts_simple_name(self):
        _validate_safe_name("test")

    def test_engine_create_rejects_traversal(self, tmp_path: Path):
        engine = SkillEngine(skills_dir=tmp_path / "skills")
        with pytest.raises(ValueError):
            engine.create(name="../../etc", description="evil", steps=[])

    def test_engine_read_rejects_traversal(self, tmp_path: Path):
        engine = SkillEngine(skills_dir=tmp_path / "skills")
        with pytest.raises(ValueError):
            engine.read("../../etc/passwd")

    def test_engine_delete_rejects_traversal(self, tmp_path: Path):
        engine = SkillEngine(skills_dir=tmp_path / "skills")
        with pytest.raises(ValueError):
            engine.delete("../../etc")

    def test_engine_patch_rejects_traversal(self, tmp_path: Path):
        engine = SkillEngine(skills_dir=tmp_path / "skills")
        with pytest.raises(ValueError):
            engine.patch("../../etc", {"description": "evil"})


class TestCronValidation:
    def test_valid_cron(self):
        from sediman.scheduler.cron import validate_cron_expr
        assert validate_cron_expr("0 9 * * *")
        assert validate_cron_expr("*/5 * * * *")
        assert validate_cron_expr("0,30 9-17 * * 1-5")

    def test_rejects_too_few_fields(self):
        from sediman.scheduler.cron import validate_cron_expr
        assert not validate_cron_expr("0 9 * *")

    def test_rejects_too_many_fields(self):
        from sediman.scheduler.cron import validate_cron_expr
        assert not validate_cron_expr("0 9 * * * extra")

    def test_rejects_letters(self):
        from sediman.scheduler.cron import validate_cron_expr
        assert not validate_cron_expr("0 9 mon * *")

    def test_rejects_empty(self):
        from sediman.scheduler.cron import validate_cron_expr
        assert not validate_cron_expr("")

    def test_rejects_semicolons(self):
        from sediman.scheduler.cron import validate_cron_expr
        assert not validate_cron_expr("0 9 * * *; rm -rf /")


class TestInputLengthLimits:
    def test_hub_install_rejects_bad_name(self, tmp_path: Path):
        from fastapi.testclient import TestClient
        from sediman.api.app import app, init_state
        init_state()
        client = TestClient(app)
        resp = client.post("/api/hub/install", json={"name": "../../etc", "force": False})
        assert resp.status_code == 422

    def test_hub_install_rejects_long_name(self, tmp_path: Path):
        from fastapi.testclient import TestClient
        from sediman.api.app import app, init_state
        init_state()
        client = TestClient(app)
        resp = client.post("/api/hub/install", json={"name": "a" * 65, "force": False})
        assert resp.status_code == 422

    def test_schedule_rejects_bad_cron(self, tmp_path: Path):
        from fastapi.testclient import TestClient
        from sediman.api.app import app, init_state
        init_state()
        client = TestClient(app)
        resp = client.post("/api/schedule", json={"cron": "bad", "task": "do thing"})
        assert resp.status_code == 422

    def test_schedule_rejects_empty_task(self, tmp_path: Path):
        from fastapi.testclient import TestClient
        from sediman.api.app import app, init_state
        init_state()
        client = TestClient(app)
        resp = client.post("/api/schedule", json={"cron": "0 9 * * *", "task": ""})
        assert resp.status_code == 422

    def test_task_rejects_empty(self, tmp_path: Path):
        from fastapi.testclient import TestClient
        from sediman.api.app import app, init_state
        init_state()
        client = TestClient(app)
        resp = client.post("/api/task", json={"task": ""})
        assert resp.status_code == 422

    def test_skills_endpoints_reject_traversal(self, tmp_path: Path):
        from fastapi.testclient import TestClient
        from sediman.api.app import app, init_state
        init_state()
        client = TestClient(app)
        resp = client.get("/api/skills/../../etc/passwd")
        assert resp.status_code != 200 or "error" in resp.json()
        resp = client.delete("/api/skills/../../etc/passwd")
        assert resp.status_code != 200 or "error" in resp.json()
