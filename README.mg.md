<p align="center">
  <img src="logo/mi-saina-logo.png" alt="mi-saina" width="360">
</p>

> **Langue / Language / Fiteny:** [English](README.md) · [Français](README.fr.md) · **Malagasy**

<h1 align="center">mi-saina — Mpanampy AI an-toerana</h1>

**mi-saina** dia mpanampy AI an-toerana **noforonin'i Antsa**, mandeha **100% ao amin'ny milinanao** miaraka amin'ny [Ollama](https://ollama.com). Tsy misy angona mivoaka mankany amin'ny rahona. Manana fidirana feno amin'ny milina Linux-nao izy: fanatanterahana baiko shell amin'ny fotoana tena izy, fitantanana rakitra, famakiana antontan-taratasy, banky angona (RAG), fikarohana an-tserasera, fitadidiana resaka, ary fitaovana ivelany (MCP).

> 🐧 **Mandeha amin'ny fizarana Linux lehibe rehetra** — Arch/EndeavourOS, Debian/Ubuntu, Fedora/RHEL, openSUSE, Void, Alpine. Mahafantatra ny fizaranao i mi-saina ka mampiasa ho azy ny mpitantana fonosana mety (`pacman`/`paru`, `apt`, `dnf`, `zypper`, `xbps`, `apk`).

---

## ✨ Endrika

- **LLM an-toerana 100% amin'ny Ollama** — miasa amin'ny modely rehetra (Qwen, DeepSeek-R1, Gemma, Phi, Mistral…).
- **Shut interaktif amin'ny fotoana tena izy** — baiko marina, vokatra mivoaka mivantana, fanontaniana `[Y/n]`, tenimiafina sudo voahaja.
- **Agent miasa an-dingana maro** — mampifandray baiko → valiny → baiko manaraka mba hahavita asa.
- **Famakiana antontan-taratasy** — mamintina/mandinika **PDF, Word (.docx), Excel (.xlsx), PowerPoint (.pptx), CSV** sy lahatsoratra/kaody (ampidiro izy, na angataho "fintino ity PDF ity: …").
- **Banky angona (RAG)** — alaharo lahatahiry iray ary manontania momba ny **antontan-taratasinao manokana**; tadiavina sy lazaina ho azy ny andalana mifanaraka. An-toerana 100%.
- **Sary efijery → fahitana** — alaivo sary ny efijery ary asaivo dinihin'ny modely vision.
- **Fitadidiana** — fikarohana ara-dikany sy lahatsoratra feno, profil mpampiasa mihamitombo ho azy, rakitra tontolon'ny tetikasa.
- **Session mitokana** — mahaleo tena ny resaka tsirairay: tsy mifangaro ny session (ny resaka vaovao tsy mandova lohahevitra taloha tsy misy ifandraisany). Mbola azo atao ny fikarohana ara-dikany rehefa ilaina, ao amin'ny barre latérale.
- **Lahatahiry fiasana isaky ny session** — afaka mametaka lahatahiry amin'ny session (📁 ao amin'ny lohateny): ny baiko shell-ny dia tanterahina **ao anatin'io lahatahiry io** ary ampiasain'ny modely mba ho marina kokoa ny valiny (lalana mifandraika).
- **Mombamomba ny milina** — angonina amin'ny fiantombohana voalohany ny lalanao marina (Téléchargements, Documents…), ny firafitry ny home sy ny fitaovana voapetraka, mba hiasan'ny mpanampy amin'ny lalana marina fa tsy maminavina. Bokotra « Havaozy » ao amin'ny Config → Mémoire.
- **Fanaraha-maso fahasalamana (manolotra ihany)** — manamarina tsindraindray ny rafitra (fanavaozana, serivisy tsy mandeha, kapila, hadisoana vao haingana) ary **manolotra** hetsika. Tsy manatanteraka na inona na inona irery — manindry dia mameno ny resaka mba hanamarinanao.
- **Fenetra desktop** (Tauri) — fampiharana ao amin'ny menu, kisary ao amin'ny barre système rehefa miditra, hitsin-dalana, fampandrenesana, palette baiko ⌘K, loko mazava/maizina/auto, panneau artefacta.
- **Fiteny maro** — Anglisy, Frantsay, Malagasy (UI + valin'ny mpanampy), safidiana rehefa mametraka ary azo ovaina ao amin'ny konfigirasiona.

---

## 🖥️ Fepetra fitaovana

| Singa | Faran'ny kely | Hatsaraina |
|-------|----------------|------------|
| RAM | 8 GB | 16–32 GB |
| GPU | *(tsy voatery)* | NVIDIA/AMD 8 GB+ VRAM |
| Fitehirizana | 15 GB malalaka | 50 GB+ |
| OS | fizarana Linux vaovao rehetra | — |

> 💡 **Tsy manana GPU?** Mandeha ihany: mahita ny RAM-nao i mi-saina ka manolotra modely maivana kokoa. Miadana fotsiny.

---

## 🚀 Fametrahana

Roa ny fomba.

### Safidy A — installeur `.run` (mora indrindra) ⭐

Ho an'ny mpampiasa: rakitra tokana, tsy mila fanangonana.

```bash
# Alaivo ny mi-saina-X.Y.Z-x86_64.run ao amin'ny pejy Releases, avy eo:
chmod +x mi-saina-*-x86_64.run
./mi-saina-*-x86_64.run        # AZA ampiasaina amin'ny sudo
```

Mikarakara ny zava-drehetra ny installeur: mametraka **Ollama**, manolotra **modely mifanaraka amin'ny fitaovanao** ary maka azy, mametraka mi-saina ao **`/opt/mi-saina`**, ary manampy ny fampiharana ao amin'ny **menu** + amin'ny **fiantombohan'ny session** (kisary tray). Ny fenetra desktop dia **mandefa ny backend ho azy**. Linux x86_64.

> 📥 Releases: **https://github.com/raantss18/mi-saina/releases**
> Fanavaozana: ao amin'ny app, **Config → Settings → Update** (na alefaso `.run` vaovao kokoa).
> Fanesorana: `sudo /opt/mi-saina/uninstall.sh`.

### Safidy B — avy amin'ny loharano (mpamorona)

```bash
git clone https://github.com/raantss18/mi-saina.git
cd mi-saina
bash install.sh
```

Mahita ny fizaranao i `install.sh` ka mametraka ny zavatra ilaina, mametraka sy mandefa Ollama, misafidy modely, mamorona venv Python, mametraka ny frontend, mametraka serivisy systemd, ary (raha misy Rust + webkit) manangana ny fenetra desktop. Amin'ny farany: tadiavo **"mi-saina"** ao amin'ny menu na sokafy ny URL web aseho (**http://localhost:3001**).

---

## 🎮 Fampiasana

### Fenetra desktop (aroso)
Aorian'ny fametrahana, fampiharana tena izy i mi-saina: alefaso **"mi-saina"** avy amin'ny menu (fenetra natif, fa tsy navigateur). Miseho ao amin'ny tray ny kisary rehefa miditra — **tsindrio izy hisokafan'ny fenetra**. Ny fanidin'ny fenetra dia mampihena azy ho ao amin'ny tray; hivoaka tanteraka: tray → *Quit*. Hitsin-dalana: **Ctrl+Alt+M** (aseho/afeno), **Ctrl/⌘+K** (palette baiko), **Ctrl/⌘+B** (sisiny).

### Miresaka am-pahalalahana
- *"Avaozy ny rafitro"*, *"Mamorona lahatahiry `tetikasa`"*, *"Tadiavo sy sokafy ny PDF blockchain-ko"*, *"Fintino ity PDF ity: …"*, *"Inona no lazain'ny naoticeko momba an'i X?"* (rehefa voalahatra ny lahatahiry ao amin'ny Config → Memory).

### Baiko ampiasain'ny agent
`[EXEC: baiko]` mandefa baiko · `[READ: lalana]` mamaky antontan-taratasy · `[RAG: fanontaniana]` mikaroka ao amin'ny bankinao · `[SEARCH: fanontaniana]` fikarohana web · `[REMEMBER: zavatra]` mitadidy.

### Skills (hitsin-dalana `/`)
Soraty `/` ao amin'ny resaka ho an'ny hitsin-dalana azo averina. Mamorona ny anao ao amin'ny **Config → Skills**.

### Lahatahiry fiasana
Tsindrio ny **📁** ao amin'ny lohatenin'ny resaka mba hametaka lahatahiry amin'ny session ankehitriny. Ny baiko dia tanterahina ao anatiny: azonao lazaina hoe *"lazao ny rakitra eto"* na *"amboary ity tetikasa ity"* nefa tsy mamerina ny lalana feno.

---

## ⚙️ Konfigirasiona

Ao amin'ny **Config**: system prompt, skills, **fitadidiana** (tontolo, profil, **banky angona / RAG**), ary **settings** (fomba fanamarinana, dingana agent, fenetra tontolo, fisainana/`think`, **fiteny**, fitadidiana ho azy, fanavaozana, autostart…). Ovay ny modely ao amin'ny **⬡ Models** (alaina avy amin'ny Ollama Hub, avaozy, fafao, na **ampidiro avy amin'ny LM Studio**).

Ny baiko root dia mangataka ny tenimiafina sudo ao anaty boaty manokana — tsy voatahiry na alefa mihitsy ny tenimiafina.

---

## 🔒 Tsiambaratelo & filaminana

An-toerana ny zava-drehetra: ny backend dia mihaino **127.0.0.1 ihany**, manamarina ny niavian'ny fangatahana (anti-CSWSH/CSRF), manakana ny baiko mampidi-doza, ary mangataka fanamarinana alohan'ny baiko mandrava. Ny antontan-taratasinao, resaka, fitadidiana ary profil dia mijanona ao amin'ny milinanao.

---

## 🛠️ Famahana olana

- Logs backend: `journalctl --user -u mi-saina-backend -n 50`
- Avereno alefa: `systemctl --user restart mi-saina-backend mi-saina-frontend`
- Fandefasana an-tanana (tsy systemd): `bash start.sh`
- Modely "not found": misafidiana modely voapetraka ao amin'ny **⬡ Models**.

---

## 📄 Lisansa

Noforonin'i **Antsa**. Jereo ny depository ho an'ny antsipirihan'ny lisansa.
