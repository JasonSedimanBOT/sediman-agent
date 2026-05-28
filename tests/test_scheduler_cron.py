from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from sediman.scheduler.cron import CronManager


@pytest.fixture
def cron(tmp_sediman_dir: Path):
    cron_dir = tmp_sediman_dir / "cron"
    with patch("sediman.scheduler.cron.JOBS_DIR", cron_dir):
        yield CronManager()


class TestCronManagerAddJob:
    def test_returns_job_id(self, cron):
        job_id = cron.add_job(cron_expr="0 * * * *", task="test task")
        assert len(job_id) == 12

    def test_creates_job_file(self, cron):
        job_id = cron.add_job(cron_expr="0 * * * *", task="test task")
        assert (cron.jobs_dir / f"{job_id}.json").exists()

    def test_job_file_has_correct_data(self, cron):
        job_id = cron.add_job(
            cron_expr="*/5 * * * *",
            task="check mail",
            provider="ollama",
            model="qwen3",
        )
        data = json.loads((cron.jobs_dir / f"{job_id}.json").read_text())
        assert data["cron"] == "*/5 * * * *"
        assert data["task"] == "check mail"
        assert data["provider"] == "ollama"


class TestCronManagerGetJob:
    def test_gets_existing_job(self, cron):
        job_id = cron.add_job(cron_expr="0 * * * *", task="t")
        job = cron.get_job(job_id)
        assert job is not None
        assert job["id"] == job_id

    def test_returns_none_for_missing(self, cron):
        assert cron.get_job("nonexistent") is None

    def test_partial_id_match(self, cron):
        job_id = cron.add_job(cron_expr="0 * * * *", task="t")
        job = cron.get_job(job_id[:6])
        assert job is not None


class TestCronManagerListJobs:
    def test_lists_all_jobs(self, cron):
        cron.add_job(cron_expr="0 * * * *", task="first")
        cron.add_job(cron_expr="0 0 * * *", task="second")
        jobs = cron.list_jobs()
        assert len(jobs) == 2

    def test_returns_empty_when_no_jobs(self, tmp_path):
        with patch("sediman.scheduler.cron.JOBS_DIR", tmp_path / "empty"):
            c = CronManager()
        assert c.list_jobs() == []


class TestCronManagerRemoveJob:
    def test_removes_existing_job(self, cron):
        job_id = cron.add_job(cron_expr="0 * * * *", task="t")
        assert cron.remove_job(job_id) is True
        assert not (cron.jobs_dir / f"{job_id}.json").exists()

    def test_returns_false_for_missing(self, cron):
        assert cron.remove_job("nonexistent") is False

    def test_partial_id_remove(self, cron):
        job_id = cron.add_job(cron_expr="0 * * * *", task="t")
        assert cron.remove_job(job_id[:6]) is True


class TestCronManagerUpdateJobResult:
    def test_updates_result(self, cron):
        job_id = cron.add_job(cron_expr="0 * * * *", task="t")
        cron.update_job_result(job_id, "completed successfully")
        job = cron.get_job(job_id)
        assert job["last_result"] == "completed successfully"
        assert job["last_run"] is not None

    def test_truncates_long_result(self, cron):
        job_id = cron.add_job(cron_expr="0 * * * *", task="t")
        cron.update_job_result(job_id, "x" * 1000)
        job = cron.get_job(job_id)
        assert len(job["last_result"]) <= 500
