"use client";

import { useEffect, useState } from "react";

interface Skill {
  name: string;
  trigger: string;
  description: string;
  icon: string;
  prompt: string;
}

export default function ConfigPanel() {
  const [systemPrompt, setSystemPrompt] = useState("");
  const [savedPrompt, setSavedPrompt] = useState("");
  const [skills, setSkills] = useState<Skill[]>([]);
  const [tab, setTab] = useState<"prompt" | "skills">("prompt");
  const [saving, setSaving] = useState(false);
  const [saveOk, setSaveOk] = useState(false);

  // Skill editor
  const [editSkill, setEditSkill] = useState<Skill | null>(null);
  const [newSkill, setNewSkill] = useState(false);

  const emptySkill = (): Skill => ({ name: "", trigger: "/", description: "", icon: "⚡", prompt: "" });

  useEffect(() => {
    fetch("http://localhost:8000/config/system-prompt")
      .then(r => r.json()).then(d => { setSystemPrompt(d.content); setSavedPrompt(d.content); }).catch(() => {});
    fetchSkills();
  }, []);

  const fetchSkills = () => {
    fetch("http://localhost:8000/config/skills")
      .then(r => r.json()).then(setSkills).catch(() => {});
  };

  const savePrompt = async () => {
    setSaving(true);
    await fetch("http://localhost:8000/config/system-prompt", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: systemPrompt }),
    });
    setSavedPrompt(systemPrompt);
    setSaving(false);
    setSaveOk(true);
    setTimeout(() => setSaveOk(false), 2000);
  };

  const deleteSkill = async (name: string) => {
    if (!confirm(`Supprimer le skill "${name}" ?`)) return;
    await fetch(`http://localhost:8000/config/skills/${encodeURIComponent(name)}`, { method: "DELETE" });
    fetchSkills();
  };

  const saveSkill = async (skill: Skill) => {
    await fetch("http://localhost:8000/config/skills", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(skill),
    });
    setEditSkill(null);
    setNewSkill(false);
    fetchSkills();
  };

  const isDirty = systemPrompt !== savedPrompt;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Tabs */}
      <div style={{ display: "flex", gap: 6 }}>
        {(["prompt", "skills"] as const).map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            padding: "4px 14px", borderRadius: 4, cursor: "pointer", fontSize: 11,
            background: tab === t ? "var(--accent)" : "var(--border)",
            border: "none", color: tab === t ? "#000" : "var(--text)", fontWeight: tab === t ? 700 : 400,
          }}>
            {t === "prompt" ? "System Prompt" : "Skills"}
          </button>
        ))}
      </div>

      {/* System Prompt Editor */}
      {tab === "prompt" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ fontSize: 10, color: "var(--text-muted)" }}>
            Instructions de base envoyées à chaque prompt, pour tous les modèles.
          </div>
          <textarea
            value={systemPrompt}
            onChange={e => setSystemPrompt(e.target.value)}
            rows={14}
            style={{
              background: "var(--bg)", border: `1px solid ${isDirty ? "var(--yellow)" : "var(--border)"}`,
              color: "var(--text)", padding: "10px", borderRadius: 6,
              fontSize: 12, fontFamily: "'JetBrains Mono', monospace", resize: "vertical",
              outline: "none", lineHeight: 1.5,
            }}
          />
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <button
              onClick={savePrompt}
              disabled={saving || !isDirty}
              style={{
                background: isDirty ? "var(--accent)" : "var(--border)",
                border: "none", color: isDirty ? "#000" : "var(--text-muted)",
                padding: "6px 16px", borderRadius: 4, cursor: isDirty ? "pointer" : "default",
                fontSize: 12, fontWeight: 700,
              }}
            >
              {saving ? "Sauvegarde..." : saveOk ? "✓ Sauvegardé" : "Sauvegarder"}
            </button>
            {isDirty && (
              <button onClick={() => setSystemPrompt(savedPrompt)}
                style={{ background: "none", border: "1px solid var(--border)", color: "var(--text-muted)", padding: "6px 12px", borderRadius: 4, cursor: "pointer", fontSize: 11 }}>
                Annuler
              </button>
            )}
            {isDirty && <span style={{ fontSize: 10, color: "var(--yellow)" }}>● Modifications non sauvegardées</span>}
          </div>
        </div>
      )}

      {/* Skills Manager */}
      {tab === "skills" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ fontSize: 10, color: "var(--text-muted)" }}>
            Skills = raccourcis slash-command. Tapez <code style={{ color: "var(--accent)" }}>/trigger</code> dans le chat pour les invoquer.
          </div>

          {/* Liste des skills */}
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {skills.map(s => (
              <div key={s.name} style={{
                display: "flex", alignItems: "center", gap: 8,
                padding: "7px 10px", background: "var(--bg)",
                border: "1px solid var(--border)", borderRadius: 6,
              }}>
                <span style={{ fontSize: 16 }}>{s.icon}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <code style={{ fontSize: 11, color: "var(--accent)", background: "var(--border)", padding: "1px 5px", borderRadius: 3 }}>
                      {s.trigger}
                    </code>
                    <span style={{ fontSize: 11, color: "var(--text)" }}>{s.description}</span>
                  </div>
                </div>
                <button onClick={() => setEditSkill(s)}
                  style={{ background: "none", border: "1px solid var(--border)", color: "var(--text-muted)", padding: "2px 8px", borderRadius: 3, cursor: "pointer", fontSize: 10 }}>
                  Éditer
                </button>
                <button onClick={() => deleteSkill(s.name)}
                  style={{ background: "none", border: "none", color: "var(--red)", cursor: "pointer", fontSize: 14 }}>
                  🗑
                </button>
              </div>
            ))}
          </div>

          <button
            onClick={() => { setEditSkill(emptySkill()); setNewSkill(true); }}
            style={{
              background: "var(--border)", border: "1px dashed var(--accent)", color: "var(--accent)",
              padding: "8px", borderRadius: 6, cursor: "pointer", fontSize: 11, width: "100%",
            }}
          >
            + Nouveau skill
          </button>

          {/* Éditeur de skill */}
          {editSkill && (
            <div style={{
              background: "var(--bg)", border: "1px solid var(--accent)", borderRadius: 8,
              padding: 14, display: "flex", flexDirection: "column", gap: 8,
            }}>
              <div style={{ fontSize: 11, color: "var(--accent)", fontWeight: 700 }}>
                {newSkill ? "Nouveau skill" : `Éditer: ${editSkill.name}`}
              </div>
              {[
                { key: "icon", label: "Icône", placeholder: "⚡" },
                { key: "name", label: "Nom", placeholder: "mon-skill" },
                { key: "trigger", label: "Trigger", placeholder: "/mon-skill" },
                { key: "description", label: "Description", placeholder: "Ce que fait ce skill" },
              ].map(f => (
                <div key={f.key} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <label style={{ fontSize: 10, color: "var(--text-muted)", width: 80, flexShrink: 0 }}>{f.label}</label>
                  <input
                    value={(editSkill as any)[f.key]}
                    onChange={e => setEditSkill({ ...editSkill, [f.key]: e.target.value })}
                    placeholder={f.placeholder}
                    style={{
                      flex: 1, background: "var(--surface)", border: "1px solid var(--border)",
                      color: "var(--text)", padding: "5px 8px", borderRadius: 4, fontSize: 11,
                      outline: "none", fontFamily: "inherit",
                    }}
                  />
                </div>
              ))}
              <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
                <label style={{ fontSize: 10, color: "var(--text-muted)", width: 80, flexShrink: 0, paddingTop: 6 }}>Prompt</label>
                <textarea
                  value={editSkill.prompt}
                  onChange={e => setEditSkill({ ...editSkill, prompt: e.target.value })}
                  placeholder="Instructions envoyées au LLM quand ce skill est invoqué..."
                  rows={4}
                  style={{
                    flex: 1, background: "var(--surface)", border: "1px solid var(--border)",
                    color: "var(--text)", padding: "5px 8px", borderRadius: 4, fontSize: 11,
                    outline: "none", fontFamily: "inherit", resize: "vertical",
                  }}
                />
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button onClick={() => saveSkill(editSkill)}
                  disabled={!editSkill.name || !editSkill.trigger || !editSkill.prompt}
                  style={{
                    background: "var(--accent)", border: "none", color: "#000",
                    padding: "6px 16px", borderRadius: 4, cursor: "pointer", fontSize: 11, fontWeight: 700,
                  }}>
                  Sauvegarder
                </button>
                <button onClick={() => { setEditSkill(null); setNewSkill(false); }}
                  style={{ background: "var(--border)", border: "none", color: "var(--text)", padding: "6px 12px", borderRadius: 4, cursor: "pointer", fontSize: 11 }}>
                  Annuler
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
