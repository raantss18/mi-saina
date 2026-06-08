"""
Tests for services.machine_profile — collecte read-only du profil machine.
Les appels système (du, xdg-user-dir) sont évités/bornés ; on teste surtout la
logique pure (catégorisation, résumé d'un dossier réel temporaire, rendu).
"""
import os
import pytest
import services.machine_profile as mp


class TestCategorize:
    @pytest.mark.parametrize("ext,cat", [
        (".pdf", "documents"), (".DOCX", "documents"), (".png", "images"),
        (".mp4", "vidéos"), (".mp3", "audio"), (".zip", "archives"),
        (".iso", "archives"), (".py", "code"), (".tsx", "code"),
        (".xyz", "autres"), ("", "autres"),
    ])
    def test_categories(self, ext, cat):
        assert mp.categorize(ext) == cat


class TestSummarizeDir:
    def test_counts_files_and_subdirs(self, tmp_path):
        (tmp_path / "a.pdf").write_text("x")
        (tmp_path / "b.png").write_text("x")
        (tmp_path / "c.py").write_text("x")
        (tmp_path / "sub").mkdir()
        s = mp._summarize_dir(str(tmp_path))
        assert s["files"] == 3
        assert s["subdirs"] == 1
        assert s["by_cat"]["documents"] == 1
        assert s["by_cat"]["images"] == 1
        assert s["by_cat"]["code"] == 1

    def test_missing_dir_is_safe(self):
        s = mp._summarize_dir("/no/such/dir/zzz")
        assert s["files"] == 0 and s["subdirs"] == 0


class TestRenderAndRefresh:
    def test_render_includes_real_paths(self):
        data = {
            "xdg": [("Téléchargements", "/home/u/Downloads")],
            "top_dirs": ["Documents", "Projets"], "hidden": 3,
            "summaries": {"Téléchargements": ("/home/u/Downloads",
                          {"files": 5, "subdirs": 1, "by_cat": {"documents": 5}, "size": "10M"})},
            "tools": ["git", "python3"],
            "desktop": "KDE", "session_type": "wayland", "locale": "fr_FR.UTF-8",
        }
        out = mp._render(data)
        assert "/home/u/Downloads" in out
        assert "Téléchargements" in out
        assert "git, python3" in out
        assert "KDE" in out

    def test_refresh_writes_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(mp, "MACHINE_FILE", tmp_path / "machine.md")
        monkeypatch.setattr(mp, "CONFIG_HOME", tmp_path)
        content = mp.refresh()
        assert (tmp_path / "machine.md").exists()
        assert "PROFIL MACHINE" in content
        assert mp.read() == content

    def test_ensure_collected_skips_if_present(self, tmp_path, monkeypatch):
        f = tmp_path / "machine.md"
        f.write_text("déjà là")
        monkeypatch.setattr(mp, "MACHINE_FILE", f)
        mp.ensure_collected()
        assert f.read_text() == "déjà là"   # non écrasé
