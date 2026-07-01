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
        from config import settings

        monkeypatch.setattr(settings, "SHELL_TIMEOUT", 1)
        result = await execute_command("sleep 30")
        assert result["status"] == "timeout"
        assert "Timeout" in result["output"]

    @pytest.mark.asyncio
    async def test_timeout_kills_the_process(self, monkeypatch, tmp_path):
        """Au timeout, la commande doit être TUÉE (avant : elle continuait en fond)."""
        import asyncio
        from config import settings

        monkeypatch.setattr(settings, "SHELL_TIMEOUT", 1)
        marker = tmp_path / "leaked"
        await execute_command(f"sleep 2 && touch {marker}")
        await asyncio.sleep(1.7)   # laisserait le temps au processus orphelin de finir
        assert not marker.exists(), "le processus a survécu au timeout"


class TestSudoPasswordNotOnCmdline:
    @pytest.mark.asyncio
    async def test_password_never_in_command_line(self, monkeypatch):
        """Le mot de passe sudo ne doit JAMAIS être interpolé dans la commande
        lancée (elle serait visible par tout processus local via /proc/*/cmdline).
        Il doit passer par stdin (`sudo -S`)."""
        import asyncio
        import services.shell_exec as se

        seen: dict = {}
        real = asyncio.create_subprocess_shell

        async def spy(cmd, **kwargs):
            seen["cmd"] = cmd
            seen["stdin"] = kwargs.get("stdin")
            kwargs["stdin"] = asyncio.subprocess.PIPE
            return await real("cat >/dev/null; true", **kwargs)

        monkeypatch.setattr(se.asyncio, "create_subprocess_shell", spy)
        result = await se.execute_command("sudo systemctl restart nginx",
                                          sudo_password="s3cret-pw")
        assert result["status"] == "ok"
        assert "s3cret-pw" not in seen["cmd"]
        assert seen["stdin"] == asyncio.subprocess.PIPE
        assert seen["cmd"].startswith("sudo -S")

    @pytest.mark.asyncio
    async def test_aur_helper_password_not_in_command_line(self, monkeypatch):
        import asyncio
        import services.shell_exec as se

        seen: dict = {}
        real = asyncio.create_subprocess_shell

        async def spy(cmd, **kwargs):
            seen["cmd"] = cmd
            kwargs["stdin"] = asyncio.subprocess.PIPE
            return await real("cat >/dev/null; true", **kwargs)

        monkeypatch.setattr(se.asyncio, "create_subprocess_shell", spy)
        result = await se.execute_command("paru -Syu", sudo_password="s3cret-pw")
        assert result["status"] == "ok"
        assert "s3cret-pw" not in seen["cmd"]
        assert "paru -Syu" in seen["cmd"]
