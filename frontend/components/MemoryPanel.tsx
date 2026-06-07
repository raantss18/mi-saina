"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "../lib/config";
import { t } from "../lib/i18n";

interface Session {
  id: string;
  title: string | null;
  updated_at: string;
}

interface SearchResult {
  role: string;
  content: string;
  score: number;
}

interface HistResult {
  session_id: string;
  title: string;
  role: string;
  snippet: string;
}

type NavPanel = "models" | "config" | "schedule" | null;

interface Props {
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewSession: (id: string) => void;
  refreshKey?: number;
  activePanel?: NavPanel;
  onNavigate?: (panel: NavPanel) => void;
}

const NAV: { id: NavPanel; icon: string; label: string }[] = [
  { id: null, icon: "💬", label: t("navChat") },
  { id: "models", icon: "⬡", label: t("navModels") },
  { id: "config", icon: "⚙", label: t("navConfig") },
  { id: "schedule", icon: "⏰", label: t("navTasks") },
];

export default function MemoryPanel({ activeSessionId, onSelectSession, onNewSession, refreshKey = 0, activePanel = null, onNavigate }: Props) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [histQuery, setHistQuery] = useState("");
  const [histResults, setHistResults] = useState<HistResult[]>([]);

  const fetchSessions = async () => {
    try {
      const res = await fetch(`${API_BASE}/memory/sessions`);
      if (res.ok) setSessions(await res.json());
    } catch {}
  };

  useEffect(() => { fetchSessions(); }, [refreshKey]);

  const handleNew = async () => {
    try {
      const res = await fetch(`${API_BASE}/memory/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: null }),
      });
      const data = await res.json();
      onNewSession(data.id);
      fetchSessions();
    } catch {}
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!confirm("Supprimer cette session ?")) return;
    await fetch(`${API_BASE}/memory/sessions/${id}`, { method: "DELETE" });
    fetchSessions();
  };

  const handleHistSearch = async () => {
    const q = histQuery.trim();
    if (!q) { setHistResults([]); return; }
    try {
      const res = await fetch(`${API_BASE}/memory/history-search?q=${encodeURIComponent(q)}`);
      if (res.ok) setHistResults(await res.json());
    } catch {}
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const res = await fetch(`${API_BASE}/memory/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: searchQuery, top_k: 5 }),
      });
      setSearchResults(await res.json());
    } catch {}
    setSearching(false);
  };

  return (
    <div style={{
      width: 240,
      background: "var(--surface)",
      borderRight: "1px solid var(--border)",
      display: "flex",
      flexDirection: "column",
      height: "100%",
      flexShrink: 0,
    }}>
      <div style={{ padding: "12px 10px 8px", borderBottom: "1px solid var(--border)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/mi-saina-icon.png" alt="mi-saina" width={22} height={22} style={{ borderRadius: 5 }} />
          <span style={{ color: "var(--text)", fontSize: 14, fontWeight: 700, letterSpacing: 0.2 }}>mi-saina</span>
        </div>

        {/* Navigation : Chat / Modèles / Config / Tâches */}
        <div style={{ display: "flex", flexDirection: "column", gap: 2, marginBottom: 8 }}>
          {NAV.map(item => {
            const active = activePanel === item.id;
            return (
              <button
                key={item.label}
                onClick={() => onNavigate?.(item.id)}
                title={item.label}
                style={{
                  display: "flex", alignItems: "center", gap: 8, width: "100%",
                  padding: "6px 8px", borderRadius: 6, cursor: "pointer", fontSize: 12,
                  border: "1px solid transparent", textAlign: "left",
                  background: active ? "var(--surface-2)" : "transparent",
                  color: active ? "var(--accent)" : "var(--text-muted)",
                  borderColor: active ? "var(--accent)" : "transparent",
                  fontWeight: active ? 700 : 400,
                }}
              >
                <span style={{ fontSize: 15, width: 18, textAlign: "center" }}>{item.icon}</span>
                {item.label}
              </button>
            );
          })}
        </div>

        <button
          onClick={handleNew}
          title={t("newSessionTip")}
          style={{
            width: "100%", padding: "6px", background: "var(--accent-dim, #20342a)",
            border: "1px solid var(--accent)", color: "var(--accent)", borderRadius: 4,
            cursor: "pointer", fontSize: 12,
          }}
        >
          {t("newSession")}
        </button>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "4px 0" }}>
        {sessions.length === 0 && (
          <div style={{ color: "var(--text-muted)", fontSize: 11, padding: "8px 12px" }}>
            {t("noSession")}
          </div>
        )}
        {sessions.map(s => (
          <div
            key={s.id}
            onClick={() => onSelectSession(s.id)}
            onMouseEnter={e => { if (s.id !== activeSessionId) e.currentTarget.style.background = "var(--surface-2)"; }}
            onMouseLeave={e => { if (s.id !== activeSessionId) e.currentTarget.style.background = "transparent"; }}
            style={{
              padding: "8px 12px",
              cursor: "pointer",
              background: s.id === activeSessionId ? "var(--border)" : "transparent",
              borderLeft: s.id === activeSessionId ? "2px solid var(--accent)" : "2px solid transparent",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              gap: 4,
              transition: "background 0.12s ease",
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 12, color: "var(--text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {s.title || "Session sans titre"}
              </div>
              <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 2 }}>
                {new Date(s.updated_at).toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}
              </div>
            </div>
            <button
              onClick={(e) => handleDelete(e, s.id)}
              style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: 12, padding: "0 2px", flexShrink: 0 }}
            >
              🗑
            </button>
          </div>
        ))}
      </div>

      <div style={{ borderTop: "1px solid var(--border)", padding: "8px 10px" }}>
        <div style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 4, letterSpacing: 0.5 }}>{t("histSearch")}</div>
        <div style={{ display: "flex", gap: 4 }}>
          <input
            value={histQuery}
            onChange={e => setHistQuery(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleHistSearch()}
            placeholder="Mot-clé dans tes anciens chats…"
            style={{
              flex: 1, background: "var(--bg)", border: "1px solid var(--border)",
              color: "var(--text)", padding: "4px 6px", borderRadius: 4, fontSize: 11, outline: "none",
            }}
          />
          <button onClick={handleHistSearch}
            style={{ background: "var(--border)", border: "none", color: "var(--text)", padding: "4px 8px", borderRadius: 4, cursor: "pointer", fontSize: 11 }}>
            🔍
          </button>
        </div>
        {histResults.length > 0 && (
          <div style={{ marginTop: 6, maxHeight: 180, overflowY: "auto" }}>
            {histResults.map((r, i) => (
              <div key={i}
                onClick={() => onSelectSession(r.session_id)}
                title="Ouvrir cette conversation"
                style={{
                  padding: "4px 6px", marginBottom: 4, cursor: "pointer",
                  background: "var(--bg)", borderRadius: 4, border: "1px solid var(--border)", fontSize: 10,
                }}>
                <div style={{ color: "var(--accent)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {r.title}
                </div>
                <div style={{ color: "var(--text-muted)", marginTop: 2, overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>
                  {r.snippet}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ borderTop: "1px solid var(--border)", padding: "8px 10px" }}>
        <div style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 4, letterSpacing: 0.5 }}>{t("semSearch")}</div>
        <div style={{ display: "flex", gap: 4 }}>
          <input
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleSearch()}
            placeholder="Rechercher..."
            style={{
              flex: 1, background: "var(--bg)", border: "1px solid var(--border)",
              color: "var(--text)", padding: "4px 6px", borderRadius: 4, fontSize: 11,
              outline: "none",
            }}
          />
          <button
            onClick={handleSearch}
            disabled={searching}
            style={{
              background: "var(--border)", border: "none", color: "var(--text)",
              padding: "4px 8px", borderRadius: 4, cursor: "pointer", fontSize: 11,
            }}
          >
            {searching ? "..." : "↵"}
          </button>
        </div>
        {searchResults.length > 0 && (
          <div style={{ marginTop: 6, maxHeight: 160, overflowY: "auto" }}>
            {searchResults.map((r, i) => (
              <div key={i} style={{
                padding: "4px 6px", marginBottom: 4,
                background: "var(--bg)", borderRadius: 4,
                border: "1px solid var(--border)", fontSize: 10,
              }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: r.role === "user" ? "var(--accent)" : "var(--green)" }}>{r.role}</span>
                  <span style={{ color: "var(--text-muted)" }}>{r.score.toFixed(2)}</span>
                </div>
                <div style={{ color: "var(--text-muted)", marginTop: 2, overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>
                  {r.content}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
