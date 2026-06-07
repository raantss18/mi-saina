"use client";

import { useEffect, useState } from "react";
import { t } from "../lib/i18n";

interface Props {
  onPick: (text: string) => void;
}

const EXAMPLES: { icon: string; titleKey: Parameters<typeof t>[0]; promptKey: Parameters<typeof t>[0] }[] = [
  { icon: "⬆", titleKey: "exUpdate", promptKey: "exUpdateP" },
  { icon: "🌐", titleKey: "exWeb", promptKey: "exWebP" },
  { icon: "📁", titleKey: "exDocs", promptKey: "exDocsP" },
  { icon: "🩺", titleKey: "exDisk", promptKey: "exDiskP" },
  { icon: "🔎", titleKey: "exFind", promptKey: "exFindP" },
  { icon: "🧩", titleKey: "exPkg", promptKey: "exPkgP" },
];

const SEEN_KEY = "ms-onboarded";

// Écran d'accueil au 1er lancement : exemples cliquables + mini visite guidée
// sautable. La visite ne s'affiche qu'une fois (localStorage['ms-onboarded']).
export default function WelcomeScreen({ onPick }: Props) {
  const [firstVisit, setFirstVisit] = useState(false);

  useEffect(() => {
    try { setFirstVisit(localStorage.getItem(SEEN_KEY) !== "1"); } catch { /* stockage indispo */ }
  }, []);

  const dismissTour = () => {
    setFirstVisit(false);
    try { localStorage.setItem(SEEN_KEY, "1"); } catch { /* stockage indispo */ }
  };

  return (
    <div className="ms-fade" style={{
      flex: 1, display: "flex", flexDirection: "column", alignItems: "center",
      justifyContent: "center", padding: "24px", gap: 20, overflowY: "auto",
    }}>
      <div style={{ textAlign: "center" }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/mi-saina-icon.png" alt="mi-saina" width={72} height={72}
          style={{ borderRadius: 18, marginBottom: 12, boxShadow: "var(--shadow)" }} />
        <div style={{ fontSize: 34, fontWeight: 800, color: "var(--text)", letterSpacing: -0.5 }}>mi-saina</div>
        <div style={{ fontSize: 14, color: "var(--text-muted)", marginTop: 6 }}>
          {t("welcomeTagline")}
        </div>
      </div>

      {firstVisit && (
        <div style={{
          maxWidth: 560, background: "var(--surface-2)", border: "1px solid var(--accent)",
          borderRadius: "var(--radius)", padding: "14px 16px", fontSize: 13, color: "var(--text)",
        }}>
          <div style={{ fontWeight: 700, color: "var(--accent)", marginBottom: 6 }}>{t("welcomeHi")}</div>
          <ul style={{ margin: "0 0 10px 0", paddingLeft: 18, color: "var(--text-muted)", lineHeight: 1.7 }}>
            <li>{t("tour1")}</li>
            <li>{t("tour2")}</li>
            <li>{t("tour3")}</li>
            <li>{t("tour4")}</li>
          </ul>
          <div style={{ textAlign: "right" }}>
            <button onClick={dismissTour} style={{
              background: "var(--accent)", border: "none", color: "var(--accent-contrast)",
              padding: "5px 14px", borderRadius: 6, cursor: "pointer", fontSize: 12, fontWeight: 700,
            }}>
              {t("welcomeGo")}
            </button>
          </div>
        </div>
      )}

      <div style={{
        display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
        gap: 10, width: "100%", maxWidth: 720,
      }}>
        {EXAMPLES.map(ex => (
          <button
            key={ex.titleKey}
            onClick={() => onPick(t(ex.promptKey))}
            style={{
              display: "flex", alignItems: "center", gap: 10, textAlign: "left",
              background: "var(--surface)", border: "1px solid var(--border)",
              borderRadius: "var(--radius)", padding: "12px 14px", cursor: "pointer",
              color: "var(--text)", fontSize: 13, transition: "border-color 0.15s, background 0.15s",
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = "var(--accent)"; e.currentTarget.style.background = "var(--surface-2)"; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = "var(--border)"; e.currentTarget.style.background = "var(--surface)"; }}
          >
            <span style={{ fontSize: 20 }}>{ex.icon}</span>
            <span>{t(ex.titleKey)}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
