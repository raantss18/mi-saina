"use client";

import { useCallback, useEffect, useState } from "react";
import { API_BASE } from "../lib/config";
import { t } from "../lib/i18n";
import { modelDesc as desc } from "../lib/models";

interface OllamaModel {
  name: string;
  size_gb: number;
  modified: string;
  active: boolean;
}

interface PullStatus {
  status: string;
  completed?: number;
  total?: number;
  percent?: number;
}

interface Props {
  onModelChange: (model: string) => void;
}

interface Suggestion { name: string; label: string; size_gb: number; note: string; installed: boolean; recommended: boolean; }

export default function ModelPanel({ onModelChange }: Props) {
  const [models, setModels] = useState<OllamaModel[]>([]);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [pullInput, setPullInput] = useState("");
  const [actionModel, setActionModel] = useState<string | null>(null);  // modèle en cours d'action
  const [actionType, setActionType] = useState<"pull" | "update" | "delete" | "import" | null>(null);
  const [pullStatus, setPullStatus] = useState<PullStatus | null>(null);
  const [error, setError] = useState("");

  const fetchModels = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/models/list`);
      if (res.ok) setModels(await res.json());
    } catch { setError(t("mpNetErr")); }
  }, []);

  const fetchSuggestions = useCallback(() => {
    fetch(`${API_BASE}/models/suggestions`).then(r => r.json())
      .then(d => setSuggestions(d.models || [])).catch(() => {});
  }, []);

  useEffect(() => {
    fetchModels();
    fetchSuggestions();
    const id = setInterval(fetchModels, 8000);
    return () => clearInterval(id);
  }, [fetchModels, fetchSuggestions]);

  const handleSelect = async (name: string) => {
    await fetch(`${API_BASE}/models/select`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model: name }),
    });
    onModelChange(name);
    fetchModels();
  };

  const handleDelete = async (name: string) => {
    if (!confirm(`Supprimer "${name}" ? (${models.find(m => m.name === name)?.size_gb}GB libérés)`)) return;
    setActionModel(name);
    setActionType("delete");
    setError("");
    try {
      const res = await fetch(`${API_BASE}/models/delete/${encodeURIComponent(name)}`, { method: "DELETE" });
      if (!res.ok) {
        const d = await res.json();
        setError(d.detail || "Erreur suppression");
      } else {
        fetchModels();
      }
    } catch { setError(t("mpNetErr")); }
    setActionModel(null);
    setActionType(null);
  };

  const handlePullOrUpdate = async (modelName: string, isUpdate: boolean) => {
    setActionModel(modelName);
    setActionType(isUpdate ? "update" : "pull");
    setError("");
    setPullStatus({ status: isUpdate ? t("cfChecking") : "…" });

    try {
      const es = new EventSource(`${API_BASE}/models/pull/${encodeURIComponent(modelName)}`);
      es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.status === "done") {
            es.close();
            setActionModel(null);
            setActionType(null);
            setPullStatus(null);
            if (!isUpdate) setPullInput("");
            fetchModels();
            fetchSuggestions();
            return;
          }
          const pct = data.total && data.completed ? Math.round((data.completed / data.total) * 100) : undefined;
          setPullStatus({ status: data.status || "", completed: data.completed, total: data.total, percent: pct });
        } catch {}
      };
      es.onerror = () => {
        es.close();
        setActionModel(null);
        setActionType(null);
        setPullStatus(null);
        fetchModels();
      };
    } catch {
      setActionModel(null);
      setActionType(null);
      setError(t("mpCantStart"));
    }
  };

  const importLmStudio = () => {
    setActionModel("LM Studio");
    setActionType("import");
    setError("");
    setPullStatus({ status: t("mpImportLabel") });
    try {
      const es = new EventSource(`${API_BASE}/models/import-lmstudio`);
      es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.status === "done") {
            es.close();
            setActionModel(null); setActionType(null); setPullStatus(null);
            fetchModels();
            return;
          }
          setPullStatus({ status: data.status || "" });
        } catch {}
      };
      es.onerror = () => {
        es.close();
        setActionModel(null); setActionType(null); setPullStatus(null);
        fetchModels();
      };
    } catch {
      setActionModel(null); setActionType(null);
      setError(t("mpImportErr"));
    }
  };

  const busy = actionModel !== null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ color: "var(--accent)", fontSize: 11, fontWeight: 700, letterSpacing: 1 }}>{t("mpHeader")}</div>
        <button onClick={fetchModels} style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: 11 }}>
          {t("mpRefresh")}
        </button>
      </div>

      {/* Progress bar globale */}
      {pullStatus && (
        <div style={{ background: "var(--bg)", border: "1px solid var(--accent)", borderRadius: 6, padding: "8px 12px" }}>
          <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }}>
            {actionType === "update" ? t("mpUpdating") : actionType === "import" ? t("mpImportLabel") : t("mpDownloading")} : <code style={{ color: "var(--accent)" }}>{actionModel}</code>
          </div>
          <div style={{ fontSize: 11, color: "var(--text)" }}>
            {pullStatus.status}{pullStatus.percent !== undefined && ` — ${pullStatus.percent}%`}
          </div>
          {pullStatus.percent !== undefined && (
            <div style={{ height: 4, background: "var(--border)", borderRadius: 2, marginTop: 6 }}>
              <div style={{ height: "100%", width: `${pullStatus.percent}%`, background: "var(--accent)", borderRadius: 2, transition: "width 0.3s" }} />
            </div>
          )}
        </div>
      )}

      {/* Liste des modèles */}
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {models.length === 0 && (
          <div className="ms-empty">
            <span className="ms-empty-icon" style={{ display: "inline-block", animation: "spin 1s linear infinite" }}>⟳</span>
            {t("mpLoading")}
          </div>
        )}
        {models.map(m => {
          const d = desc(m.name);
          const isActive = m.active;
          const isBusy = actionModel === m.name;
          return (
            <div key={m.name}
              onMouseEnter={e => { if (!isActive) e.currentTarget.style.borderColor = "var(--border-strong)"; }}
              onMouseLeave={e => { if (!isActive) e.currentTarget.style.borderColor = "var(--border)"; }}
              style={{
                display: "flex", alignItems: "center", gap: 8, padding: "8px 10px",
                borderRadius: 8, border: isActive ? "1px solid var(--accent)" : "1px solid var(--border)",
                background: isActive ? "rgba(127,184,154,0.06)" : "var(--bg)",
                transition: "border-color 0.15s ease",
              }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{ fontSize: 12, color: isActive ? "var(--accent)" : "var(--text)", fontWeight: isActive ? 700 : 400 }}>
                    {d.label}
                  </span>
                  {isActive && <span style={{ fontSize: 9, background: "var(--accent)", color: "var(--accent-contrast)", borderRadius: 3, padding: "1px 5px" }}>{t("mpActive")}</span>}
                  <span style={{ fontSize: 10, color: "var(--text-muted)", marginLeft: "auto" }}>{m.size_gb}GB</span>
                </div>
                <div style={{ display: "flex", gap: 3, marginTop: 3, flexWrap: "wrap" }}>
                  {d.tags.map(t => (
                    <span key={t} style={{ fontSize: 9, padding: "1px 5px", borderRadius: 3, background: "var(--border)", color: "var(--text-muted)" }}>{t}</span>
                  ))}
                </div>
              </div>

              {/* Boutons d'action */}
              <div style={{ display: "flex", gap: 4, flexShrink: 0 }}>
                {!isActive && (
                  <button onClick={() => handleSelect(m.name)} disabled={busy}
                    title={t("mpActivateTip")}
                    style={{ background: "var(--border)", border: "none", color: "var(--text)", padding: "3px 8px", borderRadius: 4, cursor: "pointer", fontSize: 10 }}>
                    {t("mpActivate")}
                  </button>
                )}
                <button
                  onClick={() => handlePullOrUpdate(m.name, true)}
                  disabled={busy}
                  title={t("mpUpdateTip")}
                  style={{ background: isBusy && actionType === "update" ? "rgba(127,184,154,0.2)" : "var(--border)", border: "none", color: "var(--accent)", padding: "3px 8px", borderRadius: 4, cursor: "pointer", fontSize: 10 }}
                >
                  {isBusy && actionType === "update" ? "..." : "↻"}
                </button>
                {!isActive && (
                  <button onClick={() => handleDelete(m.name)} disabled={busy}
                    title={t("mpDeleteTip")}
                    style={{ background: "rgba(248,81,73,0.1)", border: "1px solid rgba(248,81,73,0.3)", color: "var(--red)", padding: "3px 8px", borderRadius: 4, cursor: "pointer", fontSize: 10 }}>
                    🗑
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Télécharger un nouveau modèle */}
      <div>
        <div style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 6, letterSpacing: 0.5 }}>{t("mpDownloadHub")}</div>
        <div style={{ display: "flex", gap: 6 }}>
          <input
            value={pullInput}
            onChange={e => setPullInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && !busy && handlePullOrUpdate(pullInput.trim(), false)}
            placeholder={t("mpPullPlaceholder")}
            disabled={busy}
            style={{
              flex: 1, background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)",
              padding: "6px 8px", borderRadius: 4, fontSize: 11, outline: "none", fontFamily: "inherit",
            }}
          />
          <button
            onClick={() => handlePullOrUpdate(pullInput.trim(), false)}
            disabled={busy || !pullInput.trim()}
            title={t("mpPullTip")}
            style={{
              background: !busy && pullInput.trim() ? "var(--accent)" : "var(--border)",
              border: "none", color: !busy && pullInput.trim() ? "var(--accent-contrast)" : "var(--text-muted)",
              padding: "6px 12px", borderRadius: 4, cursor: "pointer", fontSize: 11, fontWeight: 600,
            }}
          >
            {t("mpDownloading")}
          </button>
        </div>
        {error && <div style={{ fontSize: 11, color: "var(--red)", marginTop: 6 }}>{error}</div>}

        {/* Import depuis LM Studio */}
        <button
          onClick={importLmStudio}
          disabled={busy}
          title={t("mpImportTip")}
          style={{
            marginTop: 8, width: "100%", background: "var(--bg)", border: "1px dashed var(--accent)",
            color: "var(--accent)", padding: "7px", borderRadius: 6, cursor: busy ? "default" : "pointer",
            fontSize: 11, fontWeight: 600,
          }}
        >
          {t("mpImportBtn")}
        </button>
      </div>

      {/* Modèles suggérés (populaires sur Ollama, marqués selon la compatibilité) */}
      {suggestions.length > 0 && (
        <div>
          <div style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 6, letterSpacing: 0.5 }}>{t("mpSuggested")}</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {suggestions.map(s => (
              <div key={s.name} style={{
                display: "flex", alignItems: "center", gap: 8, padding: "6px 10px",
                borderRadius: 8, border: "1px solid var(--border)", background: "var(--bg)",
              }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                    <span style={{ fontSize: 12, color: "var(--text)" }}>{s.label}</span>
                    <span style={{ fontSize: 9, color: "var(--text-muted)" }}>{s.size_gb}GB</span>
                    {s.recommended && <span title={t("mpCompatible")} style={{ fontSize: 9, background: "rgba(127,184,154,0.2)", color: "var(--accent)", borderRadius: 3, padding: "1px 5px" }}>✓ {t("mpCompatible")}</span>}
                  </div>
                  <div style={{ fontSize: 9, color: "var(--text-muted)", marginTop: 2 }}>{s.note}</div>
                </div>
                {s.installed
                  ? <span style={{ fontSize: 10, color: "var(--green)" }}>✓ {t("mpInstalledTag")}</span>
                  : <button onClick={() => handlePullOrUpdate(s.name, false)} disabled={busy}
                      title={t("mpPullTip")}
                      style={{ background: "var(--border)", border: "none", color: "var(--accent)", padding: "3px 10px", borderRadius: 4, cursor: "pointer", fontSize: 10, fontWeight: 600 }}>
                      ↓ {t("mpGet")}
                    </button>}
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{ fontSize: 10, color: "var(--text-muted)", borderTop: "1px solid var(--border)", paddingTop: 8 }}>
        {t("mpLegend")}
      </div>
    </div>
  );
}
