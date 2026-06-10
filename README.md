<p align="center">
  <img src="logo/mi-saina-logo.png" alt="mi-saina" width="360">
</p>

> **Langue / Language / Fiteny:** **English** · [Français](README.fr.md) · [Malagasy](README.mg.md)

<h1 align="center">mi-saina — Local AI assistant</h1>

**mi-saina** is a local AI assistant **created by Antsa** that runs **100% on your machine** with [Ollama](https://ollama.com). No data leaves your computer. It has full access to your Linux machine: real-time shell execution, file management, document reading, a document knowledge base (RAG), web search, conversation memory, and external tools (MCP).

> 🐧 **Works on every major Linux distribution** — Arch/EndeavourOS, Debian/Ubuntu, Fedora/RHEL, openSUSE, Void, Alpine. mi-saina **detects your distribution** and automatically uses the right package manager (`pacman`/`paru`, `apt`, `dnf`, `zypper`, `xbps`, `apk`).

---

## ✨ Features

- **100% local LLM via Ollama** — works with any model (Qwen, DeepSeek-R1, Gemma, Phi, Mistral…).
- **Real-time interactive shell** — real commands, live output, interactive `[Y/n]` prompts, sudo password handled securely.
- **Multi-step agent** — the model chains command → result → next command to complete a task.
- **Document reading** — summarize/analyze **PDF, Word (.docx), Excel (.xlsx), PowerPoint (.pptx), CSV** and text/code (attach them, or ask "summarize this PDF: …").
- **Knowledge base (RAG)** — index a folder and ask questions about **your own documents**; relevant passages are retrieved and cited automatically. 100% local.
- **Screen capture → vision** — capture your screen and have a vision model analyze it.
- **Memory** — semantic + full-text search of history, an auto-built user profile, project context files.
- **Isolated sessions** — each conversation is self-contained: no cross-session bleed (a new chat never inherits an unrelated past topic). Semantic recall stays available on demand from the sidebar search.
- **Per-session working folder** — attach a folder to a session (📁 in the header): its shell commands run **inside that folder** and the model uses it for more precise, relative-path answers.
- **Machine profile** — collects your real paths (Downloads, Documents…), home structure and installed tools at first launch, so the assistant acts on the right paths instead of guessing. Refresh anytime in Config → Memory.
- **Health monitor (propose-only)** — periodically checks the system (available updates, failed services, disk, recent errors) and **suggests** actions in a banner. It never runs anything on its own — clicking pre-fills the chat for you to confirm.
- **Configuration map** — deterministic, secret-safe scan of `~/.config` and `~/.local` (configured apps, default apps, your scripts, theme) so the assistant knows your setup: fewer wrong commands, fewer hallucinations, fewer tokens. A compact index is injected; the detail is read on demand. No secrets are ever read.
- **Native desktop window** (Tauri) — app in your application menu, **system-tray icon** at startup, global shortcut, notifications, ⌘K command palette, light/dark/auto theme, artifacts panel.
- **Multilingual** — English, French, Malagasy (UI + assistant replies), chosen at install and changeable in settings.

---

## 🖥️ Hardware requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 8 GB | 16–32 GB |
| GPU | *(optional)* | NVIDIA/AMD 8 GB+ VRAM |
| Storage | 15 GB free | 50 GB+ |
| OS | any recent Linux distribution | — |

> 💡 **No GPU?** Still works: mi-saina detects your RAM and suggests a lighter model. It's just slower.

---

## 🚀 Installation

Two methods.

### Option A — `.run` installer (easiest) ⭐

For users: a single file, no compilation.

```bash
# Download mi-saina-X.Y.Z-x86_64.run from the Releases page, then:
chmod +x mi-saina-*-x86_64.run
./mi-saina-*-x86_64.run        # do NOT run with sudo
```

The installer handles everything: installs **Ollama**, suggests a **model suited to your hardware** and downloads it, installs mi-saina to **`/opt/mi-saina`**, and adds the app to your **application menu** + **session startup** (tray icon). The desktop window **starts the backend itself**. Linux x86_64.

> 📥 Releases: **https://github.com/raantss18/mi-saina/releases**
> Update: from the app, **Config → Settings → Update** (or run a newer `.run`).
> Uninstall: `sudo /opt/mi-saina/uninstall.sh`.

### Option B — From source (developers)

```bash
git clone https://github.com/raantss18/mi-saina.git
cd mi-saina
bash install.sh
```

`install.sh` detects your distro and installs system dependencies, installs & starts Ollama, picks a model for your hardware, creates the Python venv, installs the frontend, sets up systemd user services, and (if Rust + webkit are present) builds the desktop window. At the end, look for **"mi-saina"** in your app menu or open the web URL shown (default **http://localhost:3001**).

> Force ports: `BACKEND_PORT=8010 FRONTEND_PORT=3010 bash install.sh`. Skip the desktop build: `MISAINA_NO_DESKTOP=1 bash install.sh`.

---

## 🎮 Usage

### Desktop window (recommended)
After install, mi-saina is a real app: launch **"mi-saina"** from your menu (native window, not the browser). A **tray icon** appears at session startup — **click it to open the window**. Closing the window minimizes it to the tray; quit via tray → *Quit*. Shortcuts: **Ctrl+Alt+M** (show/hide), **Ctrl/⌘+K** (command palette), **Ctrl/⌘+B** (toggle sidebar).

### Talk naturally
- *"Update my system"*, *"Create a `project` folder in my home"*, *"Find and open my blockchain PDF"*, *"Summarize this PDF: …"*, *"What do my notes say about X?"* (after indexing a folder in Config → Memory).

### Directives the agent uses
`[EXEC: cmd]` run a command · `[READ: path]` read a document · `[RAG: query]` search your knowledge base · `[SEARCH: query]` web search · `[REMEMBER: fact]` remember something.

### Skills (`/` shortcuts)
Type `/` in the chat for reusable shortcuts. Create your own in **Config → Skills**.

### Working folder
Click **📁** in the chat header to attach a folder to the current session. Commands then run inside it, so you can say *"list the files here"* or *"build this project"* without repeating the full path.

---

## Prompt examples

mi-saina classifies each request (**SIMPLE / INTERMEDIATE / COMPLEX**) to decide whether to *think*, decompose into sub-tasks, and how much context to pull. Simple questions answer fast with **thinking off**; complex ones are decomposed and run through a **ReAct loop** (act → observe real output → continue).

### For Linux users (general public)

| Prompt | What mi-saina does | Minimum GPU |
|--------|--------------------|-------------|
| *"Show disk usage and the biggest folders in my home"* | Runs `df -h` / `du` and summarizes the heaviest folders | Any GPU / CPU (4 GB) |
| *"What's the command to list active systemd services?"* | Answers directly (thinking off, ~1–5 s) | Any GPU / CPU (4 GB) |
| *"Update my system"* | Detects your package manager and runs the right upgrade, you confirm | Any GPU / CPU (4 GB) |
| *"Find and open my invoice PDF"* | Locates the file by keyword and opens it | 6–8 GB (RTX 3060/4060) |
| *"Summarize this PDF: …"* | Reads the document and gives the key points | 6–8 GB (RTX 3060/4060) |
| *"Tidy my Downloads folder"* | Lists the real folder and proposes an organization plan | 6–8 GB (RTX 3060/4060) |
| *"My nginx won't start after the update — diagnose and fix it"* | Inspects logs/units, proposes and (on confirm) applies a fix, verifies | 8 GB+ (RTX 4060+) |
| *"Analyze my systemd logs from the last 24h, list every failed service and give a remediation plan for each"* | Decomposes into sub-tasks, diagnoses each service, builds an ordered plan | 8 GB+ (RTX 4060+) |

### For developers / sysadmins

What sets mi-saina apart from `shell-gpt`, Aider or Continue.dev: it **acts on the real system in a ReAct loop** and **knows your machine** (real paths, configured apps), all **100 % local**.

**1. Visible ReAct loop with real output at each step**
- Prompt: *"Why is my system slow right now? Investigate and fix what you can."*
- Behind the scenes: classified COMPLEX → `[EXEC: ps aux --sort=-%mem | head]` → **real output injected** → reasons on it → `[EXEC: systemctl --failed]` → continues until it concludes. Destructive steps require confirmation.
- Why a plain LLM fails: it would *guess* the cause from training data; mi-saina reasons on **your** actual process table and unit states.

**2. RAG over live system context**
- Prompt: *"What do my notes say about the VPN setup?"* (after indexing a folder in Config → Memory)
- Behind the scenes: semantic search over your indexed docs (nomic-embed, SQLite) → top chunks (score ≥ 0.55) injected → answer cites the source files. No raw dump, budget-bounded.

**3. Multi-service causal diagnosis**
- Prompt: *"nginx, php-fpm and postgres are flaky after the upgrade — find the root cause."*
- Behind the scenes: decomposed per service; each sub-agent runs with **fresh, minimal context** (fits 8 GB VRAM), shares only the concrete successful commands; cross-references unit states and logs.
- Why a plain LLM fails: a single mega-prompt overruns the 9B and times out (measured > 170 s); decomposition makes each step tractable.

**4. Bash script generation with built-in verification**
- Prompt: *"Write a backup script for my ~/projects to an external drive, with a dry-run and a rollback note."*
- Behind the scenes: generates the script via `[EXEC: cat > … <<'EOF'` , then **runs a dry-run** and shows the result before you commit — generate → verify, not generate-and-hope.

> Tip: set the response style and reasoning in **Config → Settings** (`THINK = auto/on/off`). In `auto`, thinking is turned **off for simple queries** automatically.

---

## ⚙️ Configuration

In **Config**: system prompt, skills, **memory** (global context, profile, **document knowledge base / RAG**), and **settings** (confirmation mode, agent steps, context window, reasoning/`think`, **language**, automatic memory, software update, autostart…). Change the model anytime in **⬡ Models** (download from Ollama Hub, update, delete, or **import from LM Studio**).

Root commands ask for your sudo password in a dedicated dialog — passwords are never stored or sent.

---

## 🔒 Privacy & security

Everything is local: the backend listens on **127.0.0.1 only**, validates request origins (anti-CSWSH/CSRF), blocks catastrophic commands, and asks confirmation before destructive ones. Your documents, conversations, memory and profile stay on your machine and are never versioned.

---

## 🛠️ Troubleshooting

- Backend logs: `journalctl --user -u mi-saina-backend -n 50`
- Restart: `systemctl --user restart mi-saina-backend mi-saina-frontend`
- Manual start (no systemd): `bash start.sh`
- Model "not found": pick an installed model in **⬡ Models**.

---

## 📄 License

Created by **Antsa**. See the repository for license details.
