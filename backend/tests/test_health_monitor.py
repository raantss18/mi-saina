"""
Tests for services.health_monitor — bilan santé PROPOSE-ONLY.
On vérifie surtout : la forme des constats, l'agrégation, et que RIEN n'est exécuté
(les commandes sont seulement SUGGÉRÉES). Les commandes système sont mockées.
"""
import pytest
import services.health_monitor as hm


class TestFindingShape:
    def test_finding_fields(self):
        f = hm._finding("x", "warning", "T", "D", "sug", "cmd")
        assert f == {"id": "x", "severity": "warning", "title": "T",
                     "detail": "D", "suggestion": "sug", "command": "cmd"}


class TestDiskCheck:
    def test_warns_above_90(self, monkeypatch):
        monkeypatch.setattr(hm, "_run", lambda *a, **k: (0,
            "Filesystem 1024-blocks Used Available Capacity Mounted\n/dev/x 100 92 8 92% /home"))
        out = hm._check_disk()
        assert len(out) == 1 and out[0]["severity"] == "warning"
        assert out[0]["command"]   # action suggérée présente

    def test_critical_above_95(self, monkeypatch):
        monkeypatch.setattr(hm, "_run", lambda *a, **k: (0, "h\n/dev/x 100 97 3 97% /home"))
        assert hm._check_disk()[0]["severity"] == "critical"

    def test_silent_below_90(self, monkeypatch):
        monkeypatch.setattr(hm, "_run", lambda *a, **k: (0, "h\n/dev/x 100 40 60 40% /home"))
        assert hm._check_disk() == []


class TestRunChecks:
    def test_aggregates_and_updates_state(self, monkeypatch):
        monkeypatch.setattr(hm, "_check_disk", lambda: [hm._finding("disk", "warning", "T", "D")])
        monkeypatch.setattr(hm, "_check_failed_services", lambda: [])
        monkeypatch.setattr(hm, "_check_updates", lambda: [])
        monkeypatch.setattr(hm, "_check_journal_errors", lambda: [])
        st = hm.run_checks()
        assert st["checked_at"] is not None
        assert [f["id"] for f in st["findings"]] == ["disk"]
        assert hm.get_state()["findings"][0]["id"] == "disk"

    def test_a_failing_check_does_not_break_others(self, monkeypatch):
        def boom():
            raise RuntimeError("nope")
        monkeypatch.setattr(hm, "_check_disk", boom)
        monkeypatch.setattr(hm, "_check_failed_services", lambda: [hm._finding("svc", "info", "T", "D")])
        monkeypatch.setattr(hm, "_check_updates", lambda: [])
        monkeypatch.setattr(hm, "_check_journal_errors", lambda: [])
        st = hm.run_checks()
        assert [f["id"] for f in st["findings"]] == ["svc"]
