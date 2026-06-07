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
  // Artefacts
  artTitle: { en: "Artifacts", fr: "Artefacts", mg: "Artefacta" },
  artEmpty: { en: "Generated code blocks will appear here.", fr: "Les blocs de code générés apparaîtront ici.", mg: "Hiseho eto ny kaody noforonina." },
  artCopy: { en: "Copy", fr: "Copier", mg: "Adikao" },
  artDownload: { en: "Download", fr: "Télécharger", mg: "Alaina" },
  artRemove: { en: "Remove", fr: "Retirer", mg: "Esory" },
  artClear: { en: "Clear", fr: "Vider", mg: "Fafao" },
};

export function t(key: keyof typeof T): string {
  const e = T[key];
  if (!e) return key as string;
  return e[getLang()] || e.en;
}
