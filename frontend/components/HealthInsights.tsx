"use client";

import { useEffect, useState, useCallback } from "react";
import { API_BASE } from "../lib/config";
import { t } from "../lib/i18n";

interface Finding {
  id: string;
  severity: "info" | "warning" | "critical";
  title: string;
  detail: string;
  suggestion?: string;
  command?: string;
}

interface Props {
  /** Pré-remplit le champ de saisie avec la commande suggérée (l'utilisateur valide). */
  onPick: (text: string) => void;
}

const SEV_COLOR: Record<string, string> = {
  info: "var(--accent)", warning: "var(--yellow)", critical: "var(--red)",
};

// Bandeau « bilan santé » — PROPOSE seulement. Cliquer pré-remplit le chat avec la
// commande suggérée ; rien n'est exécuté automatiquement. Sondage périodique léger.
export default function HealthInsights({ onPick }: Props) {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const [open, setOpen] = useState(true);

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/health-monitor/insights`);
      if (!r.ok) return;
      const d = await r.json();
      if (d.enabled === false) { setFindings([]); return; }
      setFindings(Array.isArray(d.findings) ? d.findings : []);
    } catch { /* backend indispo */ }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 120_000);   // re-sonde toutes les 2 min (l'état change lentement)
    return () => clearInterval(id);
  }, [load]);

  const visible = findings.filter(f => !dismissed.has(f.id));
  if (visible.length === 0) return null;

  return (
    <div style={{
      flexShrink: 0, margin: "8px 20px 0", border: "1px solid var(--border)",
      borderRadius: 8, background: "var(--surface)", overflow: "hidden",
    }}>
      <div onClick={() => setOpen(o => !o)}
        style={{ display: "flex", alignItems: "center", gap: 8, padding: "7px 12px", cursor: "pointer" }}>
        <span style={{ fontSize: 13 }}>🩺</span>
        <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text)" }}>
          {t("healthTitle")} · {visible.length}
        </span>
        <span style={{ marginLeft: "auto", fontSize: 11, color: "var(--text-muted)" }}>{open ? "▾" : "▸"}</span>
      </div>

      {open && (
        <div style={{ display: "flex", flexDirection: "column", gap: 6, padding: "0 12px 10px" }}>
          {visible.map(f => (
            <div key={f.id} style={{
              display: "flex", alignItems: "flex-start", gap: 10, padding: "8px 10px",
              background: "var(--bg)", border: "1px solid var(--border)",
              borderLeft: `3px solid ${SEV_COLOR[f.severity] || "var(--border)"}`, borderRadius: 6,
            }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text)" }}>{f.title}</div>
                <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>{f.detail}</div>
                {f.command && (
                  <code style={{ display: "inline-block", marginTop: 4, fontSize: 10, color: "var(--text-muted)", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 4, padding: "2px 6px" }}>
                    $ {f.command}
                  </code>
                )}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 4, flexShrink: 0 }}>
                {f.command && (
                  <button onClick={() => onPick(f.command!)} title={t("healthRunTip")}
                    style={{ background: "var(--accent)", border: "none", color: "var(--accent-contrast)", padding: "3px 10px", borderRadius: 4, cursor: "pointer", fontSize: 11, fontWeight: 700, whiteSpace: "nowrap" }}>
                    {t("healthFix")}
                  </button>
                )}
                <button onClick={() => setDismissed(prev => new Set(prev).add(f.id))}
                  style={{ background: "var(--border)", border: "none", color: "var(--text-muted)", padding: "3px 10px", borderRadius: 4, cursor: "pointer", fontSize: 11, whiteSpace: "nowrap" }}>
                  {t("healthDismiss")}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
