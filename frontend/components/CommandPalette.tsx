"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { t } from "../lib/i18n";

export interface Command {
  id: string;
  label: string;
  hint?: string;     // raccourci ou contexte affiché à droite
  icon?: string;
  keywords?: string; // termes supplémentaires pour la recherche
  run: () => void;
}

interface Props {
  open: boolean;
  commands: Command[];
  onClose: () => void;
}

// Palette de commandes ⌘K / Ctrl+K : recherche floue (sous-chaîne) sur le label,
// le hint et les mots-clés ; navigation clavier ↑/↓, Entrée pour exécuter, Échap
// pour fermer.
export default function CommandPalette({ open, commands, onClose }: Props) {
  const [query, setQuery] = useState("");
  const [index, setIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) { setQuery(""); setIndex(0); setTimeout(() => inputRef.current?.focus(), 0); }
  }, [open]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return commands;
    return commands.filter(c =>
      `${c.label} ${c.hint ?? ""} ${c.keywords ?? ""}`.toLowerCase().includes(q)
    );
  }, [query, commands]);

  if (!open) return null;

  const exec = (cmd?: Command) => {
    if (!cmd) return;
    onClose();
    cmd.run();
  };

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)",
        display: "flex", alignItems: "flex-start", justifyContent: "center",
        paddingTop: "12vh", zIndex: 200,
      }}
    >
      <div
        className="ms-pop"
        onClick={e => e.stopPropagation()}
        style={{
          width: "min(620px, 92vw)", background: "var(--surface)",
          border: "1px solid var(--border-strong)", borderRadius: "var(--radius)",
          boxShadow: "var(--shadow)", overflow: "hidden",
        }}
      >
        <input
          ref={inputRef}
          value={query}
          onChange={e => { setQuery(e.target.value); setIndex(0); }}
          onKeyDown={e => {
            if (e.key === "ArrowDown") { e.preventDefault(); setIndex(i => Math.min(i + 1, filtered.length - 1)); }
            else if (e.key === "ArrowUp") { e.preventDefault(); setIndex(i => Math.max(i - 1, 0)); }
            else if (e.key === "Enter") { e.preventDefault(); exec(filtered[index]); }
            else if (e.key === "Escape") { e.preventDefault(); onClose(); }
          }}
          placeholder={t("paletteSearch")}
          style={{
            width: "100%", background: "transparent", border: "none", outline: "none",
            color: "var(--text)", fontSize: 15, padding: "14px 16px",
            borderBottom: "1px solid var(--border)",
          }}
        />
        <div style={{ maxHeight: 360, overflowY: "auto", padding: 6 }}>
          {filtered.length === 0 && (
            <div style={{ padding: "16px", color: "var(--text-muted)", fontSize: 13, textAlign: "center" }}>
              {t("paletteEmpty")}
            </div>
          )}
          {filtered.map((c, i) => (
            <div
              key={c.id}
              onClick={() => exec(c)}
              onMouseEnter={() => setIndex(i)}
              style={{
                display: "flex", alignItems: "center", gap: 12,
                padding: "9px 12px", borderRadius: 8, cursor: "pointer",
                background: i === index ? "var(--surface-2)" : "transparent",
              }}
            >
              <span style={{ fontSize: 16, width: 20, textAlign: "center" }}>{c.icon ?? "›"}</span>
              <span style={{ flex: 1, fontSize: 13, color: "var(--text)" }}>{c.label}</span>
              {c.hint && <span style={{ fontSize: 11, color: "var(--text-muted)" }}>{c.hint}</span>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
