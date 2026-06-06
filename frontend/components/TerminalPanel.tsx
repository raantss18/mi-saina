"use client";

import { useEffect, useRef, useState } from "react";

export interface ShellEntry {
  command?: string;
  content: string;
  shellStreaming?: boolean;
  shellDone?: boolean;
  waitingInput?: boolean;
  returncode?: number;
  error?: string;
  logicalFailure?: boolean;
  statusReason?: string;
}

export type TaskStatus = "idle" | "running" | "success" | "failure" | "stopped";

const STATUS_META: Record<TaskStatus, { label: string; color: string; icon: string }> = {
  idle:    { label: "prêt",            color: "var(--text-muted)", icon: "○" },
  running: { label: "tâche en cours…", color: "var(--accent)",     icon: "⟳" },
  success: { label: "terminé · succès", color: "var(--green)",     icon: "✓" },
  failure: { label: "terminé · échec",  color: "var(--red)",       icon: "✗" },
  stopped: { label: "arrêté",          color: "var(--yellow)",     icon: "■" },
};

export default function TerminalPanel({
  entries, taskStatus, onClose, onInput,
}: {
  entries: ShellEntry[];
  taskStatus: TaskStatus;
  onClose: () => void;
  onInput?: (text: string) => void;
}) {
  const bodyRef = useRef<HTMLDivElement>(null);
  const [inputVal, setInputVal] = useState("");

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [entries, taskStatus]);

  const meta = STATUS_META[taskStatus];
  // Une commande attend-elle une saisie (prompt [Y/n], etc.) ?
  const active = entries.find(e => e.shellStreaming && !e.shellDone);
  const awaiting = entries.some(e => e.waitingInput && !e.shellDone);

  const send = () => { onInput?.(inputVal); setInputVal(""); };

  return (
    <div style={{
      width: "40%", minWidth: 300, maxWidth: 560,
      display: "flex", flexDirection: "column",
      borderLeft: "1px solid var(--border)", background: "#05090d",
    }}>
      {/* En-tête + statut de la tâche */}
      <div style={{
        padding: "6px 12px", borderBottom: "1px solid var(--border)",
        display: "flex", alignItems: "center", gap: 8, background: "var(--surface)",
        flexShrink: 0,
      }}>
        <span style={{ fontSize: 11, color: "var(--text-muted)", letterSpacing: 0.5 }}>▣ TERMINAL</span>
        <span style={{
          marginLeft: "auto", display: "flex", alignItems: "center", gap: 5,
          fontSize: 11, color: meta.color, fontWeight: 700,
        }}>
          <span style={taskStatus === "running" ? { display: "inline-block", animation: "spin 1s linear infinite" } : undefined}>
            {meta.icon}
          </span>
          {meta.label}
        </span>
        <button onClick={onClose} title="Fermer le terminal"
          style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: 14, padding: 0, marginLeft: 6 }}>
          ✕
        </button>
      </div>

      {/* Corps : sortie agrégée de toutes les commandes */}
      <div ref={bodyRef} style={{
        flex: 1, overflowY: "auto", padding: "8px 10px",
        fontFamily: "monospace", fontSize: 11, lineHeight: 1.45,
      }}>
        {entries.length === 0 && (
          <div style={{ color: "var(--text-muted)", fontStyle: "italic" }}>
            Aucune commande exécutée pour l’instant.
          </div>
        )}
        {entries.map((e, i) => {
          const done = e.shellDone;
          // Échec logique : code retour 0 mais sortie en erreur (tests, linter…)
          const logicalFail = done && e.logicalFailure;
          const failed = done && ((e.returncode !== 0 && e.returncode !== undefined) || logicalFail);
          const ok = done && !failed;
          const running = e.shellStreaming && !done;
          const color = running ? "var(--accent)" : ok ? "var(--green)" : failed ? "var(--red)" : "var(--text-muted)";
          const statusLabel = running ? "en cours…"
            : !done ? ""
            : ok ? "succès"
            : logicalFail ? "échec logique (rc=0)"
            : `échec (rc=${e.returncode})`;
          return (
            <div key={i} style={{ marginBottom: 10 }}>
              <div style={{ display: "flex", gap: 6, alignItems: "center", color }}>
                <span>{running ? "⟳" : ok ? "✓" : failed ? "✗" : "•"}</span>
                <span style={{ color: "var(--yellow)", wordBreak: "break-all", flex: 1 }}>$ {e.command}</span>
                <span style={{ fontSize: 10 }}>{statusLabel}</span>
              </div>
              {logicalFail && e.statusReason && (
                <div style={{ margin: "2px 0 0 16px", color: "var(--red)", fontSize: 10 }}>
                  ⚠ {e.statusReason}
                </div>
              )}
              {e.content && (
                <pre style={{
                  margin: "3px 0 0 16px", whiteSpace: "pre-wrap", wordBreak: "break-word",
                  color: "var(--text)",
                }}>{e.content}</pre>
              )}
              {e.error && (
                <div style={{ margin: "2px 0 0 16px", color: "var(--red)" }}>{e.error}</div>
              )}
            </div>
          );
        })}
      </div>

      {/* Saisie interactive : répondre aux prompts (mot de passe via la fenêtre dédiée) */}
      {onInput && active && (
        <div style={{
          borderTop: `1px solid ${awaiting ? "var(--accent)" : "var(--border)"}`,
          padding: "6px 10px", display: "flex", gap: 6, alignItems: "center",
          background: awaiting ? "rgba(127,184,154,0.08)" : "var(--surface)",
        }}>
          <span style={{ color: "var(--accent)", fontSize: 12 }}>›</span>
          <input
            value={inputVal}
            onChange={e => setInputVal(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); send(); } }}
            placeholder={awaiting ? "Le processus attend une réponse (ex: y, n, Entrée)…" : "Entrée pour le processus…"}
            autoFocus={awaiting}
            style={{
              flex: 1, background: "transparent", border: "none", outline: "none",
              color: "var(--text)", fontSize: 12, fontFamily: "monospace",
            }}
          />
          <button onClick={send}
            style={{ background: "var(--accent)", border: "none", color: "#000", padding: "3px 10px", borderRadius: 4, cursor: "pointer", fontSize: 11, fontWeight: 700 }}>
            ↵
          </button>
        </div>
      )}
    </div>
  );
}
