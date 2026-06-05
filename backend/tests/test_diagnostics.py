"""Tests de la détection de statut fine (services.diagnostics.assess_outcome)."""

import pytest

from services import diagnostics


class TestAssessOutcomeReturnCode:
    def test_rc_zero_clean_output_is_success(self):
        out = diagnostics.assess_outcome("Done.\nEverything is fine.", 0)
        assert out["status"] == "success"
        assert out["logical"] is False

    def test_nonzero_rc_is_failure(self):
        out = diagnostics.assess_outcome("oops", 1)
        assert out["status"] == "failure"
        assert out["logical"] is False
        assert "1" in out["reason"]

    def test_none_rc_treated_as_failure(self):
        out = diagnostics.assess_outcome("", None)
        assert out["status"] == "failure"


class TestLogicalFailureDespiteRcZero:
    @pytest.mark.parametrize("text", [
        "Traceback (most recent call last):\n  File ...\nValueError: x",
        "panic: runtime error: index out of range",
        "Tests: 1 failed, 5 passed, 6 total",
        "=== 3 failed, 10 passed in 1.2s ===",
        "FAILED tests/test_foo.py::test_bar - assert 1 == 2",
        "2 examples, 1 failure",
        "BUILD FAILED",
        "✖ 3 problems (3 errors, 0 warnings)",
        "src/main.c:10:5: error: expected ';'",
        "erreur : symbole non défini",
        "Compilation terminated.",
        "Le programme a renvoyé ❌ une erreur",
    ])
    def test_logical_failure_detected(self, text):
        out = diagnostics.assess_outcome(text, 0)
        assert out["status"] == "failure", text
        assert out["logical"] is True
        assert out["reason"]


class TestNoFalsePositive:
    @pytest.mark.parametrize("text", [
        "0 errors, 0 warnings",
        "No errors found.",
        "Aucune erreur détectée.",
        "Tests: 0 failed, 12 passed",
        "12 passed, 0 failed",
        "Build succeeded with no errors",
        "All 8 tests passed.",
        "error handling configured correctly",
        "✖ 0 problems",
    ])
    def test_clean_output_stays_success(self, text):
        out = diagnostics.assess_outcome(text, 0)
        assert out["status"] == "success", text
        assert out["logical"] is False


class TestFormatOutcomeForModel:
    def test_empty_for_success(self):
        out = diagnostics.assess_outcome("ok", 0)
        assert diagnostics.format_outcome_for_model(out) == ""

    def test_empty_for_plain_nonzero(self):
        # rc≠0 n'est PAS un échec logique → géré par le code retour, pas de note dédiée
        out = diagnostics.assess_outcome("boom", 2)
        assert diagnostics.format_outcome_for_model(out) == ""

    def test_note_for_logical_failure(self):
        out = diagnostics.assess_outcome("Tests: 1 failed, 2 passed", 0)
        note = diagnostics.format_outcome_for_model(out)
        assert "échec logique" in note
        assert "code retour 0" in note
