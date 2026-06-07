"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "../lib/config";
import { isTauri, isAutostartEnabled, setAutostart } from "../lib/desktop";
import { getLang, setLang, Lang, t } from "../lib/i18n";
import ModelPanel from "./ModelPanel";

interface Skill {
  name: string;
  trigger: string;
  description: string;
  icon: string;
  prompt: string;
}

type CfTab = "prompt" | "skills" | "memory" | "models" | "settings";

const TAB_HINTS: Record<CfTab, string> = {
  prompt: t("cfHintPrompt"),
  skills: t("cfHintSkills"),
  memory: t("cfHintMemory"),
  models: t("cfHintModels"),
  settings: t("cfHintSettings"),
};

export default function ConfigPanel({ onModelChange }: { onModelChange?: (m: string) => void } = {}) {
  const [systemPrompt, setSystemPrompt] = useState("");
  const [savedPrompt, setSavedPrompt] = useState("");
  const [skills, setSkills] = useState<Skill[]>([]);
  const [tab, setTab] = useState<CfTab>("prompt");
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

  // Mise à jour du logiciel
  const [upd, setUpd] = useState<{ current?: string; latest?: string | null; update_available?: boolean; install_type?: string } | null>(null);
  const [checking, setChecking] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [updLog, setUpdLog] = useState<string[]>([]);

  const checkUpdate = async () => {
    setChecking(true);
    try {
      const r = await fetch(`${API_BASE}/update/check`);
      setUpd(await r.json());
    } catch { /* backend indisponible */ }
    setChecking(false);
  };

  const applyUpdate = () => {
    setUpdating(true);
    setUpdLog([]);
    try {
      const es = new EventSource(`${API_BASE}/update/apply`);
      es.onmessage = (e) => {
        try {
          const d = JSON.parse(e.data);
          if (d.done) { es.close(); setUpdating(false); checkUpdate(); return; }
          if (d.log) setUpdLog(l => [...l, d.log]);
        } catch {}
      };
      es.onerror = () => { es.close(); setUpdating(false); }; // un redémarrage des services coupe le flux : normal
    } catch { setUpdating(false); }
  };

  useEffect(() => {
    if (!isTauri()) return;
    setDesktop(true);
    isAutostartEnabled().then(setAutostartState);
  }, []);

  useEffect(() => { checkUpdate(); }, []);

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
      setSetOk(t("saved")); setTimeout(() => setSetOk(""), 2000);
      // Changement de langue → synchronise l'UI et recharge (i18n par rechargement).
      const lang = d.values?.LANGUAGE as Lang | undefined;
      if (lang && lang !== getLang()) { setLang(lang); window.location.reload(); }
    } else {
      const d = await r.json().catch(() => ({}));
      setSetOk("✗ " + (d.detail || "Erreur")); setTimeout(() => setSetOk(""), 3000);
    }
  };

  // Base documentaire (RAG)
  const [ragFolder, setRagFolder] = useState("");
  const [ragStat, setRagStat] = useState<{ files: number; chunks: number } | null>(null);
  const [ragBusy, setRagBusy] = useState(false);
  const [ragLog, setRagLog] = useState<string[]>([]);

  const loadRagStatus = async () => {
    try { const r = await fetch(`${API_BASE}/rag/status`); setRagStat(await r.json()); } catch { /* indispo */ }
  };
  useEffect(() => { loadRagStatus(); }, []);

  const indexRag = () => {
    const folder = ragFolder.trim();
    if (!folder) return;
    setRagBusy(true);
    setRagLog([]);
    try {
      const es = new EventSource(`${API_BASE}/rag/index?folder=${encodeURIComponent(folder)}`);
      es.onmessage = (e) => {
        try {
          const d = JSON.parse(e.data);
          if (d.done) { es.close(); setRagBusy(false); loadRagStatus(); return; }
          if (d.error) { setRagLog(l => [...l, `✗ ${d.error}`]); es.close(); setRagBusy(false); return; }
          if (d.status) setRagLog(l => [...l.slice(-40), d.status]);
        } catch {}
      };
      es.onerror = () => { es.close(); setRagBusy(false); loadRagStatus(); };
    } catch { setRagBusy(false); }
  };

  const clearRag = async () => {
    if (!confirm(t("cfRagClearConfirm"))) return;
    await fetch(`${API_BASE}/rag/clear`, { method: "DELETE" });
    loadRagStatus();
  };

  const saveMemory = async () => {
    await fetch(`${API_BASE}/config/context`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content: context }),
    });
    await fetch(`${API_BASE}/config/profile`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content: profile }),
    });
    setMemOk(t("saved")); setTimeout(() => setMemOk(""), 2000);
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
        {(["prompt", "skills", "memory", "models", "settings"] as const).map(tb => (
          <button key={tb} onClick={() => setTab(tb)}
            title={TAB_HINTS[tb]}
            style={{
              padding: "4px 14px", borderRadius: 4, cursor: "pointer", fontSize: 11,
              background: tab === tb ? "var(--accent)" : "var(--border)",
              border: "none", color: tab === tb ? "var(--accent-contrast)" : "var(--text)", fontWeight: tab === tb ? 700 : 400,
            }}>
            {tb === "prompt" ? t("cfTabPrompt") : tb === "skills" ? t("cfTabSkills") : tb === "memory" ? t("cfTabMemory") : tb === "models" ? t("navModels") : t("cfTabSettings")}
          </button>
        ))}
      </div>

      {/* System Prompt Editor */}
      {tab === "prompt" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ fontSize: 10, color: "var(--text-muted)" }}>
            {t("cfPromptIntro")}
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
              {saving ? t("cfSaving") : saveOk ? t("cfSavedOk") : t("save")}
            </button>
            {isDirty && (
              <button onClick={() => setSystemPrompt(savedPrompt)}
                style={{ background: "none", border: "1px solid var(--border)", color: "var(--text-muted)", padding: "6px 12px", borderRadius: 4, cursor: "pointer", fontSize: 11 }}>
                {t("cancel")}
              </button>
            )}
            {isDirty && <span style={{ fontSize: 10, color: "var(--yellow)" }}>{t("cfUnsaved")}</span>}
          </div>
        </div>
      )}

      {/* Skills Manager */}
      {tab === "skills" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ fontSize: 10, color: "var(--text-muted)" }}>
            {t("cfSkillsIntro")} <code style={{ color: "var(--accent)" }}>/trigger</code> {t("cfSkillsIntro2")}
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
                  {t("cfEdit")}
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
            {t("cfNewSkill")}
          </button>

          {/* Éditeur de skill */}
          {editSkill && (
            <div style={{
              background: "var(--bg)", border: "1px solid var(--accent)", borderRadius: 8,
              padding: 14, display: "flex", flexDirection: "column", gap: 8,
            }}>
              <div style={{ fontSize: 11, color: "var(--accent)", fontWeight: 700 }}>
                {newSkill ? t("cfNewSkillTitle") : `${t("cfEditTitle")} ${editSkill.name}`}
              </div>
              {[
                { key: "icon", label: t("cfIcon"), placeholder: "⚡" },
                { key: "name", label: t("cfName"), placeholder: "mon-skill" },
                { key: "trigger", label: t("cfTrigger"), placeholder: "/mon-skill" },
                { key: "description", label: t("cfDescription"), placeholder: "" },
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
                <label style={{ fontSize: 10, color: "var(--text-muted)", width: 80, flexShrink: 0, paddingTop: 6 }}>{t("cfPrompt")}</label>
                <textarea
                  value={editSkill.prompt}
                  onChange={e => setEditSkill({ ...editSkill, prompt: e.target.value })}
                  placeholder={t("cfSkillPromptPlaceholder")}
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
            {t("cfMemIntro")}
          </div>

          <div>
            <div style={{ fontSize: 11, color: "var(--accent)", fontWeight: 700, marginBottom: 4 }}>{t("cfGlobalCtx")}</div>
            <div style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 4 }}>{t("cfGlobalCtxHint")}</div>
            <textarea value={context} onChange={e => setContext(e.target.value)} rows={6}
              placeholder={t("cfCtxPlaceholder")}
              style={{ width: "100%", boxSizing: "border-box", background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)", padding: 10, borderRadius: 6, fontSize: 12, fontFamily: "monospace", resize: "vertical", outline: "none", lineHeight: 1.5 }} />
          </div>

          <div>
            <div style={{ fontSize: 11, color: "var(--green)", fontWeight: 700, marginBottom: 4 }}>{t("cfProfile")}</div>
            <div style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 4 }}>{t("cfProfileHint")}</div>
            <textarea value={profile} onChange={e => setProfile(e.target.value)} rows={6}
              placeholder={t("cfProfilePlaceholder")}
              style={{ width: "100%", boxSizing: "border-box", background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)", padding: 10, borderRadius: 6, fontSize: 12, fontFamily: "monospace", resize: "vertical", outline: "none", lineHeight: 1.5 }} />
          </div>

          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <button onClick={saveMemory}
              style={{ background: "var(--accent)", border: "none", color: "var(--accent-contrast)", padding: "6px 16px", borderRadius: 4, cursor: "pointer", fontSize: 12, fontWeight: 700 }}>
              {t("save")}
            </button>
            {memOk && <span style={{ fontSize: 11, color: "var(--green)" }}>{memOk}</span>}
          </div>

          {/* Base documentaire (RAG) */}
          <div style={{
            marginTop: 6, padding: "10px 12px", background: "var(--bg)",
            border: "1px solid var(--border)", borderRadius: 8, display: "flex", flexDirection: "column", gap: 8,
          }}>
            <div style={{ fontSize: 11, color: "var(--accent)", fontWeight: 700 }}>{t("cfRagTitle")}</div>
            <div style={{ fontSize: 10, color: "var(--text-muted)" }}>
              {t("cfRagHint")} <code>[RAG: …]</code>. {t("cfRagLocal")} {""}<code>nomic-embed-text</code>).
              {ragStat && <> · <b>{ragStat.files}</b> {t("cfRagFiles")}, <b>{ragStat.chunks}</b> {t("cfRagChunks")}</>}
            </div>
            <div style={{ display: "flex", gap: 6 }}>
              <input value={ragFolder} onChange={e => setRagFolder(e.target.value)} disabled={ragBusy}
                placeholder={t("cfRagFolderPlaceholder")}
                style={{ flex: 1, background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text)", padding: "5px 8px", borderRadius: 4, fontSize: 11, outline: "none" }} />
              <button onClick={indexRag} disabled={ragBusy || !ragFolder.trim()}
                style={{ background: ragBusy ? "var(--border)" : "var(--accent)", border: "none", color: ragBusy ? "var(--text-muted)" : "var(--accent-contrast)", padding: "5px 12px", borderRadius: 4, cursor: ragBusy ? "default" : "pointer", fontSize: 11, fontWeight: 700 }}>
                {ragBusy ? t("cfRagIndexing") : t("cfRagIndex")}
              </button>
              {ragStat && ragStat.chunks > 0 && (
                <button onClick={clearRag} disabled={ragBusy} title={t("cfRagClearTip")}
                  style={{ background: "rgba(248,81,73,0.12)", border: "1px solid var(--red)", color: "var(--red)", padding: "5px 10px", borderRadius: 4, cursor: "pointer", fontSize: 11 }}>
                  {t("cfRagClear")}
                </button>
              )}
            </div>
            {ragLog.length > 0 && (
              <pre style={{ margin: 0, maxHeight: 140, overflowY: "auto", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 6, padding: "6px 8px", fontSize: 10, color: "var(--text-muted)", whiteSpace: "pre-wrap" }}>{ragLog.join("\n")}</pre>
            )}
          </div>
        </div>
      )}

      {/* Modèles : gestion avancée (télécharger / mettre à jour / supprimer / importer) */}
      {tab === "models" && (
        <ModelPanel onModelChange={(m) => onModelChange?.(m)} />
      )}

      {/* Réglages : comportement de l'agent (appliqués à chaud, persistés) */}
      {tab === "settings" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ fontSize: 10, color: "var(--text-muted)" }}>
            {t("cfSettingsIntro")}
          </div>

          {/* Mise à jour du logiciel */}
          <div style={{
            display: "flex", flexDirection: "column", gap: 8,
            padding: "10px 12px", background: "var(--bg)",
            border: "1px solid var(--border)", borderRadius: 8,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text)", flex: 1 }}>
                mi-saina {upd?.current ? `v${upd.current}` : ""}
              </span>
              {upd?.update_available
                ? <span style={{ fontSize: 10, fontWeight: 700, color: "var(--accent-contrast)", background: "var(--accent)", borderRadius: 12, padding: "2px 8px" }}>{t("cfUpdAvail")} v{upd.latest}</span>
                : upd?.latest
                  ? <span style={{ fontSize: 10, color: "var(--green)" }}>{t("cfUpToDate")}</span>
                  : <span style={{ fontSize: 10, color: "var(--text-muted)" }}>{t("cfUpdUnknown")}</span>}
            </div>
            <div style={{ fontSize: 10, color: "var(--text-muted)" }}>
              {t("cfUpdSource")} {upd?.install_type === "run" ? t("cfUpdRun") : upd?.install_type === "source" ? t("cfUpdGit") : "—"}.
              {" "}{t("cfUpdAuto")}
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button onClick={checkUpdate} disabled={checking || updating}
                style={{ background: "var(--border)", border: "none", color: "var(--text)", padding: "6px 12px", borderRadius: 4, cursor: "pointer", fontSize: 11 }}>
                {checking ? t("cfChecking") : t("cfCheck")}
              </button>
              <button onClick={applyUpdate} disabled={updating || !upd?.update_available}
                title={upd?.update_available ? t("cfUpdateTip") : t("cfNoUpdateTip")}
                style={{
                  background: upd?.update_available && !updating ? "var(--accent)" : "var(--border)",
                  border: "none", color: upd?.update_available && !updating ? "var(--accent-contrast)" : "var(--text-muted)",
                  padding: "6px 14px", borderRadius: 4, cursor: upd?.update_available ? "pointer" : "default", fontSize: 11, fontWeight: 700,
                }}>
                {updating ? t("cfUpdating") : t("cfUpdateBtn")}
              </button>
            </div>
            {updLog.length > 0 && (
              <pre style={{
                margin: 0, maxHeight: 160, overflowY: "auto", background: "var(--surface)",
                border: "1px solid var(--border)", borderRadius: 6, padding: "6px 8px",
                fontSize: 10, color: "var(--text-muted)", whiteSpace: "pre-wrap", wordBreak: "break-word",
              }}>{updLog.join("\n")}</pre>
            )}
          </div>

          {desktop && (
            <div style={{
              display: "flex", flexDirection: "column", gap: 4,
              padding: "8px 10px", background: "var(--bg)",
              border: "1px solid var(--accent)", borderRadius: 6,
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <label style={{ fontSize: 11, color: "var(--text)", fontWeight: 700, flex: 1 }}>{t("cfAutostart")}</label>
                <input type="checkbox" checked={autostart}
                  onChange={e => toggleAutostart(e.target.checked)}
                  style={{ width: 16, height: 16, cursor: "pointer", accentColor: "var(--accent)" }} />
              </div>
              <div style={{ fontSize: 10, color: "var(--text-muted)", lineHeight: 1.4 }}>
                {t("cfAutostartHint")}
              </div>
            </div>
          )}

          {Object.keys(setSchema).length === 0 && (
            <div style={{ color: "var(--text-muted)", fontStyle: "italic", fontSize: 11 }}>{t("cfLoading")}</div>
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
                <div style={{ fontSize: 9, color: "var(--text-muted)" }}>{t("cfRange")} : {spec.min}–{spec.max}</div>
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
