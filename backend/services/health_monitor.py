"""
Bilan santé périodique — PROPOSE seulement, n'exécute JAMAIS rien.

Toutes les vérifications sont read-only, non-root, distro-agnostiques, bornées par un
timeout et tolérantes aux erreurs. Le moniteur calcule des « insights » (constats +
action SUGGÉRÉE) exposés au frontend ; c'est l'utilisateur qui décide d'agir.

Conçu léger : pas d'appel LLM, commandes locales rapides, intervalle réglable.
"""
import asyncio
import os
import shutil
import subprocess
from datetime import datetime, timezone

from config import settings
from services.sysinfo import _read_os_release, _pkg_commands

# État partagé : dernier bilan (lu par le routeur /health-monitor).
_state: dict = {"checked_at": None, "running": False, "findings": []}


def _run(cmd: list[str], timeout: float = 6.0) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception:
        return -1, ""


def _finding(fid: str, severity: str, title: str, detail: str,
             suggestion: str = "", command: str = "") -> dict:
    """severity ∈ {info, warning, critical}. `command` = action SUGGÉRÉE (jamais auto-exécutée)."""
    return {"id": fid, "severity": severity, "title": title, "detail": detail,
            "suggestion": suggestion, "command": command}


# ── Vérifications individuelles ────────────────────────────────────────────────

def _check_disk() -> list[dict]:
    rc, out = _run(["df", "-P", str(os.path.expanduser("~"))], timeout=4)
    if rc != 0 or not out:
        return []
    try:
        line = out.strip().splitlines()[-1].split()
        use_pct = int(line[4].rstrip("%"))
        avail = line[3]
    except (IndexError, ValueError):
        return []
    if use_pct >= 95:
        return [_finding("disk", "critical", "Disque presque plein",
                         f"La partition de ton home est utilisée à {use_pct}% (reste {avail} blocs).",
                         "Libère de l'espace (gros fichiers, caches).",
                         "du -h -d1 ~ 2>/dev/null | sort -hr | head -15")]
    if use_pct >= 90:
        return [_finding("disk", "warning", "Espace disque faible",
                         f"La partition de ton home est utilisée à {use_pct}%.",
                         "Repère les plus gros dossiers.",
                         "du -h -d1 ~ 2>/dev/null | sort -hr | head -15")]
    return []


def _check_failed_services() -> list[dict]:
    findings = []
    for scope, flag in (("utilisateur", "--user"), ("système", "--system")):
        rc, out = _run(["systemctl", flag, "--failed", "--no-legend", "--plain"], timeout=5)
        if rc != 0:
            continue
        units = [l.split()[0] for l in out.strip().splitlines() if l.strip()]
        if units:
            names = ", ".join(units[:6]) + (" …" if len(units) > 6 else "")
            cmd_scope = "--user " if flag == "--user" else ""
            findings.append(_finding(
                f"failed-{scope}", "warning", f"Service(s) {scope} en échec",
                f"{len(units)} unité(s) en échec : {names}.",
                "Inspecte le journal de l'unité concernée.",
                f"systemctl {cmd_scope}status {units[0]}"))
    return findings


def _check_updates() -> list[dict]:
    """Comptage des mises à jour dispo — read-only, sans sudo, tolérant et borné.
    N'utilise que des commandes ne nécessitant pas de privilèges ni de verrou."""
    osr = _read_os_release()
    family, cmds = _pkg_commands(osr)
    count = 0
    try:
        if family == "Arch":
            if shutil.which("checkupdates"):           # pacman-contrib, db temporaire, pas de lock
                rc, out = _run(["checkupdates"], timeout=20)
                count = len([l for l in out.splitlines() if l.strip()]) if rc in (0,) else 0
            else:
                return []   # pas d'outil non-root fiable → on ne propose rien
        elif family == "Debian/Ubuntu":
            rc, out = _run(["apt", "list", "--upgradable"], timeout=20)
            count = max(0, len([l for l in out.splitlines() if "/" in l]) - 0)
        elif family == "Fedora/RHEL":
            rc, out = _run(["dnf", "-q", "check-update"], timeout=25)
            count = len([l for l in out.splitlines() if l and l[0].isalnum()])
        else:
            return []
    except Exception:
        return []
    if count > 0:
        return [_finding("updates", "info", "Mises à jour disponibles",
                         f"{count} paquet(s) peuvent être mis à jour.",
                         "Mets le système à jour (tu valideras dans le terminal).",
                         cmds["update"])]
    return []


def _check_journal_errors() -> list[dict]:
    """Erreurs récentes du journal noyau/système (read-only ; rien si pas d'accès)."""
    rc, out = _run(["journalctl", "-p", "err", "-b", "--since", "-1h",
                    "--no-pager", "-q", "-k"], timeout=6)
    if rc != 0 or not out.strip():
        return []
    n = len([l for l in out.strip().splitlines() if l.strip()])
    if n >= 20:
        return [_finding("journal", "warning", "Erreurs noyau récentes",
                         f"{n} erreur(s) noyau dans la dernière heure.",
                         "Regarde les erreurs récentes pour diagnostiquer.",
                         "journalctl -p err -b --since -1h --no-pager -k | tail -40")]
    return []


def run_checks() -> dict:
    """Lance toutes les vérifications et met à jour l'état partagé. Read-only.

    On résout les fonctions via le module au moment de l'appel (et non une liste figée)
    pour rester testable (monkeypatch des checks individuels)."""
    _state["running"] = True
    findings: list[dict] = []
    for name in ("_check_disk", "_check_failed_services", "_check_updates", "_check_journal_errors"):
        try:
            findings.extend(globals()[name]())
        except Exception:
            continue
    _state["findings"] = findings
    _state["checked_at"] = datetime.now(timezone.utc).isoformat()
    _state["running"] = False
    return get_state()


def get_state() -> dict:
    return {"checked_at": _state["checked_at"], "running": _state["running"],
            "findings": list(_state["findings"]),
            "enabled": bool(getattr(settings, "HEALTH_MONITOR", True))}


# ── Boucle de fond ─────────────────────────────────────────────────────────────

async def health_loop() -> None:
    """Boucle périodique légère. Respecte HEALTH_MONITOR / HEALTH_INTERVAL_MIN à chaud."""
    await asyncio.sleep(45)   # laisse le système démarrer avant le 1er bilan
    while True:
        try:
            if getattr(settings, "HEALTH_MONITOR", True):
                await asyncio.to_thread(run_checks)
        except Exception:
            pass
        interval = max(5, int(getattr(settings, "HEALTH_INTERVAL_MIN", 30)))
        await asyncio.sleep(interval * 60)
