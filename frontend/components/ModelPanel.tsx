"use client";

import { useCallback, useEffect, useState } from "react";
import { API_BASE } from "../lib/config";

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

const MODEL_DESCRIPTIONS: Record<string, { label: string; tags: string[] }> = {
  "deepseek-r1:8b":         { label: "DeepSeek R1 8B",          tags: ["raisonnement", "8B"] },
  "gemma3:12b":             { label: "Gemma 3 12B",              tags: ["Google", "12B"] },
  "gemma4:26b":             { label: "Gemma 4 26B Vision",       tags: ["Google", "vision", "26B"] },
  "phi4-reasoning:latest":  { label: "Phi-4 Reasoning+",         tags: ["Microsoft", "14B"] },
  "gpt-oss:20b":            { label: "Meta GPT OSS 20B",         tags: ["Meta", "20B"] },
  "magistral:small":        { label: "Magistral Small",          tags: ["Mistral", "24B"] },
  "qwen3.6:35b":            { label: "Qwen 3.6 35B MoE",         tags: ["Qwen", "MoE", "35B"] },
  "qwen3.5:9b":             { label: "Qwen 3.5 9B",              tags: ["Qwen", "9B"] },
  "qwen3:30b-a3b":          { label: "Qwen 3 30B MoE",           tags: ["Qwen", "MoE", "30B"] },
};

function desc(name: string) {
  return MODEL_DESCRIPTIONS[name] ?? { label: name, tags: [] };
}

export default function ModelPanel({ onModelChange }: Props) {
  const [models, setModels] = useState<OllamaModel[]>([]);
  const [pullInput, setPullInput] = useState("");
  const [actionModel, setActionModel] = useState<string | null>(null);  // modèle en cours d'action
  const [actionType, setActionType] = useState<"pull" | "update" | "delete" | null>(null);
  const [pullStatus, setPullStatus] = useState<PullStatus | null>(null);
  const [error, setError] = useState("");

  const fetchModels = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/models/list`);
      if (res.ok) setModels(await res.json());
    } catch { setError("Backend inaccessible"); }
  }, []);

  useEffect(() => {
    fetchModels();
    const id = setInterval(fetchModels, 8000);
    return () => clearInterval(id);
  }, [fetchModels]);

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
    } catch { setError("Erreur réseau"); }
    setActionModel(null);
    setActionType(null);
  };

  const handlePullOrUpdate = async (modelName: string, isUpdate: boolean) => {
    setActionModel(modelName);
    setActionType(isUpdate ? "update" : "pull");
    setError("");
    setPullStatus({ status: isUpdate ? "Vérification des mises à jour..." : "Connexion..." });

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
      setError("Impossible de lancer l'opération");
    }
  };

  const busy = actionModel !== null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ color: "var(--accent)", fontSize: 11, fontWeight: 700, letterSpacing: 1 }}>MODÈLES OLLAMA</div>
        <button onClick={fetchModels} style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: 11 }}>
          ↻ rafraîchir
        </button>
      </div>

      {/* Progress bar globale */}
      {pullStatus && (
        <div style={{ background: "var(--bg)", border: "1px solid var(--accent)", borderRadius: 6, padding: "8px 12px" }}>
          <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }}>
            {actionType === "update" ? "↻ Mise à jour" : "↓ Téléchargement"} : <code style={{ color: "var(--accent)" }}>{actionModel}</code>
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
        {models.length === 0 && <div style={{ fontSize: 11, color: "var(--text-muted)" }}>Chargement...</div>}
        {models.map(m => {
          const d = desc(m.name);
          const isActive = m.active;
          const isBusy = actionModel === m.name;
          return (
            <div key={m.name} style={{
              display: "flex", alignItems: "center", gap: 8, padding: "8px 10px",
              borderRadius: 6, border: isActive ? "1px solid var(--accent)" : "1px solid var(--border)",
              background: isActive ? "rgba(127,184,154,0.06)" : "var(--bg)",
            }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{ fontSize: 12, color: isActive ? "var(--accent)" : "var(--text)", fontWeight: isActive ? 700 : 400 }}>
                    {d.label}
                  </span>
                  {isActive && <span style={{ fontSize: 9, background: "var(--accent)", color: "#000", borderRadius: 3, padding: "1px 5px" }}>ACTIF</span>}
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
                    style={{ background: "var(--border)", border: "none", color: "var(--text)", padding: "3px 8px", borderRadius: 4, cursor: "pointer", fontSize: 10 }}>
                    Activer
                  </button>
                )}
                <button
                  onClick={() => handlePullOrUpdate(m.name, true)}
                  disabled={busy}
                  title="Vérifier et télécharger les mises à jour"
                  style={{ background: isBusy && actionType === "update" ? "rgba(127,184,154,0.2)" : "var(--border)", border: "none", color: "var(--accent)", padding: "3px 8px", borderRadius: 4, cursor: "pointer", fontSize: 10 }}
                >
                  {isBusy && actionType === "update" ? "..." : "↻"}
                </button>
                {!isActive && (
                  <button onClick={() => handleDelete(m.name)} disabled={busy}
                    title="Supprimer ce modèle"
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
        <div style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 6, letterSpacing: 0.5 }}>TÉLÉCHARGER DEPUIS OLLAMA HUB</div>
        <div style={{ display: "flex", gap: 6 }}>
          <input
            value={pullInput}
            onChange={e => setPullInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && !busy && handlePullOrUpdate(pullInput.trim(), false)}
            placeholder="ex: phi4-mini, llama3.2:3b..."
            disabled={busy}
            style={{
              flex: 1, background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)",
              padding: "6px 8px", borderRadius: 4, fontSize: 11, outline: "none", fontFamily: "inherit",
            }}
          />
          <button
            onClick={() => handlePullOrUpdate(pullInput.trim(), false)}
            disabled={busy || !pullInput.trim()}
            style={{
              background: !busy && pullInput.trim() ? "var(--accent)" : "var(--border)",
              border: "none", color: !busy && pullInput.trim() ? "#000" : "var(--text-muted)",
              padding: "6px 12px", borderRadius: 4, cursor: "pointer", fontSize: 11, fontWeight: 600,
            }}
          >
            ↓ Pull
          </button>
        </div>
        {error && <div style={{ fontSize: 11, color: "var(--red)", marginTop: 6 }}>{error}</div>}
      </div>

      <div style={{ fontSize: 10, color: "var(--text-muted)", borderTop: "1px solid var(--border)", paddingTop: 8 }}>
        ↻ = vérifier/télécharger les mises à jour • 🗑 = supprimer (libère l'espace disque)
      </div>
    </div>
  );
}
