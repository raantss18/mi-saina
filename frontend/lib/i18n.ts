// i18n minimaliste (EN/FR/MG). La langue est persistée dans localStorage['ms-lang']
// et synchronisée avec le réglage backend LANGUAGE. Le changement de langue
// recharge la page (simple et fiable, pas de plomberie de contexte).

export type Lang = "en" | "fr" | "mg";
export const LANGS: { code: Lang; label: string }[] = [
  { code: "en", label: "English" },
  { code: "fr", label: "Français" },
  { code: "mg", label: "Malagasy" },
];

const LANG_KEY = "ms-lang";

export function getLang(): Lang {
  if (typeof window === "undefined") return "en";
  try {
    const v = window.localStorage.getItem(LANG_KEY);
    if (v === "en" || v === "fr" || v === "mg") return v;
  } catch { /* stockage indispo */ }
  return "en";
}

export function setLang(l: Lang): void {
  try { window.localStorage.setItem(LANG_KEY, l); } catch { /* indispo */ }
}

type Dict = Record<string, { en: string; fr: string; mg: string }>;

const T: Dict = {
  // Header / contrôles
  model: { en: "model:", fr: "modèle :", mg: "modely:" },
  modelActiveTip: { en: "Active model — change it in ⬡ Models", fr: "Modèle actif — change-le dans ⬡ Modèles", mg: "Modely mandeha — ovay ao amin'ny ⬡ Modely" },
  rerun: { en: "Rerun last prompt (↺)", fr: "Relancer le dernier prompt (↺)", mg: "Avereno ny baiko farany (↺)" },
  copyResp: { en: "Copy last response", fr: "Copier la dernière réponse", mg: "Adikao ny valiny farany" },
  clearChat: { en: "Clear conversation", fr: "Effacer la conversation", mg: "Fafao ny resaka" },
  terminal: { en: "Terminal", fr: "Terminal", mg: "Terminal" },
  terminalTip: { en: "Show/hide terminal output", fr: "Afficher/masquer la sortie du terminal", mg: "Asehoy/afeno ny terminal" },
  artifacts: { en: "Artifacts", fr: "Artefacts", mg: "Artefacta" },
  artifactsTip: { en: "Show/hide artifacts panel", fr: "Afficher/masquer le panneau d'artefacts", mg: "Asehoy/afeno ny artefacta" },
  paletteTip: { en: "Command palette (Ctrl/⌘ + K)", fr: "Palette de commandes (Ctrl/⌘ + K)", mg: "Palette baiko (Ctrl/⌘ + K)" },
  sidebarTip: { en: "Toggle sidebar (Ctrl/⌘ + B)", fr: "Replier/déplier la barre latérale (Ctrl/⌘ + B)", mg: "Akatona/sokafy ny sisiny (Ctrl/⌘ + B)" },
  connected: { en: "online", fr: "connecté", mg: "mifandray" },
  offline: { en: "offline", fr: "hors ligne", mg: "tsy mifandray" },
  statusRunning: { en: "⟳ running", fr: "⟳ en cours", mg: "⟳ mandeha" },
  statusSuccess: { en: "✓ success", fr: "✓ succès", mg: "✓ vita" },
  statusFailure: { en: "✗ failed", fr: "✗ échec", mg: "✗ tsy nahomby" },
  statusStopped: { en: "■ stopped", fr: "■ arrêté", mg: "■ najanona" },
  // Saisie
  inputPlaceholder: { en: "Message… (Shift+Enter = new line) or /skill for shortcuts", fr: "Message… (Maj+Entrée = nouvelle ligne) ou /skill pour les raccourcis", mg: "Hafatra… (Shift+Enter = andalana vaovao) na /skill ho an'ny hitsin-dalana" },
  attachTip: { en: "Attach a file or image (📎)", fr: "Joindre un fichier ou une image (📎)", mg: "Hampiditra rakitra na sary (📎)" },
  captureTip: { en: "Capture screen and analyze (📷)", fr: "Capturer l'écran et l'analyser (📷)", mg: "Alaivo sary ny efijery hodinihina (📷)" },
  stopTip: { en: "Stop generation (⏹)", fr: "Arrêter la génération (⏹)", mg: "Ajanony ny famoronana (⏹)" },
  // Sidebar / nav
  newSession: { en: "+ New session", fr: "+ Nouvelle session", mg: "+ Session vaovao" },
  newSessionTip: { en: "Start a new blank conversation", fr: "Démarrer une nouvelle conversation vierge", mg: "Manomboka resaka vaovao" },
  navChat: { en: "Chat", fr: "Chat", mg: "Resaka" },
  navModels: { en: "Models", fr: "Modèles", mg: "Modely" },
  navConfig: { en: "Config", fr: "Config", mg: "Konfigirasiona" },
  navTasks: { en: "Tasks", fr: "Tâches", mg: "Asa" },
  noSession: { en: "No session", fr: "Aucune session", mg: "Tsy misy session" },
  workdir: { en: "Folder", fr: "Dossier", mg: "Lahatahiry" },
  workdirSet: { en: "Set a working folder for this session", fr: "Définir un dossier de travail pour cette session", mg: "Mametraka lahatahiry fiasana ho an'ity session ity" },
  workdirActive: { en: "Working folder", fr: "Dossier de travail", mg: "Lahatahiry fiasana" },
  workdirPrompt: { en: "Working folder for this session (commands run here):", fr: "Dossier de travail de cette session (les commandes s'exécutent ici) :", mg: "Lahatahiry fiasan'ity session ity (eto no anatanterahana ny baiko) :" },
  workdirNotFound: { en: "Folder not found", fr: "Dossier introuvable", mg: "Tsy hita ny lahatahiry" },
  historyLabel: { en: "HISTORY", fr: "HISTORIQUE", mg: "TANTARA" },
  histSearch: { en: "SEARCH HISTORY", fr: "RECHERCHE DANS L'HISTORIQUE", mg: "FIKAROHANA TANTARA" },
  semSearch: { en: "SEMANTIC SEARCH", fr: "RECHERCHE SÉMANTIQUE", mg: "FIKAROHANA ARA-DIKANY" },
  // Palette / commandes
  paletteSearch: { en: "Search an action…  (↑↓ to navigate, Enter to run)", fr: "Rechercher une action…  (↑↓ pour naviguer, Entrée pour lancer)", mg: "Hitady hetsika…  (↑↓ hivezivezy, Enter handefa)" },
  paletteEmpty: { en: "No action matches.", fr: "Aucune action ne correspond.", mg: "Tsy misy hetsika mifanaraka." },
  cmdGoChat: { en: "Go to chat", fr: "Aller au chat", mg: "Mankany amin'ny resaka" },
  cmdNewChat: { en: "New conversation", fr: "Nouvelle conversation", mg: "Resaka vaovao" },
  cmdRerun: { en: "Rerun last prompt", fr: "Relancer le dernier prompt", mg: "Avereno ny baiko farany" },
  cmdCopy: { en: "Copy last response", fr: "Copier la dernière réponse", mg: "Adikao ny valiny farany" },
  cmdStop: { en: "Stop generation", fr: "Arrêter la génération", mg: "Ajanony ny famoronana" },
  cmdTerminal: { en: "Show/hide terminal", fr: "Afficher/masquer le terminal", mg: "Asehoy/afeno ny terminal" },
  cmdArtifacts: { en: "Show/hide artifacts", fr: "Afficher/masquer les artefacts", mg: "Asehoy/afeno ny artefacta" },
  cmdPinResp: { en: "Pin last response to artifacts", fr: "Épingler la dernière réponse aux artefacts", mg: "Apetaho amin'ny artefacta ny valiny farany" },
  cmdSidebar: { en: "Toggle sidebar", fr: "Replier/déplier la barre latérale", mg: "Akatona/sokafy ny sisiny" },
  cmdOpenModels: { en: "Open: Models", fr: "Ouvrir : Modèles", mg: "Sokafy: Modely" },
  cmdOpenConfig: { en: "Open: Config", fr: "Ouvrir : Config", mg: "Sokafy: Konfigirasiona" },
  cmdOpenTasks: { en: "Open: Scheduled tasks", fr: "Ouvrir : Tâches planifiées", mg: "Sokafy: Asa voalamina" },
  // Welcome
  welcomeTagline: { en: "Your local AI assistant — it understands, acts on your system, and learns.", fr: "Votre assistant IA local — il comprend, agit sur votre système, et apprend.", mg: "Mpanampy AI an-toerana — mahatakatra, miasa amin'ny rafitrao, ary mianatra." },
  welcomeHi: { en: "👋 Welcome!", fr: "👋 Bienvenue !", mg: "👋 Tongasoa!" },
  welcomeGo: { en: "Let's go", fr: "C'est parti", mg: "Andao isika" },
  tour1: { en: "Describe a task in plain language — mi-saina proposes and runs the commands.", fr: "Décrivez une tâche en langage naturel — mi-saina propose et exécute les commandes.", mg: "Lazao amin'ny teny tsotra ny asa — mi-saina manolotra sy manatanteraka ny baiko." },
  tour2: { en: "Sensitive commands ask for your confirmation before running.", fr: "Les commandes sensibles demandent votre validation avant de s'exécuter.", mg: "Mangataka fankatoavanao alohan'ny hanatanterahana ny baiko saro-pady." },
  tour3: { en: "Open the command palette with Ctrl+K.", fr: "Ouvrez la palette d'actions avec Ctrl+K.", mg: "Sokafy ny palette baiko amin'ny Ctrl+K." },
  tour4: { en: "Type / for your shortcuts (skills); the ▣ Terminal panel shows raw output.", fr: "Tapez / pour vos raccourcis (skills) ; le panneau ▣ Terminal montre la sortie brute.", mg: "Soraty / ho an'ny hitsin-dalana; ny ▣ Terminal mampiseho ny vokatra." },
  welcomeTry: { en: "Try an example", fr: "Essayez un exemple", mg: "Andramo ohatra iray" },
  exUpdate: { en: "Update my system", fr: "Mets à jour mon système", mg: "Avaozy ny rafitro" },
  exUpdateD: { en: "Upgrade all packages safely", fr: "Met à niveau tous les paquets en sécurité", mg: "Hatsarao ny fonosana rehetra" },
  exUpdateP: { en: "Update my system", fr: "Mets à jour mon système", mg: "Avaozy ny rafitro" },
  exWeb: { en: "Summarize a web page", fr: "Résume une page web", mg: "Fintino pejy web" },
  exWebD: { en: "Fetch a URL and give the key points", fr: "Récupère une URL et donne l'essentiel", mg: "Alaivo ny URL ka omeo ny votoatiny" },
  exWebP: { en: "Summarize this page: https://", fr: "Résume cette page : https://", mg: "Fintino ity pejy ity: https://" },
  exDisk: { en: "Diagnose my disk", fr: "Diagnostique mon disque", mg: "Dinihio ny kapila" },
  exDiskD: { en: "See usage and the biggest folders", fr: "Voir l'espace et les plus gros dossiers", mg: "Jereo ny kapila sy ny lahatahiry lehibe" },
  exDiskP: { en: "Show disk usage and the biggest folders in my home", fr: "Montre l'espace disque utilisé et les plus gros dossiers de mon /home", mg: "Asehoy ny kapila sy ny lahatahiry lehibe indrindra ao amin'ny home" },
  exFind: { en: "Find a file", fr: "Cherche un fichier", mg: "Mitady rakitra" },
  exFindD: { en: "Locate and open it for you", fr: "Le localise et l'ouvre pour vous", mg: "Tadiavo ka sokafy ho anao" },
  exFindP: { en: "Find and open the file ", fr: "Trouve et ouvre le fichier ", mg: "Tadiavo sy sokafy ny rakitra " },
  exPkg: { en: "Install a package", fr: "Installe un paquet", mg: "Apetraho fonosana" },
  exPkgD: { en: "With your distro's package manager", fr: "Avec le gestionnaire de votre distro", mg: "Amin'ny mpitantana fonosanao" },
  exPkgP: { en: "Install the package ", fr: "Installe le paquet ", mg: "Apetraho ny fonosana " },
  exDocs: { en: "Tidy my Downloads", fr: "Range mes Téléchargements", mg: "Alamino ny Téléchargements" },
  exDocsD: { en: "List and suggest how to clean up", fr: "Liste et propose un rangement", mg: "Lazao ka manolora fandaminana" },
  exDocsP: { en: "List my Downloads folder and suggest how to tidy it", fr: "Liste mon dossier Téléchargements et propose un rangement", mg: "Lazao ny ao amin'ny Téléchargements ka manolora fandaminana" },
  // Artefacts
  artTitle: { en: "Artifacts", fr: "Artefacts", mg: "Artefacta" },
  artEmpty: { en: "Generated code blocks will appear here.", fr: "Les blocs de code générés apparaîtront ici.", mg: "Hiseho eto ny kaody noforonina." },
  artCopy: { en: "Copy", fr: "Copier", mg: "Adikao" },
  artDownload: { en: "Download", fr: "Télécharger", mg: "Alaina" },
  artRemove: { en: "Remove", fr: "Retirer", mg: "Esory" },
  artClear: { en: "Clear", fr: "Vider", mg: "Fafao" },

  // Commun
  success: { en: "success", fr: "succès", mg: "vita" },
  save: { en: "Save", fr: "Sauvegarder", mg: "Tehirizo" },
  cancel: { en: "Cancel", fr: "Annuler", mg: "Foano" },
  saved: { en: "✓ Saved", fr: "✓ Enregistré", mg: "✓ Voatahiry" },

  // ChatWindow
  chRunning: { en: "Running…", fr: "Exécution en cours…", mg: "Manatanteraka…" },
  chDetails: { en: "— details in ▣ Terminal", fr: "— détails dans ▣ Terminal", mg: "— antsipiriany ao ▣ Terminal" },
  chDone: { en: "✓ Command finished", fr: "✓ Commande terminée", mg: "✓ Vita ny baiko" },
  chFailed: { en: "✗ Failed — see ▣ Terminal for details", fr: "✗ Échec — voir ▣ Terminal pour le détail", mg: "✗ Tsy nahomby — jereo ▣ Terminal" },
  chReplyPrompt: { en: "Reply to the prompt (e.g. y, n, Enter)…", fr: "Répondre au prompt (ex: y, n, Enter)...", mg: "Valio ny fanontaniana (oh. y, n, Enter)…" },
  chEnterProcess: { en: "Enter for the process…", fr: "Entrée pour le processus...", mg: "Enter ho an'ny process…" },
  chSendEmpty: { en: "Send empty Enter", fr: "Envoyer Entrée vide", mg: "Alefaso Enter foana" },
  chYes: { en: "Reply Yes", fr: "Répondre Oui", mg: "Valio Eny" },
  chNo: { en: "Reply No", fr: "Répondre Non", mg: "Valio Tsia" },
  chReady: { en: "mi-saina ready", fr: "mi-saina prêt", mg: "mi-saina vonona" },
  chReadyHint: { en: "Commands run live — real-time output, interactive prompts", fr: "Commandes exécutées en direct — sortie en temps réel, prompts interactifs", mg: "Baiko atao mivantana — vokatra amin'ny fotoana, fanontaniana interaktif" },
  untitledSession: { en: "Untitled session", fr: "Session sans titre", mg: "Session tsy misy lohateny" },

  // TerminalPanel
  tpReady: { en: "ready", fr: "prêt", mg: "vonona" },
  tpRunningTask: { en: "task running…", fr: "tâche en cours…", mg: "asa mandeha…" },
  tpDoneOk: { en: "done · success", fr: "terminé · succès", mg: "vita · nahomby" },
  tpDoneFail: { en: "done · failed", fr: "terminé · échec", mg: "vita · tsy nahomby" },
  tpStopped: { en: "stopped", fr: "arrêté", mg: "najanona" },
  tpClose: { en: "Close terminal", fr: "Fermer le terminal", mg: "Akatona ny terminal" },
  tpEmpty: { en: "No command run yet.", fr: "Aucune commande exécutée pour l'instant.", mg: "Tsy mbola nisy baiko natao." },
  tpEmptyHint: { en: "Command output will appear here in real time.", fr: "La sortie des commandes apparaîtra ici en temps réel.", mg: "Hiseho eto amin'ny fotoana ny vokatry ny baiko." },
  tpRunningShort: { en: "running…", fr: "en cours…", mg: "mandeha…" },
  tpLogicalFail: { en: "logical failure (rc=0)", fr: "échec logique (rc=0)", mg: "tsy nahomby ara-dalàna (rc=0)" },
  tpWaiting: { en: "The process is waiting for input (e.g. y, n, Enter)…", fr: "Le processus attend une réponse (ex: y, n, Entrée)…", mg: "Miandry valiny ny process (oh. y, n, Enter)…" },

  // ModelPanel
  mpHeader: { en: "OLLAMA MODELS", fr: "MODÈLES OLLAMA", mg: "MODELY OLLAMA" },
  mpRefresh: { en: "↻ refresh", fr: "↻ rafraîchir", mg: "↻ avaozy" },
  mpLoading: { en: "Loading models…", fr: "Chargement des modèles…", mg: "Maka ny modely…" },
  mpActive: { en: "ACTIVE", fr: "ACTIF", mg: "MANDEHA" },
  mpActivate: { en: "Activate", fr: "Activer", mg: "Alefaso" },
  mpActivateTip: { en: "Use this model for replies", fr: "Utiliser ce modèle pour les réponses", mg: "Ampiasao ity modely ity ho an'ny valiny" },
  mpUpdateTip: { en: "Check and download updates", fr: "Vérifier et télécharger les mises à jour", mg: "Hamarino sy alaina ny fanavaozana" },
  mpDeleteTip: { en: "Delete this model", fr: "Supprimer ce modèle", mg: "Fafao ity modely ity" },
  mpUpdating: { en: "↻ Update", fr: "↻ Mise à jour", mg: "↻ Fanavaozana" },
  mpDownloading: { en: "↓ Download", fr: "↓ Téléchargement", mg: "↓ Maka" },
  mpImportLabel: { en: "⇪ Import LM Studio", fr: "⇪ Import LM Studio", mg: "⇪ Import LM Studio" },
  mpDownloadHub: { en: "DOWNLOAD FROM OLLAMA HUB", fr: "TÉLÉCHARGER DEPUIS OLLAMA HUB", mg: "MAKA AVY AMIN'NY OLLAMA HUB" },
  mpPullPlaceholder: { en: "e.g. phi4-mini, llama3.2:3b…", fr: "ex: phi4-mini, llama3.2:3b...", mg: "oh. phi4-mini, llama3.2:3b…" },
  mpPullTip: { en: "Download this model from Ollama Hub", fr: "Télécharger ce modèle depuis Ollama Hub", mg: "Maka ity modely ity avy amin'ny Ollama Hub" },
  mpImportBtn: { en: "⇪ Import my LM Studio models", fr: "⇪ Importer mes modèles LM Studio", mg: "⇪ Ampidiro ny modely LM Studio-ko" },
  mpImportTip: { en: "Import into Ollama all GGUF models found in LM Studio (~/.lmstudio/models)", fr: "Importer dans Ollama tous les modèles GGUF présents dans LM Studio (~/.lmstudio/models)", mg: "Ampidiro ao Ollama ny GGUF rehetra ao LM Studio (~/.lmstudio/models)" },
  mpLegend: { en: "↻ = check/download updates • 🗑 = delete (frees disk)", fr: "↻ = vérifier/télécharger les mises à jour • 🗑 = supprimer (libère l'espace disque)", mg: "↻ = hamarino/alaina fanavaozana • 🗑 = fafao (manafaka disque)" },
  mpNetErr: { en: "Network error", fr: "Erreur réseau", mg: "Hadisoana tambajotra" },
  mpCantStart: { en: "Could not start the operation", fr: "Impossible de lancer l'opération", mg: "Tsy afaka nanomboka" },
  mpImportErr: { en: "LM Studio import failed", fr: "Import LM Studio impossible", mg: "Tsy afaka nampiditra LM Studio" },
  mpSuggested: { en: "SUGGESTED MODELS (popular)", fr: "MODÈLES SUGGÉRÉS (populaires)", mg: "MODELY ATOLOTRA (malaza)" },
  mpCompatible: { en: "fits your hardware", fr: "compatible avec ta machine", mg: "mifanaraka amin'ny milinanao" },
  mpInstalledTag: { en: "installed", fr: "installé", mg: "voapetraka" },
  mpGet: { en: "Get", fr: "Obtenir", mg: "Alaina" },

  // SchedulePanel
  spIntro: { en: "Local scheduled tasks. Run in the background without UI: only safe commands run (no root, no deletion). The result is saved in a '⏰' session.", fr: "Tâches planifiées (locales). Exécutées en arrière-plan sans interface : seules les commandes sûres tournent (ni root, ni suppression). Le résultat est sauvé dans une session « ⏰ ».", mg: "Asa voalamina an-toerana. Mandeha ao ambadika tsy misy UI: ny baiko azo antoka ihany no mandeha (tsy root, tsy famafana). Voatahiry ao amin'ny session '⏰' ny valiny." },
  spEmpty: { en: "No scheduled task.", fr: "Aucune tâche planifiée.", mg: "Tsy misy asa voalamina." },
  spEmptyHint: { en: "Create a recurring task below (e.g. summarize updates every morning).", fr: "Crée une tâche récurrente ci-dessous (ex : résumer les mises à jour chaque matin).", mg: "Mamorona asa miverimberina etsy ambany (oh. mamintina fanavaozana isa-maraina)." },
  spActive: { en: "active", fr: "actif", mg: "mandeha" },
  spInactive: { en: "inactive", fr: "inactif", mg: "tsy mandeha" },
  spEnable: { en: "Enable", fr: "Activer", mg: "Alefaso" },
  spDisable: { en: "Disable", fr: "Désactiver", mg: "Vonoy" },
  spRunNow: { en: "Run now", fr: "Exécuter maintenant", mg: "Tanteraho izao" },
  spNever: { en: "never run", fr: "jamais exécuté", mg: "tsy mbola natao" },
  spLast: { en: "last", fr: "dernier", mg: "farany" },
  spOpenResult: { en: "Open result", fr: "Ouvrir le résultat", mg: "Sokafy ny valiny" },
  spNamePlaceholder: { en: "Task name", fr: "Nom de la tâche", mg: "Anaran'ny asa" },
  spPromptPlaceholder: { en: "What should mi-saina do? (e.g. list available updates and summarize)", fr: "Que doit faire mi-saina ? (ex : liste les mises à jour disponibles et résume)", mg: "Inona no tokony hataon'i mi-saina? (oh. lazao ny fanavaozana misy ka fintino)" },
  spEveryX: { en: "Every X min", fr: "Toutes les X min", mg: "Isaky ny X minitra" },
  spDaily: { en: "Every day", fr: "Chaque jour", mg: "Isan'andro" },
  spWeekly: { en: "Every week", fr: "Chaque semaine", mg: "Isan-kerinandro" },
  spCreate: { en: "Create", fr: "Créer", mg: "Foronina" },
  spNewTask: { en: "+ New scheduled task", fr: "+ Nouvelle tâche planifiée", mg: "+ Asa voalamina vaovao" },
  spDeleteConfirm: { en: "Delete this task?", fr: "Supprimer cette tâche ?", mg: "Fafao ity asa ity?" },

  // ConfigPanel — onglets + hints
  cfTabPrompt: { en: "System Prompt", fr: "System Prompt", mg: "System Prompt" },
  cfTabSkills: { en: "Skills", fr: "Skills", mg: "Skills" },
  cfTabMemory: { en: "Memory", fr: "Mémoire", mg: "Fitadidiana" },
  cfTabSettings: { en: "Settings", fr: "Réglages", mg: "Fandrindrana" },
  cfHintPrompt: { en: "Base instructions sent to the model in every conversation", fr: "Instructions de base envoyées au modèle à chaque conversation", mg: "Toromarika fototra alefa amin'ny modely isaky ny resaka" },
  cfHintSkills: { en: "Reusable slash-command shortcuts (e.g. /update)", fr: "Raccourcis slash-command réutilisables (ex : /update)", mg: "Hitsin-dalana slash azo averina (oh. /update)" },
  cfHintMemory: { en: "Global context and user profile injected automatically", fr: "Contexte global et profil utilisateur injectés automatiquement", mg: "Tontolo sy profil mpampiasa ampidirina ho azy" },
  cfHintSettings: { en: "Agent behavior: confirmations, context, planner…", fr: "Comportement de l'agent : confirmations, contexte, planificateur…", mg: "Fitondran-tena agent: fanamarinana, tontolo, mpandrindra…" },
  cfHintModels: { en: "Download, update, delete models; import from LM Studio", fr: "Télécharger, mettre à jour, supprimer des modèles ; importer depuis LM Studio", mg: "Maka, manavao, mamafa modely; mampiditra avy amin'ny LM Studio" },
  selectModelTip: { en: "Active model — pick another to switch", fr: "Modèle actif — choisis-en un autre pour changer", mg: "Modely mandeha — misafidiana iray hafa" },
  manageModels: { en: "⚙ Manage models…", fr: "⚙ Gérer les modèles…", mg: "⚙ Hitantana modely…" },
  cfPromptIntro: { en: "Base instructions sent with every prompt, for all models.", fr: "Instructions de base envoyées à chaque prompt, pour tous les modèles.", mg: "Toromarika fototra alefa isaky ny prompt, ho an'ny modely rehetra." },
  cfSaving: { en: "Saving...", fr: "Sauvegarde...", mg: "Mitahiry..." },
  cfSavedOk: { en: "✓ Saved", fr: "✓ Sauvegardé", mg: "✓ Voatahiry" },
  cfUnsaved: { en: "● Unsaved changes", fr: "● Modifications non sauvegardées", mg: "● Fanovàna tsy voatahiry" },
  cfSkillsIntro: { en: "Skills = slash-command shortcuts. Type", fr: "Skills = raccourcis slash-command. Tapez", mg: "Skills = hitsin-dalana slash. Soraty" },
  cfSkillsIntro2: { en: "in the chat to invoke them.", fr: "dans le chat pour les invoquer.", mg: "ao amin'ny resaka mba hampiasa azy." },
  cfEdit: { en: "Edit", fr: "Éditer", mg: "Ovay" },
  cfNewSkill: { en: "+ New skill", fr: "+ Nouveau skill", mg: "+ Skill vaovao" },
  cfNewSkillTitle: { en: "New skill", fr: "Nouveau skill", mg: "Skill vaovao" },
  cfEditTitle: { en: "Edit:", fr: "Éditer:", mg: "Ovay:" },
  cfIcon: { en: "Icon", fr: "Icône", mg: "Kisary" },
  cfName: { en: "Name", fr: "Nom", mg: "Anarana" },
  cfTrigger: { en: "Trigger", fr: "Trigger", mg: "Trigger" },
  cfDescription: { en: "Description", fr: "Description", mg: "Famaritana" },
  cfPrompt: { en: "Prompt", fr: "Prompt", mg: "Prompt" },
  cfSkillPromptPlaceholder: { en: "Instructions sent to the LLM when this skill is invoked…", fr: "Instructions envoyées au LLM quand ce skill est invoqué...", mg: "Toromarika alefa amin'ny LLM rehefa ampiasaina ity skill ity…" },
  cfSkillDelete: { en: "Delete the skill", fr: "Supprimer le skill", mg: "Fafao ny skill" },
  cfMemIntro: { en: "These local notes (~/.config/mi-saina/) are injected automatically into every conversation. Never versioned.", fr: "Ces notes locales (~/.config/mi-saina/) sont injectées automatiquement dans chaque conversation. Jamais versionnées.", mg: "Ireo naoty an-toerana (~/.config/mi-saina/) dia ampidirina ho azy isaky ny resaka. Tsy versioné mihitsy." },
  cfGlobalCtx: { en: "Global context (context.md)", fr: "Contexte global (context.md)", mg: "Tontolo (context.md)" },
  cfGlobalCtxHint: { en: "Who you are, your machine, your habits — persistent instructions.", fr: "Qui tu es, ta machine, tes habitudes — instructions persistantes.", mg: "Iza ianao, ny milinanao, ny fahazaranao — toromarika maharitra." },
  cfCtxPlaceholder: { en: "E.g.: I'm a math teacher, my LaTeX projects are in ~/Documents, reply concisely.", fr: "Ex : Je suis prof de maths, mes projets LaTeX sont dans ~/Documents/GitHub, réponds en français concis.", mg: "Oh.: Mpampianatra matematika aho, ao ~/Documents ny tetikasako, valio fohifohy." },
  cfProfile: { en: "Remembered profile (profile.md)", fr: "Profil mémorisé (profile.md)", mg: "Profil voatadidy (profile.md)" },
  cfProfileHint: { en: "Preferences learned automatically. Editable by hand.", fr: "Préférences apprises automatiquement (via [REMEMBER: …]). Modifiable à la main.", mg: "Safidy nianarana ho azy. Azo ovaina an-tanana." },
  cfProfilePlaceholder: { en: "(empty — fills in as mi-saina remembers your preferences)", fr: "(vide — se remplit quand mi-saina mémorise tes préférences)", mg: "(foana — feno rehefa mitadidy ny safidinao i mi-saina)" },
  cfSettingsIntro: { en: "Applied immediately and persisted (~/.config/mi-saina/settings.json), no restart.", fr: "Appliqués immédiatement et persistés (~/.config/mi-saina/settings.json), sans redémarrage.", mg: "Ampiharina avy hatrany sy voatahiry (~/.config/mi-saina/settings.json), tsy mila averina alefa." },
  cfLoading: { en: "Loading…", fr: "Chargement…", mg: "Maka…" },
  cfRange: { en: "range", fr: "plage", mg: "elanelana" },
  // ConfigPanel — update + autostart + RAG
  cfUpdSource: { en: "Source:", fr: "Source :", mg: "Loharano:" },
  cfUpdRun: { en: ".run installer (/opt)", fr: "installeur .run (/opt)", mg: "installeur .run (/opt)" },
  cfUpdGit: { en: "source code (git)", fr: "code source (git)", mg: "kaody loharano (git)" },
  cfUpdAuto: { en: "The update is applied automatically.", fr: "La mise à jour est appliquée automatiquement.", mg: "Ampiharina ho azy ny fanavaozana." },
  cfUpdAvail: { en: "update available", fr: "maj dispo", mg: "fanavaozana misy" },
  cfUpToDate: { en: "✓ up to date", fr: "✓ à jour", mg: "✓ vaovao" },
  cfUpdUnknown: { en: "online version unknown", fr: "version en ligne inconnue", mg: "tsy fantatra ny version an-tserasera" },
  cfCheck: { en: "↻ Check", fr: "↻ Vérifier", mg: "↻ Hamarino" },
  cfChecking: { en: "Checking…", fr: "Vérification…", mg: "Manamarina…" },
  cfUpdateBtn: { en: "⬆ Update", fr: "⬆ Mettre à jour", mg: "⬆ Avaozy" },
  cfUpdating: { en: "Updating…", fr: "Mise à jour…", mg: "Manavao…" },
  cfUpdateTip: { en: "Download and install the update", fr: "Télécharger et installer la mise à jour", mg: "Alaina sy apetraka ny fanavaozana" },
  cfNoUpdateTip: { en: "No update available", fr: "Aucune mise à jour disponible", mg: "Tsy misy fanavaozana" },
  cfAutostart: { en: "Launch at session startup", fr: "Lancer au démarrage de la session", mg: "Alefaso rehefa miditra" },
  cfAutostartHint: { en: "Start mi-saina automatically (minimized to the system tray) at login.", fr: "Démarre mi-saina automatiquement (réduit dans la barre système) à l'ouverture de session.", mg: "Mandefa mi-saina ho azy (kely ao amin'ny tray) rehefa miditra." },
  cfRagTitle: { en: "📚 Knowledge base (RAG)", fr: "📚 Base documentaire (RAG)", mg: "📚 Banky angona (RAG)" },
  cfRagHint: { en: "Index a folder (PDF, Word, Excel, PowerPoint, text). mi-saina can answer from your documents via", fr: "Indexe un dossier (PDF, Word, Excel, PowerPoint, texte). mi-saina pourra répondre à partir de tes documents via", mg: "Alaharo lahatahiry (PDF, Word, Excel, PowerPoint, lahatsoratra). Afaka mamaly avy amin'ny antontan-taratasinao i mi-saina amin'ny" },
  cfRagLocal: { en: "100% local (embeddings", fr: "100 % local (embeddings", mg: "100% an-toerana (embeddings" },
  cfRagFiles: { en: "file(s)", fr: "fichier(s)", mg: "rakitra" },
  cfRagChunks: { en: "indexed extract(s).", fr: "extrait(s) indexés.", mg: "sombiny voalahatra." },
  cfRagFolderPlaceholder: { en: "Folder path, e.g. ~/Documents/Courses", fr: "Chemin d'un dossier, ex: /home/raantss/Documents/Cours", mg: "Lalan'ny lahatahiry, oh. ~/Documents/Cours" },
  cfRagIndex: { en: "Index", fr: "Indexer", mg: "Alaharo" },
  cfRagIndexing: { en: "Indexing…", fr: "Indexation…", mg: "Mandahatra…" },
  cfRagClear: { en: "Clear", fr: "Vider", mg: "Fafao" },
  cfRagClearTip: { en: "Clear the base", fr: "Vider la base", mg: "Fafao ny banky" },
  cfRagClearConfirm: { en: "Clear the indexed knowledge base?", fr: "Vider la base documentaire indexée ?", mg: "Fafao ny banky angona voalahatra?" },

  // SearchResults
  srResults: { en: "RESULTS:", fr: "RÉSULTATS:", mg: "VALINY:" },

  // ChatWindow — actions par message + raisonnement
  reasoning: { en: "Reasoning", fr: "Raisonnement", mg: "Fisainana" },
  msgCopy: { en: "Copy", fr: "Copier", mg: "Adikao" },
  msgRegen: { en: "Regenerate", fr: "Régénérer", mg: "Avereno" },
  msgDelete: { en: "Delete", fr: "Supprimer", mg: "Fafao" },
  msgCopied: { en: "Copied", fr: "Copié", mg: "Voadika" },

  // MemoryPanel — recherche unifiée
  searchPlaceholder: { en: "Search your history (keywords or meaning)…", fr: "Rechercher dans l'historique (mots-clés ou sens)…", mg: "Hikaroka ao amin'ny tantara (teny na hevitra)…" },
  searchTitle: { en: "SEARCH", fr: "RECHERCHE", mg: "FIKAROHANA" },
  searchNone: { en: "No result.", fr: "Aucun résultat.", mg: "Tsy misy valiny." },
};

export function t(key: keyof typeof T): string {
  const e = T[key];
  if (!e) return key as string;
  return e[getLang()] || e.en;
}
