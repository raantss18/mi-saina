"use client";

import { useEffect, useState } from "react";

interface Props {
  onPick: (text: string) => void;
}

const EXAMPLES: { icon: string; title: string; prompt: string }[] = [
  { icon: "⬆", title: "Mets à jour mon système", prompt: "Mets à jour mon système" },
  { icon: "🌐", title: "Résume une page web", prompt: "Résume cette page : https://" },
  { icon: "📁", title: "Range mon dossier Téléchargements", prompt: "Liste ce qu'il y a dans mon dossier Téléchargements et propose un rangement" },
  { icon: "🩺", title: "Diagnostique mon disque", prompt: "Montre l'espace disque utilisé et les plus gros dossiers de mon /home" },
  { icon: "🔎", title: "Cherche un fichier", prompt: "Trouve et ouvre le fichier " },
  { icon: "🧩", title: "Installe un paquet", prompt: "Installe le paquet " },
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
          Votre assistant IA local — il comprend, agit sur votre système, et apprend.
        </div>
      </div>

      {firstVisit && (
        <div style={{
          maxWidth: 560, background: "var(--surface-2)", border: "1px solid var(--accent)",
          borderRadius: "var(--radius)", padding: "14px 16px", fontSize: 13, color: "var(--text)",
        }}>
          <div style={{ fontWeight: 700, color: "var(--accent)", marginBottom: 6 }}>👋 Bienvenue !</div>
          <ul style={{ margin: "0 0 10px 0", paddingLeft: 18, color: "var(--text-muted)", lineHeight: 1.7 }}>
            <li>Décrivez une tâche en langage naturel — mi-saina propose et exécute les commandes.</li>
            <li>Les commandes sensibles demandent votre validation avant de s'exécuter.</li>
            <li>Ouvrez la palette d'actions avec <kbd>Ctrl</kbd>+<kbd>K</kbd>.</li>
            <li>Tapez <code>/</code> pour vos raccourcis (skills) ; le panneau <strong>▣ Terminal</strong> montre la sortie brute.</li>
          </ul>
          <div style={{ textAlign: "right" }}>
            <button onClick={dismissTour} style={{
              background: "var(--accent)", border: "none", color: "var(--accent-contrast)",
              padding: "5px 14px", borderRadius: 6, cursor: "pointer", fontSize: 12, fontWeight: 700,
            }}>
              C'est parti
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
            key={ex.title}
            onClick={() => onPick(ex.prompt)}
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
            <span>{ex.title}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
