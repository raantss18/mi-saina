"""
Vigilance sur la sortie du terminal : détecte des situations connues (verrou
pacman, droits manquants, disque plein, keyring, réseau…) et propose une action
corrective. Utilisé en direct (pendant l'exécution) et dans le retour au modèle.
"""

import re

def _r(pattern: str):
    return re.compile(pattern, re.IGNORECASE)


# Chaque règle : motif regex → libellé, explication, commande corrective suggérée (ou None)
_RULES = [
    # ── Gestion de paquets (Arch/pacman/paru) ──────────────────────────────
    {
        "re": _r(r"could not lock database|Pacman is currently in use|"
                 r"unable to lock database|db\.lck"),
        "label": "Verrou pacman",
        "message": "pacman/paru ne peut pas verrouiller sa base. Si aucun pacman ne tourne, "
                   "le verrou est périmé (mise à jour interrompue).",
        "fix": "pgrep -x pacman >/dev/null && echo 'pacman est actif, patiente' "
               "|| sudo rm -f /var/lib/pacman/db.lck",
    },
    {
        "re": _r(r"signature is unknown trust|invalid or corrupted package|"
                 r"key .* could not be looked up|keyring is not writable|GPGME error"),
        "label": "Clés de signature (keyring)",
        "message": "Trousseau de clés obsolète. Mets à jour archlinux-keyring puis réessaie.",
        "fix": "sudo pacman -Sy --needed archlinux-keyring",
    },
    {
        "re": _r(r"conflicting files|exists in filesystem"),
        "label": "Conflit de fichiers (pacman)",
        "message": "Des fichiers existent déjà. Vérifie le paquet propriétaire avant de forcer "
                   "(--overwrite est risqué).",
        "fix": None,
    },
    {
        "re": _r(r"could not satisfy dependencies|unable to satisfy dependency|"
                 r"breaks dependency"),
        "label": "Dépendances non satisfaites",
        "message": "Conflit/dépendance manquante. Fais d'abord une synchro complète "
                   "(évite les mises à jour partielles).",
        "fix": "paru -Syu",
    },
    {
        "re": _r(r"target not found|paquet .* introuvable|unable to find package|"
                 r"no match for argument"),
        "label": "Paquet introuvable",
        "message": "Nom de paquet incorrect. Cherche le bon nom avant d'installer.",
        "fix": None,
    },
    # ── Réseau ──────────────────────────────────────────────────────────────
    {
        "re": _r(r"failed retrieving file|error: failed to (download|retrieve)|"
                 r"\b404 not found\b|503 service|failed to download"),
        "label": "Échec de téléchargement / miroir",
        "message": "Téléchargement échoué (miroir indisponible). Réessaie ou rafraîchis les miroirs.",
        "fix": None,
    },
    {
        "re": _r(r"could not resolve host|temporary failure in name resolution|"
                 r"name or service not known|dns"),
        "label": "Résolution DNS / réseau",
        "message": "Problème réseau ou DNS. Vérifie la connexion.",
        "fix": "ping -c 2 archlinux.org",
    },
    {
        "re": _r(r"connection refused"),
        "label": "Connexion refusée",
        "message": "Le service/port visé n'écoute pas (service arrêté ou mauvais port).",
        "fix": None,
    },
    {
        "re": _r(r"connection timed out|operation timed out|i/o timeout"),
        "label": "Délai d'attente réseau",
        "message": "Délai dépassé (réseau lent ou hôte injoignable). Réessaie.",
        "fix": None,
    },
    # ── Privilèges / système de fichiers ─────────────────────────────────────
    {
        "re": _r(r"you cannot perform this operation unless you are root|must be root|"
                 r"are you root|operation not permitted|permission denied|eacces"),
        "label": "Privilèges insuffisants",
        "message": "Opération nécessitant les droits root (ou de mauvaises permissions). "
                   "Relance avec sudo si c'est une action système.",
        "fix": None,
    },
    {
        "re": _r(r"no space left on device|espace insuffisant|disk quota exceeded"),
        "label": "Disque plein",
        "message": "Plus d'espace disque. Vérifie l'espace puis nettoie le cache des paquets.",
        "fix": "df -h / && paru -Sc",
    },
    {
        "re": _r(r"read-only file system"),
        "label": "Système de fichiers en lecture seule",
        "message": "La partition est montée en lecture seule (souvent un souci de disque). "
                   "Vérifie les montages et les journaux.",
        "fix": None,
    },
    {
        "re": _r(r"device or resource busy"),
        "label": "Ressource occupée",
        "message": "Le fichier/montage est utilisé par un autre processus.",
        "fix": None,
    },
    {
        "re": _r(r"\bkilled\b|out of memory|oom-killer|cannot allocate memory"),
        "label": "Mémoire insuffisante (OOM)",
        "message": "Processus tué par manque de mémoire. Ferme des applis ou réduis la charge "
                   "(ex. modèle LLM plus léger).",
        "fix": None,
    },
    {
        "re": _r(r"segmentation fault|core dumped|\bsegfault\b"),
        "label": "Plantage (segfault)",
        "message": "Le programme a planté. Vérifie sa version/ses entrées.",
        "fix": None,
    },
    # ── git ───────────────────────────────────────────────────────────────
    {
        "re": _r(r"not a git repository"),
        "label": "Pas un dépôt git",
        "message": "Le dossier courant n'est pas un dépôt git. Place-toi dans le bon dossier "
                   "ou initialise-le.",
        "fix": None,
    },
    {
        "re": _r(r"authentication failed|permission denied \(publickey|"
                 r"could not read username|fatal: could not read"),
        "label": "Authentification git",
        "message": "Identifiants git invalides ou clé SSH absente. Vérifie le token/la clé SSH.",
        "fix": None,
    },
    {
        "re": _r(r"merge conflict|conflict \(content\)|fix conflicts and"),
        "label": "Conflit de fusion git",
        "message": "Conflit de merge. Résous les fichiers en conflit puis valide.",
        "fix": "git status",
    },
    {
        "re": _r(r"updates were rejected|failed to push|tip of your current branch is behind"),
        "label": "Push git rejeté",
        "message": "La branche distante a avancé. Récupère d'abord les changements.",
        "fix": "git pull --rebase",
    },
    {
        "re": _r(r"please commit your changes or stash|your local changes .* would be overwritten"),
        "label": "Modifications git non validées",
        "message": "Des changements locaux bloquent l'opération. Valide-les ou mets-les de côté.",
        "fix": "git stash",
    },
    # ── Python / pip ─────────────────────────────────────────────────────────
    {
        "re": _r(r"modulenotfounderror: no module named ['\"]?([\w\.\-]+)"),
        "label": "Module Python manquant",
        "message": "Un module Python est absent. Installe-le (de préférence dans un venv).",
        "fix": None,
    },
    {
        "re": _r(r"externally-managed-environment"),
        "label": "Environnement Python géré (PEP 668)",
        "message": "pip refuse d'installer en global (Arch). Crée et active un venv.",
        "fix": "python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt",
    },
    {
        "re": _r(r"no matching distribution found|could not find a version that satisfies"),
        "label": "Paquet pip introuvable",
        "message": "Nom ou version de paquet pip incorrect. Vérifie le nom.",
        "fix": None,
    },
    # ── Node / npm ───────────────────────────────────────────────────────────
    {
        "re": _r(r"cannot find module|module not found: error"),
        "label": "Module Node manquant",
        "message": "Dépendance Node absente. Installe les dépendances du projet.",
        "fix": "npm install",
    },
    {
        "re": _r(r"npm err!|enoent.*package\.json|missing script"),
        "label": "Erreur npm",
        "message": "Problème npm (souvent mauvais dossier ou script absent). Vérifie package.json "
                   "et place-toi dans le projet.",
        "fix": None,
    },
    {
        "re": _r(r"eaddrinuse|address already in use|port .* is already in use"),
        "label": "Port déjà utilisé",
        "message": "Le port est occupé par un autre processus. Identifie-le et libère le port.",
        "fix": "ss -tlnp | grep LISTEN",
    },
    # ── Compilation / toolchains ─────────────────────────────────────────────
    {
        "re": _r(r"fatal error: ([\w\./\-]+\.h): no such file|cannot find -l"),
        "label": "En-tête/bibliothèque manquante",
        "message": "Une bibliothèque de développement manque. Installe le paquet -dev/-devel "
                   "correspondant (et base-devel).",
        "fix": None,
    },
    {
        "re": _r(r"linker `cc` not found|error: linker|collect2: error"),
        "label": "Éditeur de liens manquant",
        "message": "Le compilateur C / l'éditeur de liens manque. Installe les outils de build.",
        "fix": "sudo pacman -S --needed base-devel",
    },
    {
        "re": _r(r"could not find `cargo\.toml`|error\[E\d+\]"),
        "label": "Erreur Rust/Cargo",
        "message": "Problème de projet ou de compilation Rust. Place-toi dans le dossier du projet "
                   "et lis l'erreur.",
        "fix": None,
    },
    {
        "re": _r(r"go: cannot find main module|go\.mod file not found"),
        "label": "Module Go manquant",
        "message": "Pas de go.mod ici. Place-toi dans le projet ou initialise le module.",
        "fix": None,
    },
    {
        "re": _r(r"make: .* no targets|make: command not found"),
        "label": "Problème make",
        "message": "make absent ou aucune cible. Installe base-devel / vérifie le Makefile.",
        "fix": None,
    },
    # ── Conteneurs / services ────────────────────────────────────────────────
    {
        "re": _r(r"cannot connect to the docker daemon|is the docker daemon running"),
        "label": "Démon Docker injoignable",
        "message": "Docker n'est pas démarré (ou utilise podman). Démarre le service.",
        "fix": "systemctl status docker",
    },
    {
        "re": _r(r"failed to start|unit .* not found|unit .* could not be found"),
        "label": "Service systemd",
        "message": "Unité systemd introuvable ou échec de démarrage. Vérifie le nom et les logs.",
        "fix": None,
    },
    {
        "re": _r(r"interactive authentication required"),
        "label": "Authentification requise (systemd)",
        "message": "Action systemd système nécessitant sudo (ou utilise --user pour tes services).",
        "fix": None,
    },
    # ── Générique ────────────────────────────────────────────────────────────
    {
        "re": _r(r"command not found|commande introuvable"),
        "label": "Commande introuvable",
        "message": "La commande n'existe pas. Vérifie le nom, ou installe le paquet qui la fournit.",
        "fix": None,
    },
]


def diagnose(text: str) -> list[dict]:
    """Retourne les diagnostics détectés dans `text` (sans doublon de libellé)."""
    found: list[dict] = []
    seen: set[str] = set()
    for rule in _RULES:
        if rule["label"] in seen:
            continue
        if rule["re"].search(text):
            seen.add(rule["label"])
            found.append({"label": rule["label"],
                          "message": rule["message"],
                          "fix": rule["fix"]})
    return found


def format_for_model(diags: list[dict]) -> str:
    """Texte injecté dans le retour au modèle pour qu'il propose la correction."""
    if not diags:
        return ""
    lines = ["[DIAGNOSTIC — la sortie révèle un problème connu]"]
    for d in diags:
        line = f"- {d['label']} : {d['message']}"
        if d["fix"]:
            line += f" Commande corrective suggérée : {d['fix']}"
        lines.append(line)
    lines.append("Propose à l'utilisateur la commande corrective adaptée (via [EXEC: …]).")
    return "\n".join(lines)
