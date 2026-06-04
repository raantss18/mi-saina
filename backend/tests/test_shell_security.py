"""
Tests for dangerous-command detection, root-privilege detection,
AUR-helper detection, GUI-command detection, and sanitize().

All functions tested here are pure / synchronous — no mocking needed.
"""
import pytest
from services.shell_stream import (
    _is_dangerous as stream_is_dangerous,
    needs_root,
    sanitize,
    _is_aur_helper,
    _strip_leading_sudo,
    _first_token,
    _command_head,
    is_gui_command,
    _norm_name,
)
from services.shell_exec import is_dangerous as exec_is_dangerous


# ── shell_stream._is_dangerous ────────────────────────────────────────────────

class TestStreamIsDangerous:
    def test_rm_rf_absolute_path(self):
        assert stream_is_dangerous("rm -rf /etc") is True

    def test_rm_rf_home_path(self):
        assert stream_is_dangerous("rm -rf /home/user/docs") is True

    def test_rm_rf_relative_is_safe(self):
        assert stream_is_dangerous("rm -rf ./build") is False

    def test_rm_rf_tilde_is_safe(self):
        # ~/something does not start with /[^/]
        assert stream_is_dangerous("rm -rf ~/temp") is False

    def test_dd_if_blocked(self):
        assert stream_is_dangerous("dd if=/dev/zero of=/dev/sda bs=1M") is True

    def test_mkfs_ext4_blocked(self):
        assert stream_is_dangerous("mkfs.ext4 /dev/sda1") is True

    def test_mkfs_btrfs_blocked(self):
        assert stream_is_dangerous("mkfs.btrfs /dev/sdb") is True

    def test_fork_bomb_blocked(self):
        assert stream_is_dangerous(":() { :|:& };:") is True

    def test_dev_sda_write_blocked(self):
        assert stream_is_dangerous("cat img.iso > /dev/sda") is True

    def test_safe_ls(self):
        assert stream_is_dangerous("ls -la /home") is False

    def test_safe_echo(self):
        assert stream_is_dangerous("echo hello world") is False

    def test_safe_pacman(self):
        assert stream_is_dangerous("pacman -Syu") is False

    def test_safe_grep(self):
        assert stream_is_dangerous("grep -r 'pattern' /home/user") is False


# ── shell_exec.is_dangerous ───────────────────────────────────────────────────

class TestExecIsDangerous:
    def test_rm_rf_root_slash(self):
        assert exec_is_dangerous("rm -rf /") is True

    def test_rm_rf_absolute_path(self):
        assert exec_is_dangerous("rm -rf /etc") is True

    def test_rm_rf_relative_safe(self):
        assert exec_is_dangerous("rm -rf ./temp") is False

    def test_dd_if_blocked(self):
        assert exec_is_dangerous("dd if=/dev/urandom of=test") is True

    def test_mkfs_blocked(self):
        assert exec_is_dangerous("mkfs.xfs /dev/sdb1") is True

    def test_fork_bomb_blocked(self):
        assert exec_is_dangerous(":() { :|:& };:") is True

    def test_dev_sda_blocked(self):
        assert exec_is_dangerous("> /dev/sda") is True

    def test_safe_commands(self):
        for cmd in ("ls", "echo hi", "cat /etc/hosts", "pwd", "uname -a"):
            assert exec_is_dangerous(cmd) is False, f"Should be safe: {cmd}"


# ── needs_root ────────────────────────────────────────────────────────────────

class TestNeedsRoot:
    def test_explicit_sudo(self):
        assert needs_root("sudo apt install vim") is True

    def test_sudo_with_flags(self):
        assert needs_root("sudo -v") is True

    def test_pacman_install(self):
        assert needs_root("pacman -S vim") is True

    def test_pacman_remove(self):
        assert needs_root("pacman -R vim") is True

    def test_pacman_update(self):
        assert needs_root("pacman -Syu") is True

    def test_pacman_upgrade_pkg(self):
        assert needs_root("pacman -U package.tar.zst") is True

    def test_paru(self):
        assert needs_root("paru -S firefox") is True

    def test_yay(self):
        assert needs_root("yay -Syu") is True

    def test_systemctl_start(self):
        assert needs_root("systemctl start nginx") is True

    def test_systemctl_enable(self):
        assert needs_root("systemctl enable docker") is True

    def test_systemctl_stop(self):
        assert needs_root("systemctl stop sshd") is True

    def test_systemctl_user_flag_is_safe(self):
        assert needs_root("systemctl --user start pipewire") is False

    def test_chmod_777(self):
        assert needs_root("chmod 777 /etc/shadow") is True

    def test_useradd(self):
        assert needs_root("useradd newuser") is True

    def test_mkinitcpio(self):
        assert needs_root("mkinitcpio -P") is True

    def test_safe_ls(self):
        assert needs_root("ls -la") is False

    def test_safe_echo(self):
        assert needs_root("echo hello") is False

    def test_safe_git(self):
        assert needs_root("git status") is False

    def test_safe_python(self):
        assert needs_root("python script.py") is False

    def test_safe_systemctl_status(self):
        # status is not in the list of dangerous subcommands
        assert needs_root("systemctl status nginx") is False


# ── _strip_leading_sudo ───────────────────────────────────────────────────────

class TestStripLeadingSudo:
    def test_removes_sudo(self):
        assert _strip_leading_sudo("sudo pacman -Syu") == "pacman -Syu"

    def test_removes_sudo_with_spaces(self):
        assert _strip_leading_sudo("  sudo  pacman -Syu") == "pacman -Syu"

    def test_no_sudo_unchanged(self):
        assert _strip_leading_sudo("ls -la") == "ls -la"

    def test_sudo_only_no_trailing_space_unchanged(self):
        # regex requires "sudo " (space) — bare "sudo" with nothing after is not stripped
        assert _strip_leading_sudo("sudo") == "sudo"


# ── _first_token ──────────────────────────────────────────────────────────────

class TestFirstToken:
    def test_simple_command(self):
        assert _first_token("ls -la") == "ls"

    def test_sudo_command(self):
        assert _first_token("sudo pacman -S vim") == "pacman"

    def test_empty(self):
        assert _first_token("") == ""

    def test_aur_helper(self):
        assert _first_token("paru -S firefox") == "paru"


# ── _command_head ─────────────────────────────────────────────────────────────

class TestCommandHead:
    def test_simple(self):
        assert _command_head("firefox") == "firefox"

    def test_sudo_prefix(self):
        assert _command_head("sudo pacman -S vim") == "pacman"

    def test_env_var_prefix(self):
        assert _command_head("DISPLAY=:0 xterm") == "xterm"

    def test_path_returns_basename(self):
        assert _command_head("/usr/bin/python script.py") == "python"

    def test_empty(self):
        assert _command_head("") == ""


# ── is_gui_command ────────────────────────────────────────────────────────────

class TestIsGuiCommand:
    def test_firefox(self):
        assert is_gui_command("firefox https://example.com") is True

    def test_code_editor(self):
        assert is_gui_command("code /home/user/project") is True

    def test_vlc(self):
        assert is_gui_command("vlc movie.mp4") is True

    def test_dolphin(self):
        assert is_gui_command("dolphin /home/user") is True

    def test_xdg_open(self):
        assert is_gui_command("xdg-open /home/user/file.pdf") is True

    def test_gio_open_is_gui(self):
        assert is_gui_command("gio open /home/user/file") is True

    def test_gio_list_not_gui(self):
        assert is_gui_command("gio list /home/user") is False

    def test_ls_not_gui(self):
        assert is_gui_command("ls -la") is False

    def test_python_not_gui(self):
        assert is_gui_command("python script.py") is False

    def test_sudo_firefox(self):
        assert is_gui_command("sudo firefox") is True

    def test_gimp(self):
        assert is_gui_command("gimp image.png") is True

    def test_discord(self):
        assert is_gui_command("discord") is True

    def test_obsidian(self):
        assert is_gui_command("obsidian") is True


# ── _is_aur_helper ────────────────────────────────────────────────────────────

class TestIsAurHelper:
    def test_paru(self):
        assert _is_aur_helper("paru -S vim") is True

    def test_yay(self):
        assert _is_aur_helper("yay -Syu") is True

    def test_pikaur(self):
        assert _is_aur_helper("pikaur -S package") is True

    def test_sudo_paru(self):
        assert _is_aur_helper("sudo paru -S vim") is True

    def test_pacman_not_aur(self):
        assert _is_aur_helper("pacman -S vim") is False

    def test_apt_not_aur(self):
        assert _is_aur_helper("apt install vim") is False


# ── sanitize ──────────────────────────────────────────────────────────────────

class TestSanitize:
    def test_removes_noconfirm(self):
        result = sanitize("pacman -Syu --noconfirm")
        assert "--noconfirm" not in result
        assert "pacman -Syu" in result

    def test_removes_no_confirm_variant(self):
        result = sanitize("paru -S pkg --no-confirm")
        assert "--no-confirm" not in result

    def test_strips_sudo_from_aur_helper(self):
        result = sanitize("sudo paru -S firefox")
        assert not result.startswith("sudo")
        assert "paru" in result

    def test_keeps_sudo_for_pacman(self):
        result = sanitize("sudo pacman -Syu")
        assert result.startswith("sudo")

    def test_safe_command_unchanged(self):
        assert sanitize("ls -la /home") == "ls -la /home"

    def test_strips_whitespace(self):
        assert sanitize("  echo hello  ") == "echo hello"


# ── _norm_name ────────────────────────────────────────────────────────────────

class TestNormName:
    def test_basic(self):
        assert _norm_name("Hello World") == "hello world"

    def test_typographic_apostrophe(self):
        assert _norm_name("l’homme") == "l'homme"

    def test_curly_quotes(self):
        result = _norm_name("“quoted”")
        assert '"quoted"' == result

    def test_multiple_spaces(self):
        assert _norm_name("foo   bar") == "foo bar"

    def test_dash_variants(self):
        assert _norm_name("foo–bar") == "foo-bar"
        assert _norm_name("foo—bar") == "foo-bar"
