"""Tests des réglages modifiables à chaud (config.EDITABLE_SETTINGS + endpoints)."""

import json
import pytest
from fastapi.testclient import TestClient

import config as config_module
from config import settings, _coerce_setting, current_settings, update_settings


@pytest.fixture
def isolated_overrides(monkeypatch, tmp_path):
    """Isole le fichier d'overrides et restaure les réglages après le test."""
    monkeypatch.setattr(config_module, "_OVERRIDES_FILE", tmp_path / "settings.json")
    saved = current_settings()
    yield tmp_path / "settings.json"
    for k, v in saved.items():
        setattr(settings, k, v)


class TestCoerceSetting:
    def test_choice_valid(self):
        assert _coerce_setting("CONFIRM_MODE", "all") == "all"

    def test_choice_invalid(self):
        with pytest.raises(ValueError):
            _coerce_setting("CONFIRM_MODE", "bogus")

    def test_int_coerces_string(self):
        assert _coerce_setting("MAX_AGENT_STEPS", "8") == 8

    def test_int_out_of_range(self):
        with pytest.raises(ValueError):
            _coerce_setting("MAX_AGENT_STEPS", 999)

    def test_bool_from_string(self):
        assert _coerce_setting("CONTEXT_DIGEST", "false") is False
        assert _coerce_setting("CONTEXT_DIGEST", "oui") is True

    def test_unknown_key_rejected(self):
        with pytest.raises(ValueError):
            _coerce_setting("OLLAMA_BASE_URL", "http://evil")


class TestUpdateSettings:
    def test_applies_live(self, isolated_overrides):
        update_settings({"MAX_AGENT_STEPS": 9})
        assert settings.MAX_AGENT_STEPS == 9

    def test_persists_to_file(self, isolated_overrides):
        update_settings({"CONFIRM_MODE": "never"})
        data = json.loads(isolated_overrides.read_text())
        assert data["CONFIRM_MODE"] == "never"

    def test_atomic_on_invalid(self, isolated_overrides):
        before = settings.MAX_AGENT_STEPS
        with pytest.raises(ValueError):
            update_settings({"MAX_AGENT_STEPS": 7, "CONFIRM_MODE": "nope"})
        # rien n'est appliqué si une valeur est invalide
        assert settings.MAX_AGENT_STEPS == before

    def test_apply_overrides_on_load(self, isolated_overrides):
        isolated_overrides.write_text(json.dumps({"MAX_AGENT_STEPS": 3}))
        config_module._apply_overrides()
        assert settings.MAX_AGENT_STEPS == 3

    def test_apply_overrides_ignores_bad_values(self, isolated_overrides):
        settings.MAX_AGENT_STEPS = 6
        isolated_overrides.write_text(json.dumps({"MAX_AGENT_STEPS": 999}))
        config_module._apply_overrides()
        assert settings.MAX_AGENT_STEPS == 6   # valeur hors bornes ignorée


class TestSettingsEndpoints:
    @pytest.fixture
    def client(self, monkeypatch, tmp_path):
        monkeypatch.setattr(config_module, "_OVERRIDES_FILE", tmp_path / "settings.json")
        saved = current_settings()
        from main import app
        with TestClient(app) as c:
            yield c
        for k, v in saved.items():
            setattr(settings, k, v)

    def test_get_settings(self, client):
        r = client.get("/config/settings")
        assert r.status_code == 200
        body = r.json()
        assert "CONFIRM_MODE" in body["schema"]
        assert "CONFIRM_MODE" in body["values"]

    def test_put_settings_ok(self, client):
        r = client.put("/config/settings", json={"values": {"MAX_AGENT_STEPS": 10}})
        assert r.status_code == 200
        assert r.json()["values"]["MAX_AGENT_STEPS"] == 10

    def test_put_settings_invalid_returns_400(self, client):
        r = client.put("/config/settings", json={"values": {"CONFIRM_MODE": "xxx"}})
        assert r.status_code == 400
