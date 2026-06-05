"""
Tests des chemins shell_stream non encore couverts (#100) :
  - auto-réparation de chemin (_resolve_file / _repair_open_command)
  - lancement d'application graphique (launch_gui) : succès / échec
"""
import pytest

from services import shell_stream as ss


# ── Auto-réparation de chemin ──────────────────────────────────────────────────

class TestResolveFile:
    def test_existing_path_returned_as_is(self, tmp_path):
        f = tmp_path / "exists.txt"
        f.write_text("x")
        assert ss._resolve_file(str(f)) == str(f)

    def test_collapses_extra_spaces(self, tmp_path):
        (tmp_path / "Mon Rapport.pdf").write_text("x")
        # double espace dans la requête → normalisé → doit résoudre
        got = ss._resolve_file(f"{tmp_path}/Mon  Rapport.pdf")
        assert got is not None and got.endswith("Mon Rapport.pdf")

    def test_typographic_apostrophe_resolved(self, tmp_path):
        (tmp_path / "l'ete.txt").write_text("x")           # apostrophe droite sur disque
        got = ss._resolve_file(f"{tmp_path}/l’ete.txt")  # apostrophe typo dans la requête
        assert got is not None and got.endswith("l'ete.txt")

    def test_url_is_not_a_file(self):
        assert ss._resolve_file("https://example.com/x") is None

    def test_no_close_match_returns_none(self, tmp_path):
        (tmp_path / "alpha.txt").write_text("x")
        assert ss._resolve_file(f"{tmp_path}/zzzzzzzzzz.pdf") is None


class TestRepairOpenCommand:
    def test_rebuilds_with_resolved_path(self, tmp_path):
        (tmp_path / "Mon Rapport.pdf").write_text("x")
        # chemin quoté (comme le produit le modèle) avec double espace à corriger
        cmd = f'xdg-open "{tmp_path}/Mon  Rapport.pdf"'
        rebuilt, fixed = ss._repair_open_command(cmd)
        assert fixed is not None and fixed.endswith("Mon Rapport.pdf")
        assert "Mon Rapport.pdf" in rebuilt

    def test_existing_path_unchanged(self, tmp_path):
        f = tmp_path / "ok.txt"
        f.write_text("x")
        cmd = f"xdg-open {f}"
        rebuilt, fixed = ss._repair_open_command(cmd)
        assert fixed is None
        assert rebuilt == cmd

    def test_non_open_command_unchanged(self, tmp_path):
        cmd = f"cat {tmp_path}/whatever.txt"
        rebuilt, fixed = ss._repair_open_command(cmd)
        assert fixed is None
        assert rebuilt == cmd


# ── Lancement d'application graphique ──────────────────────────────────────────

async def _collect(agen):
    return [ev async for ev in agen]


@pytest.mark.asyncio
async def test_launch_gui_success():
    # `true` rend la main vite avec code 0 → considéré « lancé »
    events = await _collect(ss.launch_gui("true"))
    done = [e for e in events if e["type"] == "done"]
    assert done and done[-1]["returncode"] == 0


@pytest.mark.asyncio
async def test_launch_gui_failure_reports_returncode():
    # sort vite avec un code ≠ 0 → erreur remontée + done rc≠0
    events = await _collect(ss.launch_gui("sh -c 'exit 7'"))
    done = [e for e in events if e["type"] == "done"]
    assert done and done[-1]["returncode"] == 7
    text = " ".join(e.get("text", "") for e in events if e["type"] == "chunk")
    assert "Échec" in text or "7" in text
