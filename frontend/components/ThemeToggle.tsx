"use client";

import { useEffect, useState } from "react";
import { applyTheme, nextTheme, readTheme, Theme, THEME_ICON, THEME_LABEL } from "../lib/theme";

// Bouton de bascule de thème (auto → clair → sombre). Lit l'état au montage pour
// rester cohérent avec le script anti-flash du layout, puis écrit data-theme +
// localStorage à chaque changement.
export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("auto");

  useEffect(() => { setTheme(readTheme()); }, []);

  const cycle = () => {
    const t = nextTheme(theme);
    applyTheme(t);
    setTheme(t);
  };

  return (
    <button
      onClick={cycle}
      title={`${THEME_LABEL[theme]} — cliquer pour changer`}
      aria-label={THEME_LABEL[theme]}
      style={{
        background: "var(--border)", border: "none", color: "var(--text-muted)",
        padding: "4px 10px", borderRadius: 4, cursor: "pointer", fontSize: 12, lineHeight: 1,
      }}
    >
      {THEME_ICON[theme]}
    </button>
  );
}
