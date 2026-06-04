"use client";

import { useEffect, useRef } from "react";

export interface ShellEntry {
  command?: string;
  content: string;
  shellStreaming?: boolean;
  shellDone?: boolean;
  returncode?: number;
  error?: string;
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
  entries, taskStatus, onClose,
}: {
  entries: ShellEntry[];
  taskStatus: TaskStatus;
  onClose: () => void;
}) {
  const bodyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [entries, taskStatus]);

  const meta = STATUS_META[taskStatus];

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
          const ok = done && e.returncode === 0;
          const failed = done && e.returncode !== 0 && e.returncode !== undefined;
          const running = e.shellStreaming && !done;
          const color = running ? "var(--accent)" : ok ? "var(--green)" : failed ? "var(--red)" : "var(--text-muted)";
          return (
            <div key={i} style={{ marginBottom: 10 }}>
              <div style={{ display: "flex", gap: 6, alignItems: "center", color }}>
                <span>{running ? "⟳" : ok ? "✓" : failed ? "✗" : "•"}</span>
                <span style={{ color: "var(--yellow)", wordBreak: "break-all", flex: 1 }}>$ {e.command}</span>
                <span style={{ fontSize: 10 }}>
                  {running ? "en cours…" : done ? (ok ? "succès" : `échec (rc=${e.returncode})`) : ""}
                </span>
              </div>
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
    </div>
  );
}
