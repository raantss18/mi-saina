# [mi-saina-improve] Tests du classifieur de complexité (P4 — thinking conditionnel).
import pytest
from services import task_classifier as tc


class TestClassify:
    @pytest.mark.parametrize("text", [
        "Quelle commande pour lister les services systemd actifs ?",
        "Donne-moi la commande pour voir l'espace disque utilisé.",
        "C'est quoi un inode ?",
        "Affiche-moi la version du noyau.",
    ])
    def test_simple(self, text):
        assert tc.classify(text) == tc.SIMPLE
        assert tc.wants_thinking(tc.SIMPLE) is False

    @pytest.mark.parametrize("text", [
        "Mon service nginx ne démarre pas après mise à jour du système. Diagnostique et propose un fix complet.",
        "J'ai une erreur au boot, répare-la.",
        "Trouve le fichier de conf et corrige le port.",
    ])
    def test_intermediate(self, text):
        assert tc.classify(text) == tc.INTERMEDIATE
        assert tc.wants_thinking(tc.INTERMEDIATE) is True

    @pytest.mark.parametrize("text", [
        "Analyse mes logs systemd des 24 dernières heures, identifie tous les services en échec, "
        "pour chacun propose un diagnostic causal et un plan de remédiation avec vérification.",
        "Identifie les conflits de port, les services redondants, et propose un plan de nettoyage "
        "ordonné avec rollback possible.",
        "Fais le ménage de tous les paquets orphelins puis nettoie le cache.",
    ])
    def test_complex(self, text):
        assert tc.classify(text) == tc.COMPLEX
        assert tc.wants_thinking(tc.COMPLEX) is True

    def test_empty_is_simple(self):
        assert tc.classify("") == tc.SIMPLE
        assert tc.classify("   ") == tc.SIMPLE

    def test_negated_symptom_not_counted_as_action(self):
        # « ne démarre pas » ne doit pas gonfler le compte de verbes → reste INTERMEDIATE
        assert tc.classify("nginx ne démarre pas, diagnostique") == tc.INTERMEDIATE


class TestSubtaskGranularity:
    """Sous-tâches atomiques d'un plan : doivent souvent retomber en SIMPLE (thinking off)
    même si la tâche globale est COMPLEX — c'est le gain de la re-classification par étape."""

    @pytest.mark.parametrize("sub", [
        "Trouver le projet LaTeX dans ~/Documents",
        "Compiler le projet",
        "Afficher l'espace disque",
    ])
    def test_atomic_subtasks_are_simple(self, sub):
        assert tc.classify(sub) == tc.SIMPLE
        assert tc.wants_thinking(tc.classify(sub)) is False

    @pytest.mark.parametrize("sub", [
        "Diagnostiquer chaque service en échec",
        "Proposer un plan de remédiation ordonné",
    ])
    def test_analytic_subtasks_keep_thinking(self, sub):
        assert tc.classify(sub) == tc.COMPLEX
        assert tc.wants_thinking(tc.classify(sub)) is True
