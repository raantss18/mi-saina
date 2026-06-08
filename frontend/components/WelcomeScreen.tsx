"use client";

import { useEffect, useState } from "react";
import { t } from "../lib/i18n";

interface Props {
  onPick: (text: string) => void;
}

const EXAMPLES: {
  icon: string; tint: string;
  titleKey: Parameters<typeof t>[0]; descKey: Parameters<typeof t>[0]; promptKey: Parameters<typeof t>[0];
}[] = [
  { icon: "⬆", tint: "#3b82f6", titleKey: "exUpdate", descKey: "exUpdateD", promptKey: "exUpdateP" },
  { icon: "🌐", tint: "#06b6d4", titleKey: "exWeb", descKey: "exWebD", promptKey: "exWebP" },
  { icon: "📁", tint: "#eab308", titleKey: "exDocs", descKey: "exDocsD", promptKey: "exDocsP" },
  { icon: "🩺", tint: "#ef4444", titleKey: "exDisk", descKey: "exDiskD", promptKey: "exDiskP" },
  { icon: "🔎", tint: "#a855f7", titleKey: "exFind", descKey: "exFindD", promptKey: "exFindP" },
  { icon: "🧩", tint: "#22c55e", titleKey: "exPkg", descKey: "exPkgD", promptKey: "exPkgP" },
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
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center" }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/mi-saina-icon.png" alt="mi-saina" width={80} height={80}
          style={{ borderRadius: 20, marginBottom: 14, boxShadow: "var(--shadow)" }} />
        <div style={{ fontSize: 36, fontWeight: 800, color: "var(--text)", letterSpacing: -0.5, lineHeight: 1.1 }}>mi-saina</div>
        <div style={{ fontSize: 14, color: "var(--text-muted)", marginTop: 8, maxWidth: 440 }}>
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

      <div style={{ width: "100%", maxWidth: 760 }}>
        <div style={{
          fontSize: 11, fontWeight: 700, letterSpacing: 0.8, textTransform: "uppercase",
          color: "var(--text-muted)", textAlign: "center", marginBottom: 12,
        }}>
          {t("welcomeTry")}
        </div>
        <div style={{
          display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))", gap: 12,
        }}>
          {EXAMPLES.map(ex => (
            <button
              key={ex.titleKey}
              onClick={() => onPick(t(ex.promptKey))}
              style={{
                display: "flex", alignItems: "center", gap: 12, textAlign: "left",
                background: "var(--surface)", border: "1px solid var(--border)",
                borderRadius: 12, padding: "14px 16px", cursor: "pointer", color: "var(--text)",
                transition: "border-color 0.15s, background 0.15s, transform 0.15s, box-shadow 0.15s",
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = ex.tint;
                e.currentTarget.style.background = "var(--surface-2)";
                e.currentTarget.style.transform = "translateY(-2px)";
                e.currentTarget.style.boxShadow = "var(--shadow)";
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = "var(--border)";
                e.currentTarget.style.background = "var(--surface)";
                e.currentTarget.style.transform = "none";
                e.currentTarget.style.boxShadow = "none";
              }}
            >
              <span style={{
                flexShrink: 0, width: 38, height: 38, borderRadius: 10,
                display: "flex", alignItems: "center", justifyContent: "center", fontSize: 19,
                background: `${ex.tint}22`, border: `1px solid ${ex.tint}55`,
              }}>{ex.icon}</span>
              <span style={{ minWidth: 0 }}>
                <span style={{ display: "block", fontSize: 13, fontWeight: 700 }}>{t(ex.titleKey)}</span>
                <span style={{
                  display: "block", fontSize: 11, color: "var(--text-muted)", marginTop: 2,
                  overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                }}>{t(ex.descKey)}</span>
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
