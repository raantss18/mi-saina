"""Mise à jour du logiciel mi-saina.

Deux modes auto-détectés :
- « source » : dépôt git cloné → git pull (+ dépendances) puis redémarrage.
- « run »    : installé via .run dans /opt → téléchargement de la dernière
               release GitHub et relance de l'installeur (pkexec).
"""
import asyncio
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import httpx
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()

REPO_DIR = Path(__file__).resolve().parent.parent.parent  # racine du dépôt / install
GH_REPO = os.environ.get("MISAINA_GH_REPO", "raantss18/mi-saina")


def _current_version() -> str:
    vf = REPO_DIR / "VERSION"
    if vf.exists():
        return vf.read_text().strip()
    return "0.0.0"


def _install_type() -> str:
    if str(REPO_DIR).startswith("/opt/mi-saina"):
        return "run"
    if (REPO_DIR / ".git").exists():
        return "source"
    return "unknown"


def _parts(v: str):
    nums = [int(x) for x in re.findall(r"\d+", v or "")][:3]
    return nums or [0]


def _is_newer(latest: str, current: str) -> bool:
    return _parts(latest) > _parts(current)


async def _latest_release() -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"https://api.github.com/repos/{GH_REPO}/releases/latest",
                headers={"Accept": "application/vnd.github+json"},
            )
            if r.status_code == 200:
                return r.json()
    except Exception:
        pass
    return None


@router.get("/check")
async def check():
    current = _current_version()
    rel = await _latest_release()
    latest = (rel.get("tag_name", "").lstrip("vV").strip() if rel else None)
    return {
        "current": current,
        "latest": latest,
        "update_available": bool(latest and _is_newer(latest, current)),
        "install_type": _install_type(),
    }


def _ev(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"


async def _run(cmd: list[str], cwd: Path):
    """Exécute une commande en streamant ses lignes ; renvoie le code retour final."""
    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
    )
    assert proc.stdout
    async for line in proc.stdout:
        t = line.decode(errors="replace").rstrip()
        if t:
            yield ("log", t)
    rc = await proc.wait()
    yield ("rc", rc)


async def _update_source():
    yield _ev({"log": "📥 git pull…"})
    pulled_changes = True
    async for kind, val in _run(["git", "pull", "--ff-only"], REPO_DIR):
        if kind == "log":
            if "Already up to date" in val or "à jour" in val:
                pulled_changes = False
            yield _ev({"log": val})
        elif kind == "rc" and val != 0:
            yield _ev({"log": "✗ git pull a échoué (modifications locales ? réseau ?)"})
            return

    if not pulled_changes:
        yield _ev({"log": "✓ Déjà à jour — rien à faire."})
        return

    # Dépendances Python (venv local)
    venv_py = None
    for v in ("mi-saina-env", "localmind-env"):
        p = Path.home() / v / "bin" / "python"
        if p.exists():
            venv_py = p
            break
    if venv_py and (REPO_DIR / "backend" / "requirements.txt").exists():
        yield _ev({"log": "📦 Dépendances Python…"})
        async for kind, val in _run([str(venv_py), "-m", "pip", "install", "-q", "-r", "requirements.txt"], REPO_DIR / "backend"):
            if kind == "log":
                yield _ev({"log": val})

    # Dépendances frontend
    if shutil.which("npm"):
        yield _ev({"log": "📦 Dépendances frontend…"})
        async for kind, val in _run(["npm", "install", "--silent"], REPO_DIR / "frontend"):
            if kind == "log":
                yield _ev({"log": val})

    # Redémarrage : services systemd si présents, sinon l'appli desktop se relance.
    has_systemd = False
    try:
        chk = await asyncio.create_subprocess_exec(
            "systemctl", "--user", "is-active", "mi-saina-backend",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
        )
        out, _ = await chk.communicate()
        has_systemd = out.decode().strip() == "active"
    except Exception:
        pass

    if has_systemd:
        yield _ev({"log": "🔄 Redémarrage des services… (la connexion va se couper, c'est normal)"})
        # Détaché (commande fixe, aucune interpolation) : laisse le flux arriver
        # avant de redémarrer le backend.
        subprocess.Popen(
            ["bash", "-c", "sleep 2 && systemctl --user restart mi-saina-backend mi-saina-frontend"],
            start_new_session=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    else:
        yield _ev({"log": "✅ Mise à jour appliquée. Recompile/relance la fenêtre desktop pour terminer (npm run desktop:build)."})


async def _update_run():
    rel = await _latest_release()
    if not rel:
        yield _ev({"log": "✗ Impossible de récupérer la dernière release."})
        return
    asset = next((a for a in rel.get("assets", []) if a["name"].endswith(".run")), None)
    if not asset:
        yield _ev({"log": "✗ Aucun installeur .run dans la dernière release."})
        return
    # Dossier temporaire privé (0700) → pas d'attaque par lien symbolique dans /tmp.
    tmpdir = Path(tempfile.mkdtemp(prefix="mi-saina-upd-"))
    safe_name = os.path.basename(asset["name"]) or "mi-saina.run"
    dest = tmpdir / safe_name
    yield _ev({"log": f"📥 Téléchargement de {safe_name}…"})
    try:
        async with httpx.AsyncClient(timeout=None, follow_redirects=True) as client:
            async with client.stream("GET", asset["browser_download_url"]) as resp:
                with open(dest, "wb") as f:
                    async for chunk in resp.aiter_bytes(1 << 16):
                        f.write(chunk)
        os.chmod(dest, 0o755)
    except Exception as e:  # noqa: BLE001
        yield _ev({"log": f"✗ Téléchargement échoué : {e}"})
        return
    yield _ev({"log": "🚀 Lancement de l'installeur (mot de passe administrateur demandé)…"})
    # subprocess (liste, sans shell) : pkexec affiche une fenêtre graphique de mot
    # de passe pour l'installation dans /opt ; repli sans pkexec si indisponible.
    launcher = "pkexec" if shutil.which("pkexec") else None
    cmd = [launcher, "sh", str(dest)] if launcher else ["sh", str(dest)]
    subprocess.Popen(cmd, start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    yield _ev({"log": "✅ Installeur lancé. Suis la fenêtre d'installation, puis relance mi-saina."})


@router.get("/apply")
async def apply():
    async def stream():
        itype = _install_type()
        yield _ev({"log": f"Type d'installation détecté : {itype}"})
        if itype == "source":
            async for m in _update_source():
                yield m
        elif itype == "run":
            async for m in _update_run():
                yield m
        else:
            yield _ev({"log": "Type d'installation inconnu — mets à jour manuellement."})
        yield _ev({"done": True})

    return StreamingResponse(stream(), media_type="text/event-stream")
