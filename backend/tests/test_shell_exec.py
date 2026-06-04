"""
Tests for services.shell_exec.execute_command.

Safe commands (echo, false) are executed for real.
Dangerous / sudo-blocked paths are tested without running a subprocess.
"""
import pytest
from services.shell_exec import execute_command, is_dangerous


class TestExecuteCommandBlocked:
    @pytest.mark.asyncio
    async def test_dangerous_command_blocked(self):
        result = await execute_command("rm -rf /")
        assert result["status"] == "blocked"
        assert "bloquée" in result["output"] or "dangereux" in result["output"]

    @pytest.mark.asyncio
    async def test_dd_command_blocked(self):
        result = await execute_command("dd if=/dev/zero of=/dev/sda")
        assert result["status"] == "blocked"

    @pytest.mark.asyncio
    async def test_mkfs_command_blocked(self):
        result = await execute_command("mkfs.ext4 /dev/sda1")
        assert result["status"] == "blocked"


class TestExecuteCommandSudo:
    @pytest.mark.asyncio
    async def test_sudo_without_password_returns_needs_sudo(self):
        result = await execute_command("sudo apt install vim")
        assert result["status"] == "needs_sudo"

    @pytest.mark.asyncio
    async def test_pacman_without_password_returns_needs_sudo(self):
        result = await execute_command("pacman -Syu")
        assert result["status"] == "needs_sudo"


class TestExecuteCommandSafe:
    @pytest.mark.asyncio
    async def test_echo_returns_ok(self):
        result = await execute_command("echo hello world")
        assert result["status"] == "ok"
        assert result["returncode"] == 0
        assert "hello world" in result["output"]

    @pytest.mark.asyncio
    async def test_false_returns_nonzero(self):
        result = await execute_command("false")
        assert result["status"] == "ok"
        assert result["returncode"] != 0

    @pytest.mark.asyncio
    async def test_exit_code_captured(self):
        result = await execute_command("bash -c 'exit 42'")
        assert result["status"] == "ok"
        assert result["returncode"] == 42

    @pytest.mark.asyncio
    async def test_multiline_output(self):
        result = await execute_command("printf 'line1\\nline2\\nline3'")
        assert result["status"] == "ok"
        assert "line1" in result["output"]
        assert "line2" in result["output"]
        assert "line3" in result["output"]

    @pytest.mark.asyncio
    async def test_stderr_merged_with_stdout(self):
        result = await execute_command("echo error >&2")
        assert result["status"] == "ok"
        assert "error" in result["output"]

    @pytest.mark.asyncio
    async def test_unknown_command_returns_nonzero(self):
        result = await execute_command("this_cmd_xyz_does_not_exist_12345")
        assert result["status"] == "ok"
        assert result["returncode"] != 0


class TestExecuteCommandTimeout:
    @pytest.mark.asyncio
    async def test_timeout_returns_timeout_status(self, monkeypatch):
        import asyncio
        from config import settings

        monkeypatch.setattr(settings, "SHELL_TIMEOUT", 0)

        async def instant_timeout(coro, timeout=None):
            raise asyncio.TimeoutError()

        monkeypatch.setattr(asyncio, "wait_for", instant_timeout)
        result = await execute_command("echo test")
        assert result["status"] == "timeout"
        assert "Timeout" in result["output"]
