"""
Tests for services.userctx — notamment le garde-fou anti-empoisonnement du profil :
une « mémoire » qui affirme l'environnement (OS/distribution/système de fichiers)
ne doit JAMAIS être écrite (c'est auto-détecté, et c'est presque toujours une
hallucination qui contaminerait toutes les sessions suivantes).
"""
import pytest
import services.userctx as userctx


@pytest.fixture
def tmp_profile(tmp_path, monkeypatch):
    """Isole context.md / profile.md dans un répertoire temporaire."""
    monkeypatch.setattr(userctx, "CONFIG_HOME", tmp_path)
    monkeypatch.setattr(userctx, "CONTEXT_FILE", tmp_path / "context.md")
    monkeypatch.setattr(userctx, "PROFILE_FILE", tmp_path / "profile.md")
    return tmp_path


class TestAppendProfileGuard:
    def test_genuine_preference_is_saved(self, tmp_profile):
        userctx.append_profile("The user prefers the French language.")
        assert "French language" in userctx.read_profile()

    @pytest.mark.parametrize("bad", [
        "L'utilisateur utilise le système de fichiers Windows.",
        "The user is on macOS.",
        "The user uses the Linux filesystem.",
        "L'utilisateur est sous Ubuntu.",
    ])
    def test_environment_claims_are_rejected(self, tmp_profile, bad):
        userctx.append_profile(bad)
        assert userctx.read_profile().strip() == ""   # rien écrit

    def test_dedup_still_works(self, tmp_profile):
        userctx.append_profile("The user's editor is Neovim.")
        userctx.append_profile("the user's editor is neovim.")   # casse différente
        assert userctx.read_profile().count("Neovim") == 1
