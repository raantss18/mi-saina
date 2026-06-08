"""
Tests for pure-logic helpers in routers/chat.py:
  - EXEC_RE regex
  - _build_messages
  - _format_exec_feedback
"""
import pytest
import re
from unittest.mock import patch

# Import from the chat router (pure logic, no WebSocket needed)
from routers.chat import (
    EXEC_RE, _build_messages, _format_exec_feedback, _MAX_FEEDBACK_CHARS,
    _is_placeholder_cmd, _BAD_FACT_RE,
)


# ── Garde-fou : commandes-gabarits recopiées depuis les instructions ───────────

class TestPlaceholderCmd:
    @pytest.mark.parametrize("cmd", [
        "commande", "command", "cmd", "...", "…", "<command>", "<commande>",
        "  …  ", "`commande`", "<...>", "command here", "votre commande", "",
    ])
    def test_placeholders_rejected(self, cmd):
        assert _is_placeholder_cmd(cmd) is True

    @pytest.mark.parametrize("cmd", [
        "ls -la ~/Downloads", "paru -Syu", "echo hello", "du -sh ~/*",
        "cat notes.md", "mkdir -p ~/projet",
    ])
    def test_real_commands_kept(self, cmd):
        assert _is_placeholder_cmd(cmd) is False

    def test_filter_in_extraction(self):
        # Le modèle recopie la syntaxe d'exemple + une vraie commande
        text = "Syntaxe : [EXEC: commande]. Maintenant : [EXEC: ls -la]"
        cmds = [c.strip() for c in EXEC_RE.findall(text)
                if c.strip() and not _is_placeholder_cmd(c)]
        assert cmds == ["ls -la"]


# ── Garde-fou : faits empoisonnés (OS/environnement, tâches) ───────────────────

class TestBadFact:
    @pytest.mark.parametrize("fact", [
        "L'utilisateur utilise le système de fichiers Windows.",
        "The user is on macOS.",
        "User wants to see disk usage of their home.",
        "L'utilisateur souhaite organiser son dossier Téléchargements.",
        "The user uses the Linux filesystem.",
    ])
    def test_bad_facts_blocked(self, fact):
        assert _BAD_FACT_RE.search(fact) is not None

    @pytest.mark.parametrize("fact", [
        "The user prefers the French language.",
        "L'utilisateur préfère paru pour les mises à jour.",
        "The user's name is Antsa.",
        "L'utilisateur utilise l'éditeur Neovim.",
    ])
    def test_genuine_preferences_allowed(self, fact):
        assert _BAD_FACT_RE.search(fact) is None


# ── EXEC_RE ───────────────────────────────────────────────────────────────────

class TestExecRegex:
    def test_basic_command_extracted(self):
        text = "I will run [EXEC: ls -la] now."
        matches = EXEC_RE.findall(text)
        assert matches == ["ls -la"]

    def test_multiple_commands_extracted(self):
        text = "[EXEC: echo hello]\nsome text\n[EXEC: ls /tmp]"
        matches = EXEC_RE.findall(text)
        assert matches == ["echo hello", "ls /tmp"]

    def test_no_command_returns_empty(self):
        text = "There are no commands in this text."
        assert EXEC_RE.findall(text) == []

    def test_command_with_args_and_flags(self):
        text = '[EXEC: git log --oneline -10]'
        matches = EXEC_RE.findall(text)
        assert matches == ["git log --oneline -10"]

    def test_command_with_quotes(self):
        text = '[EXEC: grep -r "pattern" /home]'
        matches = EXEC_RE.findall(text)
        assert matches == ['grep -r "pattern" /home']

    def test_whitespace_inside_brackets(self):
        # The regex strips leading whitespace (via \s*) but NOT trailing whitespace
        # inside the capture group — callers strip() the match before use
        text = '[EXEC:   ls   ]'
        matches = EXEC_RE.findall(text)
        assert len(matches) == 1
        assert matches[0].strip() == "ls"

    def test_multiline_command_captured(self):
        text = '[EXEC: echo line1\necho line2]'
        matches = EXEC_RE.findall(text)
        assert len(matches) == 1

    def test_case_sensitive(self):
        # [exec: ...] lowercase should NOT match
        text = '[exec: ls]'
        assert EXEC_RE.findall(text) == []


# ── _build_messages ───────────────────────────────────────────────────────────

class TestBuildMessages:
    def setup_method(self):
        # Patch _load_system_prompt so tests don't depend on filesystem
        self.patcher = patch("routers.chat._load_system_prompt", return_value="You are a test assistant.")
        self.patcher.start()

    def teardown_method(self):
        self.patcher.stop()

    def test_basic_structure(self):
        msgs = _build_messages([], "Hello", None)
        assert msgs[0]["role"] == "system"
        assert msgs[-1]["role"] == "user"
        assert msgs[-1]["content"] == "Hello"

    def test_history_included(self):
        history = [
            {"role": "user", "content": "previous question"},
            {"role": "assistant", "content": "previous answer"},
        ]
        msgs = _build_messages(history, "new question", None)
        assert len(msgs) == 4  # system + 2 history + new user message
        assert msgs[1]["content"] == "previous question"
        assert msgs[2]["content"] == "previous answer"

    def test_memory_context_appended_to_system(self):
        memory = "RELEVANT MEMORY HERE"
        msgs = _build_messages([], "Hello", memory)
        assert memory in msgs[0]["content"]

    def test_no_memory_context_no_append(self):
        msgs = _build_messages([], "Hello", None)
        assert "RELEVANT MEMORY" not in msgs[0]["content"]

    def test_empty_memory_context_no_append(self):
        msgs = _build_messages([], "Hello", "")
        assert msgs[0]["content"] == "You are a test assistant."

    def test_text_attachments_prepended(self):
        attachments = [
            {"type": "text", "name": "notes.txt", "content": "file contents here"}
        ]
        msgs = _build_messages([], "analyze this", None, attachments)
        user_msg = msgs[-1]
        assert "[Fichier: notes.txt]" in user_msg["content"]
        assert "file contents here" in user_msg["content"]
        assert "analyze this" in user_msg["content"]

    def test_image_attachments_added_to_images_field(self):
        attachments = [
            {"type": "image", "name": "photo.png", "data": "base64data=="}
        ]
        msgs = _build_messages([], "describe this image", None, attachments)
        user_msg = msgs[-1]
        assert "images" in user_msg
        assert "base64data==" in user_msg["images"]

    def test_mixed_attachments(self):
        attachments = [
            {"type": "image", "name": "photo.png", "data": "imgdata"},
            {"type": "text", "name": "code.py", "content": "print('hello')"},
        ]
        msgs = _build_messages([], "review", None, attachments)
        user_msg = msgs[-1]
        assert "images" in user_msg
        assert "[Fichier: code.py]" in user_msg["content"]

    def test_no_attachments(self):
        msgs = _build_messages([], "simple question", None, None)
        assert msgs[-1]["content"] == "simple question"
        assert "images" not in msgs[-1]


# ── _format_exec_feedback ─────────────────────────────────────────────────────

class TestFormatExecFeedback:
    def test_single_command_formatted(self):
        results = [("ls -la", "total 8\ndrwxr-xr-x 2 user user 40 Jan 1 00:00 .", 0)]
        output = _format_exec_feedback(results)
        assert "$ ls -la" in output
        assert "total 8" in output
        assert "(code retour: 0)" in output

    def test_empty_output_shown_as_no_output(self):
        results = [("echo", "", 0)]
        output = _format_exec_feedback(results)
        assert "(aucune sortie)" in output

    def test_multiple_commands(self):
        results = [
            ("ls", "file.txt", 0),
            ("cat file.txt", "contents", 0),
        ]
        output = _format_exec_feedback(results)
        assert "$ ls" in output
        assert "$ cat file.txt" in output

    def test_nonzero_return_code_included(self):
        results = [("false", "", 1)]
        output = _format_exec_feedback(results)
        assert "(code retour: 1)" in output

    def test_long_output_truncated(self):
        long_output = "x" * (_MAX_FEEDBACK_CHARS + 500)
        results = [("cmd", long_output, 0)]
        output = _format_exec_feedback(results)
        assert "tronquée" in output
        # Ensure the output is actually truncated
        assert len(output) < len(long_output) + 1000

    def test_output_at_exact_limit_not_truncated(self):
        exact_output = "x" * _MAX_FEEDBACK_CHARS
        results = [("cmd", exact_output, 0)]
        output = _format_exec_feedback(results)
        assert "tronquée" not in output

    def test_instruction_appended(self):
        results = [("ls", "output", 0)]
        output = _format_exec_feedback(results)
        assert "RÉSULTAT DES COMMANDES" in output
        assert "INSTRUCTION" in output

    def test_negative_return_code_included(self):
        results = [("cmd", "error output", -1)]
        output = _format_exec_feedback(results)
        assert "(code retour: -1)" in output
