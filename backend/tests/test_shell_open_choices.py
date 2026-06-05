"""
Tests de la détection d'ouverture ambiguë (shell_stream.open_choice_candidates) :
plusieurs fichiers proches → on propose une liste cliquable plutôt que choisir.
"""
import pytest

from services import shell_stream as ss


@pytest.fixture
def docs(tmp_path):
    for name in ["rapport_final.pdf", "rapport_final_v2.pdf", "rapport_brouillon.pdf", "notes.txt"]:
        (tmp_path / name).write_text("x")
    return tmp_path


def test_ambiguous_open_returns_multiple_candidates(docs):
    # « rapport_final » n'existe pas tel quel mais matche 2+ fichiers
    cmd = f'xdg-open {docs}/rapport_final'
    cands = ss.open_choice_candidates(cmd)
    assert len(cands) >= 2
    assert any(c.endswith("rapport_final.pdf") for c in cands)
    assert any(c.endswith("rapport_final_v2.pdf") for c in cands)


def test_existing_file_is_not_ambiguous(docs):
    # Le fichier existe → pas de choix à proposer (flux normal)
    cmd = f'xdg-open {docs}/notes.txt'
    assert ss.open_choice_candidates(cmd) == []


def test_single_match_is_not_ambiguous(tmp_path):
    (tmp_path / "uniquedoc.pdf").write_text("x")
    cmd = f'xdg-open {tmp_path}/uniquedoc'
    # Un seul candidat → on laisse l'auto-réparation opérer, pas de liste
    assert ss.open_choice_candidates(cmd) == []


def test_non_open_command_ignored(docs):
    assert ss.open_choice_candidates(f'ls {docs}/rapport_final') == []


def test_url_not_treated_as_file():
    assert ss.open_choice_candidates("xdg-open https://example.com") == []


def test_candidates_helper_ranks_substring_first(docs):
    cands = ss._resolve_file_candidates(f"{docs}/rapport_final")
    # Les fichiers contenant « rapport_final » doivent ressortir
    assert cands and cands[0].endswith((".pdf",))
