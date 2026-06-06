// Gestion du thème clair/sombre/auto, partagée entre l'UI et le script anti-flash
// du layout. « auto » suit le système (aucun data-theme forcé) ; « dark »/« light »
// forcent la valeur et sont persistés dans localStorage['ms-theme'].

export type Theme = "auto" | "dark" | "light";

export const THEME_KEY = "ms-theme";

// Cycle pour le bouton de bascule : auto → light → dark → auto.
export function nextTheme(t: Theme): Theme {
  return t === "auto" ? "light" : t === "light" ? "dark" : "auto";
}

export function readTheme(): Theme {
  if (typeof window === "undefined") return "auto";
  try {
    const v = window.localStorage.getItem(THEME_KEY);
    return v === "dark" || v === "light" ? v : "auto";
  } catch {
    return "auto"; // stockage indispo (origine opaque, mode privé…)
  }
}

// Applique le thème au document et le persiste. « auto » retire l'attribut et la
// clé pour laisser prefers-color-scheme décider.
export function applyTheme(t: Theme): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  if (t === "auto") {
    root.removeAttribute("data-theme");
    try { window.localStorage.removeItem(THEME_KEY); } catch { /* stockage indispo */ }
  } else {
    root.setAttribute("data-theme", t);
    try { window.localStorage.setItem(THEME_KEY, t); } catch { /* stockage indispo */ }
  }
}

export const THEME_ICON: Record<Theme, string> = {
  auto: "🌗",
  light: "☀",
  dark: "🌙",
};

export const THEME_LABEL: Record<Theme, string> = {
  auto: "Thème : auto (système)",
  light: "Thème : clair",
  dark: "Thème : sombre",
};
