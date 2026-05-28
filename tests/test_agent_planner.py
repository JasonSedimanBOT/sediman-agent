from __future__ import annotations

import pytest

from sediman.agent.planner import TaskPlanner, Plan, ScheduleIntent


class TestTaskPlannerNoSchedule:
    def test_simple_task_no_schedule(self, tmp_sediman_dir):
        planner = TaskPlanner()
        plan = planner.plan("go to google and search for AI news")
        assert plan.browser_task == "go to google and search for AI news"
        assert plan.schedule is None

    def test_navigation_only_task(self, tmp_sediman_dir):
        planner = TaskPlanner()
        plan = planner.plan("navigate to https://example.com")
        assert plan.browser_task == "navigate to https://example.com"
        assert plan.schedule is None

    def test_extract_data_task(self, tmp_sediman_dir):
        planner = TaskPlanner()
        plan = planner.plan("go to hacker news and find the top post")
        assert plan.schedule is None
        assert "hacker news" in plan.browser_task.lower()


class TestTaskPlannerScheduleDetection:
    def test_every_5_minutes(self, tmp_sediman_dir):
        planner = TaskPlanner()
        plan = planner.plan("get nvidia stock price every 5 minutes")
        assert plan.schedule is not None
        assert plan.schedule.cron == "*/5 * * * *"
        assert "nvidia" in plan.schedule.task.lower()
        assert "every" not in plan.browser_task.lower()

    def test_every_minute(self, tmp_sediman_dir):
        planner = TaskPlanner()
        plan = planner.plan("check the server status every minute")
        assert plan.schedule is not None
        assert plan.schedule.cron == "*/1 * * * *"

    def test_every_30_minutes(self, tmp_sediman_dir):
        planner = TaskPlanner()
        plan = planner.plan("monitor the website every 30 minutes")
        assert plan.schedule is not None
        assert plan.schedule.cron == "*/30 * * * *"

    def test_every_hour(self, tmp_sediman_dir):
        planner = TaskPlanner()
        plan = planner.plan("check prices every hour")
        assert plan.schedule is not None
        assert plan.schedule.cron == "0 * * * *"

    def test_hourly(self, tmp_sediman_dir):
        planner = TaskPlanner()
        plan = planner.plan("check CPU usage hourly")
        assert plan.schedule is not None
        assert plan.schedule.cron == "0 * * * *"

    def test_daily(self, tmp_sediman_dir):
        planner = TaskPlanner()
        plan = planner.plan("send a report daily")
        assert plan.schedule is not None
        assert plan.schedule.cron == "0 9 * * *"

    def test_daily_at_time(self, tmp_sediman_dir):
        planner = TaskPlanner()
        plan = planner.plan("run backup daily at 3am")
        assert plan.schedule is not None
        assert "3" in plan.schedule.cron
        assert "*" in plan.schedule.cron

    def test_weekly(self, tmp_sediman_dir):
        planner = TaskPlanner()
        plan = planner.plan("clean up temp files weekly")
        assert plan.schedule is not None
        assert plan.schedule.cron == "0 9 * * 1"

    def test_every_2_hours(self, tmp_sediman_dir):
        planner = TaskPlanner()
        plan = planner.plan("check the feed every 2 hours")
        assert plan.schedule is not None
        assert plan.schedule.cron == "0 */2 * * *"

    def test_monitor_keyword(self, tmp_sediman_dir):
        planner = TaskPlanner()
        plan = planner.plan("monitor the competitor website")
        assert plan.schedule is not None
        assert plan.schedule.cron == "*/5 * * * *"


class TestTaskPlannerBrowserTaskExtraction:
    def test_strips_every_minutes(self, tmp_sediman_dir):
        planner = TaskPlanner()
        plan = planner.plan("get nvidia stock price every 5 minutes")
        assert "every" not in plan.browser_task.lower()
        assert "nvidia" in plan.browser_task.lower()
        assert "stock price" in plan.browser_task.lower()

    def test_strips_schedule_it_every(self, tmp_sediman_dir):
        planner = TaskPlanner()
        plan = planner.plan("go to yahoo finance and get nvda price and schedule it every 5 minutes")
        assert "schedule" not in plan.browser_task.lower()
        assert "every" not in plan.browser_task.lower()
        assert "yahoo" in plan.browser_task.lower()

    def test_strips_run_it_every(self, tmp_sediman_dir):
        planner = TaskPlanner()
        plan = planner.plan("check reddit top post and run it every hour")
        assert "every" not in plan.browser_task.lower()
        assert "reddit" in plan.browser_task.lower()

    def test_preserves_task_when_no_schedule(self, tmp_sediman_dir):
        planner = TaskPlanner()
        plan = planner.plan("go to amazon and find cheap headphones")
        assert plan.browser_task == "go to amazon and find cheap headphones"

    def test_fallback_to_original_when_strip_empties(self, tmp_sediman_dir):
        planner = TaskPlanner()
        plan = planner.plan("every 5 minutes")
        assert plan.browser_task == "every 5 minutes"


class TestScheduleIntentDataclass:
    def test_fields(self):
        intent = ScheduleIntent(cron="*/5 * * * *", task="check price")
        assert intent.cron == "*/5 * * * *"
        assert intent.task == "check price"


class TestPlanDataclass:
    def test_defaults(self):
        plan = Plan(browser_task="do something")
        assert plan.browser_task == "do something"
        assert plan.schedule is None
        assert plan.needs_memory is True
        assert plan.needs_skill_eval is True

    def test_with_schedule(self):
        schedule = ScheduleIntent(cron="0 * * * *", task="check")
        plan = Plan(browser_task="do it", schedule=schedule)
        assert plan.schedule.cron == "0 * * * *"
