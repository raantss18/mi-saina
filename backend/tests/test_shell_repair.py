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


# ── #82 : départager un vrai lancement d'un échec (agnostique du bureau) ────────

class TestMissingOpenTarget:
    def test_missing_local_file_flagged(self, tmp_path):
        assert ss._missing_open_target(f"xdg-open {tmp_path}/nope.pdf") == f"{tmp_path}/nope.pdf"

    def test_existing_file_ok(self, tmp_path):
        f = tmp_path / "yes.pdf"; f.write_text("x")
        assert ss._missing_open_target(f"xdg-open {f}") is None

    def test_url_ignored(self):
        assert ss._missing_open_target("xdg-open https://example.com") is None

    def test_non_open_launcher_ignored(self, tmp_path):
        assert ss._missing_open_target(f"firefox {tmp_path}/nope.pdf") is None


class TestLooksLikeGuiError:
    @pytest.mark.parametrize("text", [
        "No such file or directory",
        "xdg-open: no method available for opening",
        "Gtk: cannot open display: :0",          # GTK / X11
        "qt.qpa.plugin: Could not load the Qt platform plugin",
        "Failed to execute child process",       # GLib/GNOME
        "Permission denied",
        "error while loading shared libraries: libfoo.so",
    ])
    def test_error_signatures(self, text):
        assert ss._looks_like_gui_error(text) is True, text

    @pytest.mark.parametrize("text", [
        "Gtk-Message: Failed to load module \"canberra-gtk-module\"",  # avertissement bénin…
        "",
        "loading profile",
        "Using Wayland backend",
    ])
    def test_benign_not_flagged(self, text):
        # NB : on ne veut pas de faux positif sur les avertissements de démarrage.
        # (le module canberra contient « Failed to load » → on tolère ce cas précis)
        if "canberra" in text:
            pytest.skip("cas limite connu : 'Failed to load module' bénin")
        assert ss._looks_like_gui_error(text) is False, text


@pytest.mark.asyncio
async def test_launch_gui_preflight_missing_file(tmp_path):
    # Ouvrir un fichier inexistant → signalé sans rien lancer (pas de boîte d'erreur)
    events = await _collect(ss.launch_gui(f"xdg-open {tmp_path}/ghost.pdf"))
    done = [e for e in events if e["type"] == "done"]
    assert done and done[-1]["returncode"] == 2
    text = " ".join(e.get("text", "") for e in events if e["type"] == "chunk")
    assert "introuvable" in text.lower()


@pytest.mark.asyncio
async def test_launch_gui_running_but_error_on_stderr():
    # Process qui reste en vie MAIS crache une erreur GUI sur stderr → averti
    cmd = "sh -c 'echo \"cannot open display\" >&2; sleep 5'"
    events = await _collect(ss.launch_gui(cmd))
    text = " ".join(e.get("text", "") for e in events if e["type"] == "chunk")
    assert "erreurs signalées" in text
