"""
Tests for services.config_map — scan déterministe et SECRET-SAFE de ~/.config / ~/.local.
On vérifie : l'index/détail, l'extraction de l'index, et surtout que RIEN de sensible
(dossier/clé ressemblant à un secret) n'entre dans la carte.
"""
import os
import stat
import pytest
import services.config_map as cm


def _make_tree(tmp_path):
    cfg = tmp_path / "config"
    loc = tmp_path / "local"
    (cfg / "kitty").mkdir(parents=True)
    (cfg / "nvim").mkdir()
    (cfg / "Code - OSS").mkdir()
    # Dossiers ressemblant à un secret → doivent être ignorés
    (cfg / "secrets").mkdir()
    (cfg / "my-credentials").mkdir()
    # gtk theme (clé non sensible)
    (cfg / "gtk-3.0").mkdir()
    (cfg / "gtk-3.0" / "settings.ini").write_text("[Settings]\ngtk-theme-name=Breeze\n")
    # mimeapps
    (cfg / "mimeapps.list").write_text(
        "[Default Applications]\napplication/pdf=okular.desktop\n")
    # scripts perso exécutables
    (loc / "bin").mkdir(parents=True)
    s = loc / "bin" / "deploy"
    s.write_text("#!/bin/sh\necho hi\n")
    s.chmod(s.stat().st_mode | stat.S_IXUSR)
    # lanceur custom
    appdir = loc / "share" / "applications"
    appdir.mkdir(parents=True)
    (appdir / "myapp.desktop").write_text(
        "[Desktop Entry]\nName=My Tool\nExec=/usr/bin/mytool --flag\n")
    return cfg, loc


class TestScanSecretSafety:
    def test_secret_dirs_excluded(self, tmp_path):
        cfg, loc = _make_tree(tmp_path)
        data = cm.scan(cfg, loc)
        assert "secrets" not in data["apps"]          # contient "secret"
        assert "my-credentials" not in data["apps"]   # contient "credential"
        assert "kitty" in data["apps"] and "nvim" in data["apps"]

    def test_is_secretish(self):
        assert cm._is_secretish("api_token") is True
        assert cm._is_secretish("client_secret") is True
        assert cm._is_secretish("id_rsa") is True
        assert cm._is_secretish("kitty") is False
        assert cm._is_secretish("nvim") is False

    def test_ini_get_skips_secret_keys(self, tmp_path):
        f = tmp_path / "x.ini"
        f.write_text("[S]\ntheme=Breeze\napi_token=SECRET123\n")
        out = cm._ini_get(f, "S", ["theme", "api_token"])
        assert out == {"theme": "Breeze"}   # le token est ignoré


class TestScanContent:
    def test_apps_scripts_launchers(self, tmp_path):
        cfg, loc = _make_tree(tmp_path)
        data = cm.scan(cfg, loc)
        assert "deploy" in data["scripts"]
        assert any(name == "My Tool" and exe == "mytool" for name, exe in data["launchers"])
        assert data["defaults"].get("application/pdf") == "okular"
        assert data["settings"].get("thème_gtk") == "Breeze"


class TestRenderAndIndex:
    def test_compose_has_markers_and_index_extracts(self, tmp_path):
        cfg, loc = _make_tree(tmp_path)
        composed = cm._compose(cm.scan(cfg, loc))
        assert cm._INDEX_START in composed and cm._INDEX_END in composed
        # index_block lit depuis MAP_FILE → on l'écrit dans un tmp
        f = tmp_path / "config-map.md"
        f.write_text(composed)
        import services.config_map as mod
        mod_map_file = mod.MAP_FILE
        try:
            mod.MAP_FILE = f
            idx = mod.index_block()
            assert "CONFIG CONNUE" in idx
            assert "CARTE DE CONFIGURATION — détail" not in idx   # index seul
        finally:
            mod.MAP_FILE = mod_map_file

    def test_refresh_writes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cm, "MAP_FILE", tmp_path / "config-map.md")
        monkeypatch.setattr(cm, "CONFIG_HOME", tmp_path)
        content = cm.refresh()
        assert (tmp_path / "config-map.md").exists()
        assert "CONFIG CONNUE" in content

    def test_ensure_fresh_skips_recent(self, tmp_path, monkeypatch):
        f = tmp_path / "config-map.md"
        f.write_text("frais")
        monkeypatch.setattr(cm, "MAP_FILE", f)
        cm.ensure_fresh(24.0)
        assert f.read_text() == "frais"   # récent → non réécrit
