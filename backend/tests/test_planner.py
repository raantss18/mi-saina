"""
Tests for the planner service:
  - estimate_tokens
  - fit_budget
  - should_plan
  - _parse_subtasks
  - rule_split
"""
import pytest
from unittest.mock import patch, AsyncMock
from config import settings
from services.planner import (
    estimate_tokens,
    fit_budget,
    should_plan,
    rule_split,
    _parse_subtasks,
    plan_task,
    _digest_line,
    _build_digest,
    _DIGEST_HEADER,
)


# ── estimate_tokens ───────────────────────────────────────────────────────────

class TestEstimateTokens:
    def test_exactly_four_chars(self):
        assert estimate_tokens("abcd") == 1

    def test_eight_chars(self):
        assert estimate_tokens("a" * 8) == 2

    def test_four_hundred_chars(self):
        assert estimate_tokens("a" * 400) == 100

    def test_empty_string_returns_minimum_one(self):
        assert estimate_tokens("") == 1

    def test_short_string_returns_minimum_one(self):
        assert estimate_tokens("ab") == 1

    def test_long_text(self):
        text = "word " * 200  # 1000 chars
        assert estimate_tokens(text) == 250


# ── fit_budget ────────────────────────────────────────────────────────────────

class TestFitBudget:
    def test_empty_list(self):
        assert fit_budget([]) == []

    def test_no_trim_needed(self):
        msgs = [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "hello"},
        ]
        result = fit_budget(msgs, max_tokens=10_000)
        assert len(result) == 2

    def test_always_keeps_system_message(self):
        msgs = [{"role": "system", "content": "sys"}]
        for i in range(50):
            msgs.append({"role": "user", "content": f"msg{i} " * 20})
        result = fit_budget(msgs, max_tokens=100)
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "sys"

    def test_always_keeps_last_message(self):
        msgs = [{"role": "system", "content": "sys"}]
        for i in range(50):
            msgs.append({"role": "user", "content": f"message number {i}"})
        result = fit_budget(msgs, max_tokens=100)
        assert result[-1]["content"] == "message number 49"

    def test_trims_middle_messages(self):
        msgs = [{"role": "system", "content": "sys"}]
        for i in range(20):
            msgs.append({"role": "user", "content": "x" * 100})
        result = fit_budget(msgs, max_tokens=50)
        # Should have system + fewer messages + last
        assert len(result) < 21

    def test_no_system_message(self):
        msgs = [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "second"},
            {"role": "user", "content": "third"},
        ]
        result = fit_budget(msgs, max_tokens=10_000)
        # No system message, should still work
        assert result[-1]["content"] == "third"

    def test_single_message_preserved(self):
        msgs = [{"role": "user", "content": "hello"}]
        result = fit_budget(msgs, max_tokens=5)
        assert len(result) == 1
        assert result[0]["content"] == "hello"


# ── fit_budget : résumé extractif de l'historique élagué ────────────────────────

class TestContextDigest:
    def _long_session(self):
        msgs = [{"role": "system", "content": "sys"}]
        for i in range(30):
            msgs.append({"role": "user", "content": f"Question numéro {i} " * 10})
            msgs.append({"role": "assistant", "content": f"Réponse numéro {i} " * 10})
        msgs.append({"role": "user", "content": "dernière question"})
        return msgs

    def test_digest_inserted_when_trimming(self, monkeypatch):
        monkeypatch.setattr(settings, "CONTEXT_DIGEST", True)
        result = fit_budget(self._long_session(), max_tokens=300)
        # système + résumé + quelques récents + dernier
        assert result[0]["role"] == "system"
        assert result[1]["content"].startswith(_DIGEST_HEADER)
        assert result[-1]["content"] == "dernière question"

    def test_digest_mentions_old_content(self, monkeypatch):
        monkeypatch.setattr(settings, "CONTEXT_DIGEST", True)
        result = fit_budget(self._long_session(), max_tokens=300)
        digest = result[1]["content"]
        assert "numéro 0" in digest      # le tout premier échange (origine) est préservé

    def test_digest_respects_budget(self, monkeypatch):
        monkeypatch.setattr(settings, "CONTEXT_DIGEST", True)
        result = fit_budget(self._long_session(), max_tokens=300)
        digest = result[1]["content"]
        assert estimate_tokens(digest) <= max(150, 300 // 6) + 5

    def test_disabled_falls_back_to_hard_cut(self, monkeypatch):
        monkeypatch.setattr(settings, "CONTEXT_DIGEST", False)
        result = fit_budget(self._long_session(), max_tokens=300)
        assert not any(_DIGEST_HEADER in (m.get("content") or "") for m in result)
        assert result[0]["role"] == "system"
        assert result[-1]["content"] == "dernière question"

    def test_no_digest_when_no_trim(self, monkeypatch):
        monkeypatch.setattr(settings, "CONTEXT_DIGEST", True)
        msgs = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "salut"},
            {"role": "assistant", "content": "bonjour"},
            {"role": "user", "content": "ça va ?"},
        ]
        result = fit_budget(msgs, max_tokens=10_000)
        assert result == msgs


class TestDigestLine:
    def test_user_message(self):
        line = _digest_line({"role": "user", "content": "ouvre le fichier rapport.pdf"})
        assert line.startswith("Utilisateur —")
        assert "rapport.pdf" in line

    def test_extracts_exec_commands(self):
        line = _digest_line({"role": "assistant",
                             "content": "Je lance ça [EXEC: ls -la] pour voir."})
        assert "commandes : ls -la" in line
        assert "[EXEC:" not in line

    def test_empty_message_returns_none(self):
        assert _digest_line({"role": "user", "content": "   "}) is None

    def test_strips_noise_markers(self):
        line = _digest_line({"role": "user",
                             "content": "[RÉSULTAT DES COMMANDES] tout va bien"})
        assert "[RÉSULTAT" not in line
        assert "tout va bien" in line

    def test_truncates_long_content(self):
        line = _digest_line({"role": "user", "content": "mot " * 200})
        assert "…" in line


class TestBuildDigest:
    def test_empty_returns_empty_string(self):
        assert _build_digest([], 100) == ""

    def test_keeps_oldest_when_over_budget(self):
        dropped = [{"role": "user", "content": f"message très long {i} " * 20}
                   for i in range(10)]
        digest = _build_digest(dropped, 120)
        assert estimate_tokens(digest) <= 120
        # le plus récent (9) est sacrifié avant le plus ancien (0) — origine préservée
        assert "long 0" in digest
        assert "long 9" not in digest


# ── should_plan ───────────────────────────────────────────────────────────────

class TestShouldPlan:
    def test_simple_command_not_planned(self):
        assert should_plan("ls -la") is False

    def test_single_short_action_not_planned(self):
        assert should_plan("ouvre Firefox") is False

    def test_puis_keyword_triggers_planning(self):
        assert should_plan("ouvre Firefox puis installe vim") is True

    def test_ensuite_keyword_triggers_planning(self):
        assert should_plan("cherche le fichier ensuite ouvre-le") is True

    def test_two_distinct_verbs_triggers_planning(self):
        assert should_plan("installe vim et lance-le") is True

    def test_long_text_triggers_planning(self):
        assert should_plan("a" * 241) is True

    def test_exactly_240_chars_not_planned_by_length(self):
        # 240 chars — only triggered if keywords or 2+ verbs present
        text = "a" * 240
        # No verbs, no keywords → should not plan
        assert should_plan(text) is False

    def test_planning_disabled_returns_false(self, monkeypatch):
        from config import settings
        monkeypatch.setattr(settings, "PLANNER_ENABLED", False)
        assert should_plan("ouvre Firefox puis installe vim") is False

    def test_enfin_keyword(self):
        assert should_plan("cherche les fichiers, puis compile, enfin lance") is True


# ── _parse_subtasks ───────────────────────────────────────────────────────────

class TestParseSubtasks:
    def test_valid_json_array(self):
        raw = '["Trouver le projet", "Compiler le code", "Lancer les tests"]'
        result = _parse_subtasks(raw)
        assert result == ["Trouver le projet", "Compiler le code", "Lancer les tests"]

    def test_empty_array_returns_empty(self):
        result = _parse_subtasks("[]")
        assert result == []

    def test_invalid_json_returns_empty(self):
        result = _parse_subtasks("not json at all")
        assert result == []

    def test_strips_think_tags(self):
        raw = '<think>reasoning here</think>["Tâche A", "Tâche B"]'
        result = _parse_subtasks(raw)
        assert result == ["Tâche A", "Tâche B"]

    def test_unclosed_think_tag_handled(self):
        raw = '["Tâche A", "Tâche B"]<think>unfinished reasoning'
        result = _parse_subtasks(raw)
        assert result == ["Tâche A", "Tâche B"]

    def test_takes_last_json_array(self):
        raw = '[1, 2, 3]["Tâche A", "Tâche B"]'
        result = _parse_subtasks(raw)
        assert result == ["Tâche A", "Tâche B"]

    def test_too_short_tasks_filtered(self):
        raw = '["ok", "Tâche correcte"]'  # "ok" has 2 chars < 3
        result = _parse_subtasks(raw)
        # "ok" is 2 chars, should be filtered → whole list fails validation
        assert result == []

    def test_tasks_exactly_min_length(self):
        raw = '["abc", "Tâche correcte"]'  # "abc" has 3 chars
        result = _parse_subtasks(raw)
        assert "abc" in result

    def test_too_long_tasks_filtered(self):
        long_task = "a" * 201
        raw = f'["{long_task}", "Normal task"]'
        result = _parse_subtasks(raw)
        assert result == []

    def test_max_subtasks_respected(self, monkeypatch):
        from config import settings
        monkeypatch.setattr(settings, "MAX_SUBTASKS", 2)
        raw = '["Task A", "Task B", "Task C", "Task D"]'
        result = _parse_subtasks(raw)
        assert len(result) == 2

    def test_non_string_items_filtered(self):
        raw = '["Valid task", 42, null, "Another task"]'
        result = _parse_subtasks(raw)
        assert result == ["Valid task", "Another task"]


# ── rule_split ────────────────────────────────────────────────────────────────

class TestRuleSplit:
    def test_no_split_for_simple_text(self):
        assert rule_split("simple task") == ["simple task"]

    def test_splits_on_puis(self):
        parts = rule_split("fais A puis fais B")
        assert len(parts) == 2

    def test_splits_on_ensuite(self):
        parts = rule_split("étape 1 ensuite étape 2")
        assert len(parts) == 2

    def test_splits_on_enfin(self):
        parts = rule_split("commence par A puis B enfin C")
        assert len(parts) >= 2

    def test_splits_on_semicolon(self):
        parts = rule_split("cmd1; cmd2; cmd3")
        assert len(parts) == 3

    def test_soft_split_needs_two_verbs(self):
        # "installe vim et lance-le" has 2 verbs → splits
        parts = rule_split("installe vim et lance-le")
        assert len(parts) >= 2

    def test_soft_split_single_verb_no_split(self):
        # Only one verb → no split
        parts = rule_split("installe vim et les dépendances")
        assert len(parts) == 1

    def test_cleans_residual_connectors(self):
        parts = rule_split("d'abord ouvre Firefox puis installe vim")
        # The "d'abord" should be cleaned from the first part
        assert not parts[0].startswith("d'abord")

    def test_max_subtasks_respected(self, monkeypatch):
        from config import settings
        monkeypatch.setattr(settings, "MAX_SUBTASKS", 2)
        parts = rule_split("A puis B puis C puis D")
        assert len(parts) <= 2

    def test_result_not_empty_strings(self):
        parts = rule_split("A puis B")
        assert all(p.strip() for p in parts)


# ── plan_task (async, rule path) ──────────────────────────────────────────────

class TestPlanTask:
    @pytest.mark.asyncio
    async def test_plan_task_returns_list(self):
        result = await plan_task("simple task without complex keywords")
        assert isinstance(result, list)
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_plan_task_splits_multi_action(self):
        result = await plan_task("ouvre Firefox puis installe vim")
        assert len(result) >= 2

    @pytest.mark.asyncio
    async def test_plan_task_llm_fallback_to_rules_on_empty(self, monkeypatch):
        from config import settings
        monkeypatch.setattr(settings, "PLANNER_USE_LLM", True)

        async def mock_llm_plan(text):
            return []  # LLM returns nothing → fall back to rule_split

        with patch("services.planner._llm_plan", new=mock_llm_plan):
            result = await plan_task("ouvre Firefox puis installe vim")
        assert isinstance(result, list)
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_plan_task_uses_llm_when_enabled(self, monkeypatch):
        from config import settings
        monkeypatch.setattr(settings, "PLANNER_USE_LLM", True)

        async def mock_llm_plan(text):
            return ["Step one", "Step two", "Step three"]

        with patch("services.planner._llm_plan", new=mock_llm_plan):
            result = await plan_task("some complex task")
        assert result == ["Step one", "Step two", "Step three"]
