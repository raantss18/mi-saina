"""
Tests de la résolution de référents entre sous-tâches (services.planner).

Chaque sous-tâche tourne dans un contexte neuf : un pronom pendant
(« compile-le ») doit être rattaché au dernier artefact concret produit par les
commandes précédentes. Helpers déterministes → testables sans LLM.
"""
import pytest

from services.planner import has_dangling_reference, last_artifact, reference_hint


class TestHasDanglingReference:
    @pytest.mark.parametrize("text", [
        "compile-le maintenant",
        "ouvre-la",
        "lance-les",
        "fais-le ensuite",
        "exécute ça",
        "ouvre cela",
        "recompile ce dernier",
        "relance la même",
    ])
    def test_pronoun_detected(self, text):
        assert has_dangling_reference(text) is True, text

    @pytest.mark.parametrize("text", [
        "ouvre le fichier main.c",          # « le » article + nom → pas pendant
        "crée le dossier projet",
        "liste les fichiers du dossier",
        "installe le paquet htop",
        "trouve la configuration nginx",
        "",
    ])
    def test_article_not_flagged(self, text):
        assert has_dangling_reference(text) is False, text


class TestLastArtifact:
    def test_extracts_last_path_with_tilde(self):
        assert last_artifact(["mkdir -p ~/proj", "touch ~/proj/main.c"]) == "~/proj/main.c"

    def test_extracts_filename_with_extension(self):
        assert last_artifact(["gcc -O2 main.c -o app", "echo done"]) == "main.c"

    def test_prefers_most_recent_command(self):
        cmds = ["touch a.py", "touch b.py"]
        assert last_artifact(cmds) == "b.py"

    def test_no_path_returns_empty(self):
        assert last_artifact(["echo hello", "ls -la"]) == ""

    def test_empty_list(self):
        assert last_artifact([]) == ""


class TestReferenceHint:
    def test_hint_built_when_pronoun_and_artifact(self):
        hint = reference_hint("compile-le", ["touch ~/proj/main.c"])
        assert "~/proj/main.c" in hint
        assert "RÉFÉRENCE" in hint

    def test_no_hint_without_pronoun(self):
        assert reference_hint("crée un fichier source", ["touch ~/proj/main.c"]) == ""

    def test_no_hint_without_artifact(self):
        assert reference_hint("compile-le", ["echo hi"]) == ""

    def test_no_hint_when_both_missing(self):
        assert reference_hint("affiche la date", ["date"]) == ""
