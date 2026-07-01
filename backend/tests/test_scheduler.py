"""Tests du planificateur local (mode headless).

Régression : `_run_safe_command` appelait `stream_pty(cmd, timeout=300)` alors
que le paramètre s'appelle `idle_timeout` → TypeError silencieux, TOUTES les
tâches planifiées échouaient sans trace. On exécute désormais une vraie commande
pour garantir que la signature reste compatible.
"""
from datetime import datetime, timedelta

import pytest

from services import scheduler


class TestRunSafeCommand:
    @pytest.mark.asyncio
    async def test_executes_real_command(self):
        out, rc = await scheduler._run_safe_command("echo bonjour-scheduler")
        assert rc == 0
        assert "bonjour-scheduler" in out

    @pytest.mark.asyncio
    async def test_root_command_is_skipped(self):
        out, rc = await scheduler._run_safe_command("sudo systemctl restart nginx")
        assert rc == -1
        assert "root" in out


class TestIsDue:
    def test_every_never_run(self):
        job = {"schedule": "every:5", "last_run": None}
        assert scheduler._is_due(job, datetime.now()) is True

    def test_every_recent_not_due(self):
        now = datetime.now()
        job = {"schedule": "every:10",
               "last_run": (now - timedelta(minutes=3)).isoformat()}
        assert scheduler._is_due(job, now) is False

    def test_daily_after_target(self):
        now = datetime.now().replace(hour=12, minute=0)
        job = {"schedule": "daily:09:00", "last_run": None}
        assert scheduler._is_due(job, now) is True

    def test_invalid_schedule_is_ignored(self):
        job = {"schedule": "n'importe quoi", "last_run": None}
        assert scheduler._is_due(job, datetime.now()) is False
