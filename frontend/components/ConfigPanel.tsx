"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "../lib/config";
import { isTauri, isAutostartEnabled, setAutostart } from "../lib/desktop";

interface Skill {
  name: string;
  trigger: string;
  description: string;
  icon: string;
  prompt: string;
}

const TAB_HINTS: Record<"prompt" | "skills" | "memory" | "settings", string> = {
  prompt: "Instructions de base envoyées au modèle à chaque conversation",
  skills: "Raccourcis slash-command réutilisables (ex : /update)",
  memory: "Contexte global et profil utilisateur injectés automatiquement",
  settings: "Comportement de l'agent : confirmations, contexte, planificateur…",
};

export default function ConfigPanel() {
  const [systemPrompt, setSystemPrompt] = useState("");
  const [savedPrompt, setSavedPrompt] = useState("");
  const [skills, setSkills] = useState<Skill[]>([]);
  const [tab, setTab] = useState<"prompt" | "skills" | "memory" | "settings">("prompt");
  const [context, setContext] = useState("");
  const [profile, setProfile] = useState("");
  const [memOk, setMemOk] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveOk, setSaveOk] = useState(false);

  // Réglages modifiables à chaud
  const [setSchema, setSetSchema] = useState<Record<string, any>>({});
  const [setValues, setSetValues] = useState<Record<string, any>>({});
  const [setOk, setSetOk] = useState("");

  // Skill editor
  const [editSkill, setEditSkill] = useState<Skill | null>(null);
  const [newSkill, setNewSkill] = useState(false);

  // Intégrations desktop (Tauri) : lancement au démarrage
  const [desktop, setDesktop] = useState(false);
  const [autostart, setAutostartState] = useState(false);

  useEffect(() => {
    if (!isTauri()) return;
    setDesktop(true);
    isAutostartEnabled().then(setAutostartState);
  }, []);

  const toggleAutostart = async (on: boolean) => {
    setAutostartState(on);
    await setAutostart(on);
  };

  const emptySkill = (): Skill => ({ name: "", trigger: "/", description: "", icon: "⚡", prompt: "" });

  useEffect(() => {
    fetch(`${API_BASE}/config/system-prompt`)
      .then(r => r.json()).then(d => { setSystemPrompt(d.content); setSavedPrompt(d.content); }).catch(() => {});
    fetch(`${API_BASE}/config/context`).then(r => r.json()).then(d => setContext(d.content)).catch(() => {});
    fetch(`${API_BASE}/config/profile`).then(r => r.json()).then(d => setProfile(d.content)).catch(() => {});
    fetch(`${API_BASE}/config/settings`).then(r => r.json())
      .then(d => { setSetSchema(d.schema); setSetValues(d.values); }).catch(() => {});
    fetchSkills();
  }, []);

  const saveSettings = async () => {
    const r = await fetch(`${API_BASE}/config/settings`, {
      method: "PUT", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ values: setValues }),
    });
    if (r.ok) {
      const d = await r.json();
      setSetValues(d.values);
      setSetOk("✓ Enregistré"); setTimeout(() => setSetOk(""), 2000);
    } else {
      const d = await r.json().catch(() => ({}));
      setSetOk("✗ " + (d.detail || "Erreur")); setTimeout(() => setSetOk(""), 3000);
    }
  };

  const saveMemory = async () => {
    await fetch(`${API_BASE}/config/context`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content: context }),
    });
    await fetch(`${API_BASE}/config/profile`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content: profile }),
    });
    setMemOk("✓ Enregistré"); setTimeout(() => setMemOk(""), 2000);
  };

  const fetchSkills = () => {
    fetch(`${API_BASE}/config/skills`)
      .then(r => r.json()).then(setSkills).catch(() => {});
  };

  const savePrompt = async () => {
    setSaving(true);
    await fetch(`${API_BASE}/config/system-prompt`, {
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
    await fetch(`${API_BASE}/config/skills/${encodeURIComponent(name)}`, { method: "DELETE" });
    fetchSkills();
  };

  const saveSkill = async (skill: Skill) => {
    await fetch(`${API_BASE}/config/skills`, {
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
        {(["prompt", "skills", "memory", "settings"] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            title={TAB_HINTS[t]}
            style={{
              padding: "4px 14px", borderRadius: 4, cursor: "pointer", fontSize: 11,
              background: tab === t ? "var(--accent)" : "var(--border)",
              border: "none", color: tab === t ? "var(--accent-contrast)" : "var(--text)", fontWeight: tab === t ? 700 : 400,
            }}>
            {t === "prompt" ? "System Prompt" : t === "skills" ? "Skills" : t === "memory" ? "Mémoire" : "Réglages"}
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
                border: "none", color: isDirty ? "var(--accent-contrast)" : "var(--text-muted)",
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
                    background: "var(--accent)", border: "none", color: "var(--accent-contrast)",
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

      {/* Mémoire : contexte global + profil utilisateur */}
      {tab === "memory" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ fontSize: 10, color: "var(--text-muted)" }}>
            Ces notes locales (<code>~/.config/mi-saina/</code>) sont injectées automatiquement dans chaque conversation. Jamais versionnées.
          </div>

          <div>
            <div style={{ fontSize: 11, color: "var(--accent)", fontWeight: 700, marginBottom: 4 }}>Contexte global (context.md)</div>
            <div style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 4 }}>Qui tu es, ta machine, tes habitudes — instructions persistantes.</div>
            <textarea value={context} onChange={e => setContext(e.target.value)} rows={6}
              placeholder="Ex : Je suis prof de maths, mes projets LaTeX sont dans ~/Documents/GitHub, réponds en français concis."
              style={{ width: "100%", boxSizing: "border-box", background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)", padding: 10, borderRadius: 6, fontSize: 12, fontFamily: "monospace", resize: "vertical", outline: "none", lineHeight: 1.5 }} />
          </div>

          <div>
            <div style={{ fontSize: 11, color: "var(--green)", fontWeight: 700, marginBottom: 4 }}>Profil mémorisé (profile.md)</div>
            <div style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 4 }}>Préférences apprises automatiquement (via [REMEMBER: …]). Modifiable à la main.</div>
            <textarea value={profile} onChange={e => setProfile(e.target.value)} rows={6}
              placeholder="(vide — se remplit quand mi-saina mémorise tes préférences)"
              style={{ width: "100%", boxSizing: "border-box", background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)", padding: 10, borderRadius: 6, fontSize: 12, fontFamily: "monospace", resize: "vertical", outline: "none", lineHeight: 1.5 }} />
          </div>

          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <button onClick={saveMemory}
              style={{ background: "var(--accent)", border: "none", color: "var(--accent-contrast)", padding: "6px 16px", borderRadius: 4, cursor: "pointer", fontSize: 12, fontWeight: 700 }}>
              Sauvegarder
            </button>
            {memOk && <span style={{ fontSize: 11, color: "var(--green)" }}>{memOk}</span>}
          </div>
        </div>
      )}

      {/* Réglages : comportement de l'agent (appliqués à chaud, persistés) */}
      {tab === "settings" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ fontSize: 10, color: "var(--text-muted)" }}>
            Appliqués immédiatement et persistés (<code>~/.config/mi-saina/settings.json</code>), sans redémarrage.
          </div>

          {desktop && (
            <div style={{
              display: "flex", flexDirection: "column", gap: 4,
              padding: "8px 10px", background: "var(--bg)",
              border: "1px solid var(--accent)", borderRadius: 6,
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <label style={{ fontSize: 11, color: "var(--text)", fontWeight: 700, flex: 1 }}>Lancer au démarrage de la session</label>
                <input type="checkbox" checked={autostart}
                  onChange={e => toggleAutostart(e.target.checked)}
                  style={{ width: 16, height: 16, cursor: "pointer", accentColor: "var(--accent)" }} />
              </div>
              <div style={{ fontSize: 10, color: "var(--text-muted)", lineHeight: 1.4 }}>
                Démarre mi-saina automatiquement (réduit dans la barre système) à l&apos;ouverture de session.
              </div>
            </div>
          )}

          {Object.keys(setSchema).length === 0 && (
            <div style={{ color: "var(--text-muted)", fontStyle: "italic", fontSize: 11 }}>Chargement…</div>
          )}

          {Object.entries(setSchema).map(([key, spec]: [string, any]) => (
            <div key={key} style={{
              display: "flex", flexDirection: "column", gap: 4,
              padding: "8px 10px", background: "var(--bg)",
              border: "1px solid var(--border)", borderRadius: 6,
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <label style={{ fontSize: 11, color: "var(--text)", fontWeight: 700, flex: 1 }}>{spec.label}</label>

                {spec.type === "bool" && (
                  <input type="checkbox" checked={!!setValues[key]}
                    onChange={e => setSetValues({ ...setValues, [key]: e.target.checked })}
                    style={{ width: 16, height: 16, cursor: "pointer", accentColor: "var(--accent)" }} />
                )}

                {spec.type === "choice" && (
                  <select value={setValues[key] ?? ""}
                    onChange={e => setSetValues({ ...setValues, [key]: e.target.value })}
                    style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text)", padding: "4px 8px", borderRadius: 4, fontSize: 11, outline: "none", cursor: "pointer" }}>
                    {spec.choices.map((c: string) => <option key={c} value={c}>{c}</option>)}
                  </select>
                )}

                {spec.type === "int" && (
                  <input type="number" value={setValues[key] ?? 0}
                    min={spec.min} max={spec.max} step={spec.step || 1}
                    onChange={e => setSetValues({ ...setValues, [key]: Number(e.target.value) })}
                    style={{ width: 90, background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text)", padding: "4px 8px", borderRadius: 4, fontSize: 11, outline: "none", textAlign: "right" }} />
                )}
              </div>
              {spec.help && <div style={{ fontSize: 10, color: "var(--text-muted)", lineHeight: 1.4 }}>{spec.help}</div>}
              {spec.type === "int" && (
                <div style={{ fontSize: 9, color: "var(--text-muted)" }}>plage : {spec.min}–{spec.max}</div>
              )}
            </div>
          ))}

          {Object.keys(setSchema).length > 0 && (
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <button onClick={saveSettings}
                style={{ background: "var(--accent)", border: "none", color: "var(--accent-contrast)", padding: "6px 16px", borderRadius: 4, cursor: "pointer", fontSize: 12, fontWeight: 700 }}>
                Sauvegarder
              </button>
              {setOk && <span style={{ fontSize: 11, color: setOk.startsWith("✓") ? "var(--green)" : "var(--red)" }}>{setOk}</span>}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
