"""
Détection du matériel et de la distribution à l'exécution.

Le system prompt reste GÉNÉRIQUE (versionné, sans données perso) ; ce bloc est
ajouté dynamiquement pour que mi-saina s'adapte à n'importe quelle machine et
distribution (gestionnaire de paquets, commandes de maj/install correctes).
"""

import os
import re
import shutil
import subprocess

_cache: str | None = None


def _read_os_release() -> dict:
    data = {}
    try:
        with open("/etc/os-release", encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    k, _, v = line.partition("=")
                    data[k.strip()] = v.strip().strip('"')
    except OSError:
        pass
    return data


def _pkg_commands(osr: dict) -> tuple[str, dict]:
    """Retourne (nom_distro_famille, {update, install, search, remove})."""
    ids = (osr.get("ID", "") + " " + osr.get("ID_LIKE", "")).lower()

    def has(*names):
        return any(shutil.which(n) for n in names)

    if "arch" in ids or has("pacman"):
        mgr = "paru" if has("paru") else ("yay" if has("yay") else "pacman")
        if mgr == "pacman":
            return "Arch", {"update": "sudo pacman -Syu", "install": "sudo pacman -S",
                            "search": "pacman -Ss", "remove": "sudo pacman -R"}
        return "Arch", {"update": f"{mgr} -Syu", "install": f"{mgr} -S",
                        "search": f"{mgr} -Ss", "remove": f"{mgr} -R"}
    if "debian" in ids or "ubuntu" in ids or has("apt", "apt-get"):
        return "Debian/Ubuntu", {"update": "sudo apt update && sudo apt upgrade",
                                 "install": "sudo apt install", "search": "apt search",
                                 "remove": "sudo apt remove"}
    if "fedora" in ids or "rhel" in ids or "centos" in ids or has("dnf"):
        return "Fedora/RHEL", {"update": "sudo dnf upgrade", "install": "sudo dnf install",
                               "search": "dnf search", "remove": "sudo dnf remove"}
    if "suse" in ids or has("zypper"):
        return "openSUSE", {"update": "sudo zypper update", "install": "sudo zypper install",
                            "search": "zypper search", "remove": "sudo zypper remove"}
    if has("xbps-install"):
        return "Void", {"update": "sudo xbps-install -Su", "install": "sudo xbps-install -S",
                        "search": "xbps-query -Rs", "remove": "sudo xbps-remove"}
    if has("apk"):
        return "Alpine", {"update": "sudo apk upgrade", "install": "sudo apk add",
                          "search": "apk search", "remove": "sudo apk del"}
    return "Linux", {"update": "(gestionnaire inconnu)", "install": "(gestionnaire inconnu)",
                     "search": "(gestionnaire inconnu)", "remove": "(gestionnaire inconnu)"}


def _cpu() -> str:
    model, cores = "", os.cpu_count() or 0
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as f:
            for line in f:
                if line.startswith("model name"):
                    model = line.split(":", 1)[1].strip()
                    break
    except OSError:
        pass
    return f"{model} ({cores} cœurs)" if model else f"{cores} cœurs"


def _ram_gb() -> str:
    try:
        with open("/proc/meminfo", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    kb = int(re.search(r"\d+", line).group())
                    return f"{kb / 1024 / 1024:.0f} GB"
    except (OSError, AttributeError):
        pass
    return "inconnue"


def _gpu() -> str:
    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total",
                 "--format=csv,noheader"],
                capture_output=True, text=True, timeout=4).stdout.strip()
            if out:
                return out.splitlines()[0].strip()
        except Exception:
            pass
    if shutil.which("lspci"):
        try:
            out = subprocess.run(["lspci"], capture_output=True, text=True, timeout=4).stdout
            for line in out.splitlines():
                if re.search(r"VGA compatible controller|3D controller", line):
                    return line.split(":", 2)[-1].strip()
        except Exception:
            pass
    return "inconnu"


def system_block() -> str:
    """Bloc d'infos système ajouté au system prompt (mis en cache)."""
    global _cache
    if _cache is not None:
        return _cache
    osr = _read_os_release()
    distro = osr.get("PRETTY_NAME") or osr.get("NAME") or "Linux"
    family, cmds = _pkg_commands(osr)
    _cache = (
        "## SYSTÈME (détecté automatiquement)\n"
        f"- OS : {distro} (famille {family})\n"
        f"- Shell : {os.environ.get('SHELL', '/bin/bash').split('/')[-1]}\n"
        f"- CPU : {_cpu()}\n"
        f"- GPU : {_gpu()}\n"
        f"- RAM : {_ram_gb()}\n"
        "### Gestionnaire de paquets de CETTE machine — utilise EXACTEMENT ces commandes :\n"
        f"- Mettre à jour le système : [EXEC: {cmds['update']}]\n"
        f"- Installer un paquet : [EXEC: {cmds['install']} <paquet>]\n"
        f"- Chercher un paquet : [EXEC: {cmds['search']} <motclé>]\n"
        "- N'utilise JAMAIS le gestionnaire d'une autre distribution. Pas de `--noconfirm`/`-y` "
        "(l'utilisateur valide). Ne lance jamais paru/yay avec sudo."
    )
    return _cache
