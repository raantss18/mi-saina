"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ChatWindow from "../components/ChatWindow";
import ConfigPanel from "../components/ConfigPanel";
import MemoryPanel from "../components/MemoryPanel";
import ModelPanel from "../components/ModelPanel";
import SearchResults from "../components/SearchResults";

interface Message {
  role: "user" | "assistant" | "shell" | "plan";
  content: string;
  shellStreaming?: boolean;
  shellDone?: boolean;
  waitingInput?: boolean;
  error?: string;
  model?: string;
  streaming?: boolean;
  command?: string;
  status?: string;
  returncode?: number;
  attachments?: Attachment[];
}

interface Attachment {
  type: "text" | "image";
  name: string;
  content?: string;
  data?: string;
}

interface SearchResult { title: string; url: string; snippet: string; }
interface Skill { name: string; trigger: string; description: string; icon: string; prompt: string; }

type Panel = "models" | "config" | null;

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [activeModel, setActiveModel] = useState<string>("magistral:small");
  const [connected, setConnected] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [sudoModal, setSudoModal] = useState(false);
  const [sudoPassword, setSudoPassword] = useState("");
  const [pendingCommand, setPendingCommand] = useState("");
  const [confirmCommand, setConfirmCommand] = useState<string | null>(null);
  const [panel, setPanel] = useState<Panel>(null);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [skillMenu, setSkillMenu] = useState(false);
  const [skillFilter, setSkillFilter] = useState("");
  const [lastUserMsg, setLastUserMsg] = useState("");
  const [memoryRefresh, setMemoryRefresh] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // Charger les skills au démarrage
  useEffect(() => {
    fetch("http://localhost:8000/config/skills")
      .then(r => r.json()).then(setSkills).catch(() => {});
  }, []);

  const connect = useCallback(() => {
    const ws = new WebSocket("ws://localhost:8000/chat/ws");
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => { setConnected(false); setStreaming(false); setTimeout(connect, 3000); };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "session_id") { setSessionId(data.session_id); return; }

      if (data.type === "token") {
        setMessages(prev => {
          const last = prev[prev.length - 1];
          if (last?.role === "assistant" && last.streaming)
            return [...prev.slice(0, -1), { ...last, content: last.content + data.content }];
          return [...prev, { role: "assistant", content: data.content, streaming: true }];
        });
        return;
      }

      if (data.type === "done") {
        setActiveModel(data.model || "");
        setStreaming(false);
        setMessages(prev => {
          const last = prev[prev.length - 1];
          if (last?.role === "assistant")
            return [...prev.slice(0, -1), { ...last, streaming: false, model: data.model }];
          return prev;
        });
        return;
      }

      if (data.type === "stopped") {
        setStreaming(false);
        setMessages(prev => {
          const last = prev[prev.length - 1];
          if (last?.role === "assistant")
            return [...prev.slice(0, -1), { ...last, streaming: false, content: last.content + " ⏹" }];
          return prev;
        });
        return;
      }

      // Ancien format (fallback)
      if (data.type === "shell_result") {
        setMessages(prev => [...prev, {
          role: "shell", content: data.output || "",
          command: data.command, shellDone: true,
          returncode: data.returncode ?? (data.status === "ok" ? 0 : 1),
        }]);
        return;
      }

      // Nouveau : début de commande streamée
      if (data.type === "shell_start") {
        setMessages(prev => [...prev, {
          role: "shell", command: data.command,
          content: "", shellStreaming: true, shellDone: false,
        }]);
        return;
      }

      // Chunks en temps réel
      if (data.type === "shell_chunk") {
        setMessages(prev => {
          const idx = [...prev].reverse().findIndex(m => m.role === "shell" && m.command === data.command && !m.shellDone);
          if (idx === -1) return prev;
          const realIdx = prev.length - 1 - idx;
          const updated = [...prev];
          updated[realIdx] = { ...updated[realIdx], content: updated[realIdx].content + data.text };
          return updated;
        });
        return;
      }

      // Processus attend une entrée
      if (data.type === "shell_waiting") {
        setMessages(prev => {
          const idx = [...prev].reverse().findIndex(m => m.role === "shell" && m.command === data.command && !m.shellDone);
          if (idx === -1) return prev;
          const realIdx = prev.length - 1 - idx;
          const updated = [...prev];
          updated[realIdx] = { ...updated[realIdx], waitingInput: true };
          return updated;
        });
        return;
      }

      // Commande terminée
      if (data.type === "shell_done") {
        setMessages(prev => {
          const idx = [...prev].reverse().findIndex(m => m.role === "shell" && m.command === data.command && !m.shellDone);
          if (idx === -1) return [...prev, { role: "shell", command: data.command, content: data.error || "", shellDone: true, shellStreaming: false, returncode: data.returncode }];
          const realIdx = prev.length - 1 - idx;
          const updated = [...prev];
          updated[realIdx] = { ...updated[realIdx], shellDone: true, shellStreaming: false, returncode: data.returncode, waitingInput: false, error: data.error };
          return updated;
        });
        setStreaming(false);
        return;
      }

      if (data.type === "needs_sudo") {
        setPendingCommand(data.command);
        setSudoModal(true);
        return;
      }

      // Plan généré (tâche découpée en sous-tâches)
      if (data.type === "plan") {
        const list = (data.subtasks as string[]).map((s, i) => `${i + 1}. ${s}`).join("\n");
        setMessages(prev => [...prev, { role: "plan", content: `🧭 Plan (${data.subtasks.length} étapes)\n${list}` }]);
        return;
      }

      // Début d'une sous-tâche
      if (data.type === "subtask_start") {
        setMessages(prev => [...prev, { role: "plan", content: `▶ Étape ${data.index}/${data.total} — ${data.text}` }]);
        return;
      }

      // Demande de validation avant exécution d'une commande
      if (data.type === "confirm_exec") {
        setConfirmCommand(data.command);
        return;
      }

      // L'utilisateur a refusé une commande → trace dans le fil
      if (data.type === "exec_declined") {
        setMessages(prev => [...prev, {
          role: "shell", command: data.command,
          content: "⏭ Commande refusée — non exécutée.",
          shellDone: true, shellStreaming: false, returncode: -1,
        }]);
        return;
      }

      if (data.type === "session_title") {
        // Rafraîchir le panel sessions pour afficher le nouveau titre
        setMemoryRefresh(n => n + 1);
        return;
      }
    };
  }, []);

  useEffect(() => { connect(); return () => wsRef.current?.close(); }, [connect]);

  const sendShellInput = (text: string) => {
    wsRef.current?.send(JSON.stringify({ type: "shell_stdin", text }));
    // Réinitialiser l'indicateur waitingInput sur le bloc courant
    setMessages(prev => prev.map(m =>
      m.role === "shell" && m.waitingInput ? { ...m, waitingInput: false } : m
    ));
  };

  // Rafraîchir les skills quand le panel config se ferme
  useEffect(() => {
    if (panel !== "config") {
      fetch("http://localhost:8000/config/skills")
        .then(r => r.json()).then(setSkills).catch(() => {});
    }
  }, [panel]);

  const sendMessage = (overrideText?: string) => {
    const text = (overrideText ?? input).trim();
    if (!text || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    const searchMatch = text.match(/\[SEARCH:\s*(.+?)\]/i);
    if (searchMatch) {
      fetch("http://localhost:8000/search/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: searchMatch[1] }) })
        .then(r => r.json()).then(d => { setSearchResults(d); setSearchQuery(searchMatch[1]); }).catch(() => {});
    }

    setLastUserMsg(text);
    setMessages(prev => [...prev, { role: "user", content: text, attachments: attachments.length ? [...attachments] : undefined }]);
    wsRef.current.send(JSON.stringify({
      message: text,
      task_type: "reason",
      session_id: sessionId,
      attachments: attachments.length ? attachments : undefined,
    }));
    setInput("");
    setAttachments([]);
    setStreaming(true);
    setSkillMenu(false);
  };

  const stopGeneration = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "stop" }));
    }
  };

  const rerunLast = () => {
    if (lastUserMsg) sendMessage(lastUserMsg);
  };

  const clearChat = () => { setMessages([]); setLastUserMsg(""); };

  const copyLastResponse = () => {
    const last = [...messages].reverse().find(m => m.role === "assistant");
    if (last) navigator.clipboard.writeText(last.content);
  };

  const respondConfirm = (approved: boolean) => {
    wsRef.current?.send(JSON.stringify({ type: "exec_response", approved }));
    setConfirmCommand(null);
  };

  const handleSudoSubmit = () => {
    setSudoModal(false);
    wsRef.current?.send(JSON.stringify({ type: "sudo_response", password: sudoPassword }));
    setSudoPassword("");
    setPendingCommand("");
  };

  // Gestion pièces jointes
  const handleFileAttach = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const newAttachments: Attachment[] = [];

    for (const file of files) {
      const isImage = file.type.startsWith("image/");
      if (isImage) {
        const data = await new Promise<string>((res) => {
          const reader = new FileReader();
          reader.onload = () => res((reader.result as string).split(",")[1]);
          reader.readAsDataURL(file);
        });
        newAttachments.push({ type: "image", name: file.name, data });
      } else {
        const content = await file.text();
        newAttachments.push({ type: "text", name: file.name, content });
      }
    }
    setAttachments(prev => [...prev, ...newAttachments]);
    e.target.value = "";
  };

  // Skill autocomplete
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setInput(val);
    if (val.startsWith("/")) {
      setSkillFilter(val.slice(1).toLowerCase());
      setSkillMenu(true);
    } else {
      setSkillMenu(false);
    }
  };

  const applySkill = (skill: Skill) => {
    setInput(skill.prompt);
    setSkillMenu(false);
    inputRef.current?.focus();
  };

  const filteredSkills = skills.filter(s =>
    skillFilter === "" || s.trigger.toLowerCase().includes(skillFilter) || s.name.toLowerCase().includes(skillFilter)
  );

  const btnStyle = (active = false, danger = false): React.CSSProperties => ({
    background: active ? "var(--accent)" : danger ? "rgba(248,81,73,0.15)" : "var(--border)",
    border: danger ? "1px solid var(--red)" : "none",
    color: active ? "#000" : danger ? "var(--red)" : "var(--text-muted)",
    padding: "4px 10px", borderRadius: 4, cursor: "pointer", fontSize: 11,
    fontWeight: active ? 700 : 400, whiteSpace: "nowrap" as const,
  });

  return (
    <div style={{ display: "flex", height: "100vh", background: "var(--bg)" }}>
      <MemoryPanel
        activeSessionId={sessionId}
        onSelectSession={(id) => { setSessionId(id); setMessages([]); }}
        onNewSession={(id) => { setSessionId(id); setMessages([]); }}
        refreshKey={memoryRefresh}
      />

      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        {/* Header */}
        <div style={{
          padding: "6px 16px", borderBottom: "1px solid var(--border)",
          display: "flex", alignItems: "center", gap: 8,
          background: "var(--surface)", flexShrink: 0,
        }}>
          <span style={{ color: "var(--text-muted)", fontSize: 10 }}>modèle:</span>
          <span style={{ background: "var(--border)", padding: "2px 8px", borderRadius: 12, fontSize: 11, color: "var(--accent)" }}>
            {activeModel}
          </span>

          {/* Contrôles principaux */}
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6 }}>
            {/* Re-run */}
            <button onClick={rerunLast} disabled={!lastUserMsg || streaming} title="Relancer le dernier prompt (↺)" style={btnStyle()}>
              ↺
            </button>
            {/* Copy */}
            <button onClick={copyLastResponse} title="Copier la dernière réponse" style={btnStyle()}>
              ⎘
            </button>
            {/* Clear */}
            <button onClick={clearChat} title="Effacer la conversation" style={btnStyle(false, true)}>
              🗑
            </button>
            <div style={{ width: 1, height: 16, background: "var(--border)", margin: "0 4px" }} />
            <button onClick={() => setPanel(p => p === "config" ? null : "config")} style={btnStyle(panel === "config")}>
              ⚙ Config
            </button>
            <button onClick={() => setPanel(p => p === "models" ? null : "models")} style={btnStyle(panel === "models")}>
              ⬡ Modèles
            </button>
            <div style={{ display: "flex", alignItems: "center", gap: 5, marginLeft: 4 }}>
              <div style={{ width: 6, height: 6, borderRadius: "50%", background: connected ? "var(--green)" : "var(--red)" }} />
              <span style={{ fontSize: 10, color: "var(--text-muted)" }}>{connected ? "connecté" : "hors ligne"}</span>
            </div>
          </div>
        </div>

        {/* Panels */}
        {panel && (
          <div style={{ padding: "14px 20px", flexShrink: 0, borderBottom: "1px solid var(--border)", background: "var(--surface)", overflowY: "auto", maxHeight: "50vh" }}>
            {panel === "models" && <ModelPanel onModelChange={(m) => { setActiveModel(m); setPanel(null); }} />}
            {panel === "config" && <ConfigPanel />}
          </div>
        )}

        {/* Chat */}
        <ChatWindow messages={messages} onShellInput={sendShellInput} />

        {/* Search results */}
        {searchResults.length > 0 && (
          <div style={{ padding: "0 20px", flexShrink: 0 }}>
            <SearchResults results={searchResults} query={searchQuery} onClose={() => setSearchResults([])} />
          </div>
        )}

        {/* Pièces jointes en attente */}
        {attachments.length > 0 && (
          <div style={{ padding: "4px 20px", display: "flex", gap: 6, flexWrap: "wrap", flexShrink: 0, borderTop: "1px solid var(--border)" }}>
            {attachments.map((a, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 4, background: "var(--border)", borderRadius: 4, padding: "3px 8px", fontSize: 11 }}>
                <span>{a.type === "image" ? "🖼" : "📄"}</span>
                <span style={{ color: "var(--text)" }}>{a.name}</span>
                <button onClick={() => setAttachments(prev => prev.filter((_, j) => j !== i))}
                  style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: 12, padding: 0 }}>
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Skill autocomplete */}
        {skillMenu && filteredSkills.length > 0 && (
          <div style={{
            position: "absolute", bottom: 80, left: 260, right: 20,
            background: "var(--surface)", border: "1px solid var(--accent)",
            borderRadius: 8, zIndex: 50, overflow: "hidden", maxHeight: 200, overflowY: "auto",
          }}>
            {filteredSkills.map(s => (
              <div key={s.name} onClick={() => applySkill(s)}
                style={{ padding: "8px 12px", cursor: "pointer", display: "flex", alignItems: "center", gap: 10, borderBottom: "1px solid var(--border)" }}
                onMouseEnter={e => (e.currentTarget.style.background = "var(--border)")}
                onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
              >
                <span style={{ fontSize: 16 }}>{s.icon}</span>
                <div>
                  <code style={{ fontSize: 11, color: "var(--accent)" }}>{s.trigger}</code>
                  <span style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: 8 }}>{s.description}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Zone de saisie */}
        <div style={{
          padding: "10px 16px",
          borderTop: "1px solid var(--border)",
          background: "var(--surface)",
          flexShrink: 0,
        }}>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            {/* Attachment */}
            <button onClick={() => fileRef.current?.click()} title="Joindre un fichier ou une image (📎)"
              style={{ ...btnStyle(), padding: "6px 8px" }}>
              📎
            </button>
            <input ref={fileRef} type="file" multiple accept="*/*" style={{ display: "none" }} onChange={handleFileAttach} />

            {/* Input */}
            <div style={{ flex: 1, display: "flex", alignItems: "center", background: "var(--bg)", borderRadius: 6, border: "1px solid var(--border)", padding: "0 10px" }}>
              <span style={{ color: "var(--accent)", fontSize: 14, fontWeight: 700, marginRight: 6 }}>›</span>
              <input
                ref={inputRef}
                value={input}
                onChange={handleInputChange}
                onKeyDown={e => {
                  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
                  if (e.key === "Escape") { setSkillMenu(false); }
                }}
                placeholder="Message... ou /skill pour les raccourcis"
                disabled={!connected}
                style={{
                  flex: 1, background: "transparent", border: "none", outline: "none",
                  color: "var(--text)", fontSize: 13, fontFamily: "inherit", padding: "8px 0",
                }}
              />
            </div>

            {/* Stop / Send */}
            {streaming ? (
              <button onClick={stopGeneration} title="Arrêter la génération (⏹)"
                style={{ background: "var(--red)", border: "none", color: "#fff", padding: "8px 14px", borderRadius: 6, cursor: "pointer", fontSize: 13, fontWeight: 700 }}>
                ⏹
              </button>
            ) : (
              <button onClick={() => sendMessage()} disabled={!connected || (!input.trim() && attachments.length === 0)}
                style={{
                  background: connected && (input.trim() || attachments.length) ? "var(--accent)" : "var(--border)",
                  border: "none",
                  color: connected && (input.trim() || attachments.length) ? "#000" : "var(--text-muted)",
                  padding: "8px 16px", borderRadius: 6, cursor: "pointer",
                  fontSize: 13, fontWeight: 700, transition: "background 0.15s",
                }}>
                ↵
              </button>
            )}
          </div>

          {/* Skills rapides (barre compacte) */}
          {skills.length > 0 && !streaming && (
            <div style={{ display: "flex", gap: 4, marginTop: 6, flexWrap: "wrap" }}>
              {skills.slice(0, 8).map(s => (
                <button key={s.name} onClick={() => applySkill(s)} title={s.description}
                  style={{
                    background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text-muted)",
                    padding: "2px 8px", borderRadius: 12, cursor: "pointer", fontSize: 10,
                    display: "flex", alignItems: "center", gap: 3,
                  }}>
                  <span>{s.icon}</span>
                  <code>{s.trigger}</code>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Sudo modal */}
      {sudoModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 }}>
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, padding: 24, minWidth: 340 }}>
            <div style={{ color: "var(--yellow)", marginBottom: 8, fontSize: 13, fontWeight: 700 }}>🔐 Sudo requis</div>
            <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 16 }}>
              <code style={{ color: "var(--text)" }}>$ {pendingCommand}</code>
            </div>
            <input type="password" value={sudoPassword} onChange={e => setSudoPassword(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleSudoSubmit()}
              placeholder="Mot de passe sudo..." autoFocus
              style={{ width: "100%", background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)", padding: 8, borderRadius: 4, fontSize: 13, outline: "none", fontFamily: "inherit" }}
            />
            <div style={{ display: "flex", gap: 8, marginTop: 12, justifyContent: "flex-end" }}>
              <button onClick={() => { setSudoModal(false); setSudoPassword(""); }}
                style={{ background: "var(--border)", border: "none", color: "var(--text)", padding: "6px 14px", borderRadius: 4, cursor: "pointer", fontSize: 12 }}>
                Annuler
              </button>
              <button onClick={handleSudoSubmit}
                style={{ background: "var(--accent)", border: "none", color: "#000", padding: "6px 14px", borderRadius: 4, cursor: "pointer", fontSize: 12, fontWeight: 700 }}>
                Confirmer
              </button>
            </div>
          </div>
        </div>
      )}

      {confirmCommand !== null && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 }}>
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, padding: 24, minWidth: 380, maxWidth: 640 }}>
            <div style={{ color: "var(--accent)", marginBottom: 8, fontSize: 13, fontWeight: 700 }}>▶ Exécuter cette commande ?</div>
            <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 16, background: "var(--bg)", border: "1px solid var(--border)", borderRadius: 4, padding: "8px 10px", whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
              <code style={{ color: "var(--text)" }}>$ {confirmCommand}</code>
            </div>
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button onClick={() => respondConfirm(false)} autoFocus
                style={{ background: "var(--border)", border: "none", color: "var(--text)", padding: "6px 14px", borderRadius: 4, cursor: "pointer", fontSize: 12 }}>
                Refuser
              </button>
              <button onClick={() => respondConfirm(true)}
                style={{ background: "var(--accent)", border: "none", color: "#000", padding: "6px 14px", borderRadius: 4, cursor: "pointer", fontSize: 12, fontWeight: 700 }}>
                Exécuter
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
