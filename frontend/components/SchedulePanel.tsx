"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "../lib/config";
import { t } from "../lib/i18n";

interface Job {
  id: string;
  name: string;
  prompt: string;
  schedule: string;
  enabled: boolean;
  last_run: string | null;
  last_result: string;
  last_session?: string;
}

const API = `${API_BASE}/schedule`;
const DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"];

function describe(s: string): string {
  if (s.startsWith("every:")) return `toutes les ${s.split(":")[1]} min`;
  if (s.startsWith("daily:")) return `chaque jour à ${s.split(":").slice(1).join(":")}`;
  if (s.startsWith("weekly:")) { const [, d, h, m] = s.split(":"); return `chaque ${DAYS[+d]} à ${h}:${m}`; }
  return s;
}

export default function SchedulePanel({ onOpenSession }: { onOpenSession?: (id: string) => void }) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [adding, setAdding] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  // formulaire
  const [name, setName] = useState("");
  const [prompt, setPrompt] = useState("");
  const [freq, setFreq] = useState<"every" | "daily" | "weekly">("daily");
  const [minutes, setMinutes] = useState("60");
  const [time, setTime] = useState("09:00");
  const [dow, setDow] = useState("6");

  const fetchJobs = () => fetch(API).then(r => r.json()).then(setJobs).catch(() => {});
  useEffect(() => { fetchJobs(); }, []);

  const buildSchedule = () => {
    if (freq === "every") return `every:${parseInt(minutes) || 60}`;
    if (freq === "daily") return `daily:${time}`;
    return `weekly:${dow}:${time}`;
  };

  const create = async () => {
    if (!name.trim() || !prompt.trim()) return;
    await fetch(API, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, prompt, schedule: buildSchedule() }) });
    setName(""); setPrompt(""); setAdding(false); fetchJobs();
  };

  const runNow = async (id: string) => { setBusy(id); await fetch(`${API}/${id}/run`, { method: "POST" }); setBusy(null); fetchJobs(); };
  const toggle = async (id: string) => { await fetch(`${API}/${id}/toggle`, { method: "POST" }); fetchJobs(); };
  const remove = async (id: string) => { if (!confirm(t("spDeleteConfirm"))) return; await fetch(`${API}/${id}`, { method: "DELETE" }); fetchJobs(); };

  const inp = { background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text)", padding: "5px 8px", borderRadius: 4, fontSize: 11, outline: "none", fontFamily: "inherit" } as const;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ fontSize: 10, color: "var(--text-muted)" }}>
        {t("spIntro")}
      </div>

      {jobs.length === 0 && !adding && (
        <div className="ms-empty">
          <span className="ms-empty-icon">⏰</span>
          <div>{t("spEmpty")}</div>
          <div style={{ fontSize: 11, opacity: 0.8 }}>{t("spEmptyHint")}</div>
        </div>
      )}

      {jobs.map(j => (
        <div key={j.id} style={{ background: "var(--bg)", border: "1px solid var(--border)", borderRadius: 6, padding: "8px 10px", opacity: j.enabled ? 1 : 0.55 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text)", flex: 1 }}>⏰ {j.name}</span>
            <button onClick={() => toggle(j.id)} title={j.enabled ? t("spDisable") : t("spEnable")}
              style={{ background: "none", border: "1px solid var(--border)", color: j.enabled ? "var(--green)" : "var(--text-muted)", borderRadius: 3, cursor: "pointer", fontSize: 10, padding: "2px 6px" }}>
              {j.enabled ? t("spActive") : t("spInactive")}
            </button>
            <button onClick={() => runNow(j.id)} disabled={busy === j.id} title={t("spRunNow")}
              style={{ background: "var(--border)", border: "none", color: "var(--text)", borderRadius: 3, cursor: "pointer", fontSize: 10, padding: "2px 6px" }}>
              {busy === j.id ? "…" : "▶"}
            </button>
            <button onClick={() => remove(j.id)} style={{ background: "none", border: "none", color: "var(--red)", cursor: "pointer", fontSize: 13 }}>🗑</button>
          </div>
          <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 3 }}>
            {describe(j.schedule)} · {j.last_run ? `${t("spLast")} : ${new Date(j.last_run).toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}` : t("spNever")}
          </div>
          {j.last_result && (
            <div onClick={() => j.last_session && onOpenSession?.(j.last_session)}
              title={j.last_session ? t("spOpenResult") : ""}
              style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 4, cursor: j.last_session ? "pointer" : "default", overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>
              {j.last_result}
            </div>
          )}
        </div>
      ))}

      {adding ? (
        <div style={{ background: "var(--bg)", border: "1px solid var(--accent)", borderRadius: 8, padding: 12, display: "flex", flexDirection: "column", gap: 8 }}>
          <input value={name} onChange={e => setName(e.target.value)} placeholder={t("spNamePlaceholder")} style={{ ...inp }} />
          <textarea value={prompt} onChange={e => setPrompt(e.target.value)} rows={3} placeholder={t("spPromptPlaceholder")} style={{ ...inp, resize: "vertical" }} />
          <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
            <select value={freq} onChange={e => setFreq(e.target.value as "every" | "daily" | "weekly")} style={{ ...inp }}>
              <option value="every">{t("spEveryX")}</option>
              <option value="daily">{t("spDaily")}</option>
              <option value="weekly">{t("spWeekly")}</option>
            </select>
            {freq === "every" && <input value={minutes} onChange={e => setMinutes(e.target.value)} style={{ ...inp, width: 60 }} />}
            {freq === "weekly" && (
              <select value={dow} onChange={e => setDow(e.target.value)} style={{ ...inp }}>
                {DAYS.map((d, i) => <option key={i} value={i}>{d}</option>)}
              </select>
            )}
            {(freq === "daily" || freq === "weekly") && <input type="time" value={time} onChange={e => setTime(e.target.value)} style={{ ...inp }} />}
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={create} disabled={!name.trim() || !prompt.trim()}
              style={{ background: "var(--accent)", border: "none", color: "var(--accent-contrast)", padding: "6px 14px", borderRadius: 4, cursor: "pointer", fontSize: 11, fontWeight: 700 }}>{t("spCreate")}</button>
            <button onClick={() => setAdding(false)} style={{ background: "var(--border)", border: "none", color: "var(--text)", padding: "6px 12px", borderRadius: 4, cursor: "pointer", fontSize: 11 }}>{t("cancel")}</button>
          </div>
        </div>
      ) : (
        <button onClick={() => setAdding(true)} style={{ background: "var(--border)", border: "1px dashed var(--accent)", color: "var(--accent)", padding: "8px", borderRadius: 6, cursor: "pointer", fontSize: 11, width: "100%" }}>
          {t("spNewTask")}
        </button>
      )}
    </div>
  );
}
