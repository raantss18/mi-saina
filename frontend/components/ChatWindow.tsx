"use client";

import { useEffect, useRef, useState } from "react";
import Markdown from "./Markdown";
import { t } from "../lib/i18n";

export interface Message {
  role: "user" | "assistant" | "shell" | "plan";
  content: string;
  model?: string;
  streaming?: boolean;
  command?: string;
  // Pour les blocs shell streamés
  shellStreaming?: boolean;
  shellDone?: boolean;
  returncode?: number;
  error?: string;
  waitingInput?: boolean;
  attachments?: { type: string; name: string }[];
}

interface Props {
  messages: Message[];
  onShellInput?: (text: string) => void;
}

function ShellStreamBlock({
  msg,
  onInput,
}: {
  msg: Message;
  onInput?: (text: string) => void;
}) {
  const [inputVal, setInputVal] = useState("");

  const done = msg.shellDone;
  const rc = msg.returncode;
  const ok = done && rc === 0;
  const failed = done && rc !== 0 && rc !== undefined;
  const running = msg.shellStreaming;

  const borderColor = !done ? "var(--accent)" : ok ? "var(--green)" : "var(--red)";
  const headerBg = !done ? "rgba(127,184,154,0.08)" : ok ? "rgba(63,185,80,0.08)" : "rgba(248,81,73,0.08)";

  const submitInput = () => {
    if (inputVal.trim() !== "" || inputVal === "") {
      onInput?.(inputVal);
      setInputVal("");
    }
  };

  return (
    <div style={{
      maxWidth: "80%",
      background: "#070c11",
      border: `1px solid ${borderColor}44`,
      borderLeft: `3px solid ${borderColor}`,
      borderRadius: 6, overflow: "hidden", fontFamily: "monospace",
    }}>
      {/* Header */}
      <div style={{
        padding: "5px 12px", background: headerBg,
        borderBottom: `1px solid ${borderColor}22`,
        display: "flex", alignItems: "center", gap: 8,
      }}>
        {running && !done && (
          <span style={{ color: "var(--accent)", animation: "spin 1s linear infinite", display: "inline-block" }}>⟳</span>
        )}
        {done && ok && <span style={{ color: "var(--green)" }}>✓</span>}
        {done && failed && <span style={{ color: "var(--red)" }}>✗</span>}
        <code style={{ fontSize: 11, color: "var(--text-muted)", flex: 1 }}>$ {msg.command}</code>
        {done && (
          <span style={{ fontSize: 10, color: ok ? "var(--green)" : "var(--red)" }}>
            {ok ? t("success") : `rc=${rc}`}
          </span>
        )}
        {running && !done && (
          <span style={{ fontSize: 10, color: "var(--accent)" }}>{t("tpRunningShort")}</span>
        )}
      </div>

      {/* Résumé compact (la sortie complète est dans le panneau ▣ Terminal) */}
      <div style={{
        padding: "6px 12px", fontSize: 11, color: "var(--text-muted)",
        display: "flex", alignItems: "center", gap: 6,
      }}>
        {running && !done && <span>{t("chRunning")} <span style={{ opacity: 0.7 }}>{t("chDetails")}</span></span>}
        {ok && <span style={{ color: "var(--green)" }}>{t("chDone")}</span>}
        {failed && <span style={{ color: "var(--red)" }}>{t("chFailed")}</span>}
      </div>

      {/* Input interactif */}
      {(msg.waitingInput || (running && !done)) && (
        <div style={{
          borderTop: `1px solid ${borderColor}33`,
          padding: "6px 10px",
          display: "flex", gap: 6, alignItems: "center",
          background: "rgba(127,184,154,0.04)",
        }}>
          <span style={{ color: "var(--accent)", fontSize: 12 }}>›</span>
          <input
            value={inputVal}
            onChange={e => setInputVal(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); submitInput(); } }}
            placeholder={msg.waitingInput ? t("chReplyPrompt") : t("chEnterProcess")}
            autoFocus={msg.waitingInput}
            style={{
              flex: 1, background: "transparent", border: "none", outline: "none",
              color: "var(--text)", fontSize: 12, fontFamily: "monospace",
            }}
          />
          <button
            onClick={submitInput}
            style={{
              background: "var(--accent)", border: "none", color: "var(--accent-contrast)",
              padding: "3px 10px", borderRadius: 4, cursor: "pointer", fontSize: 11, fontWeight: 700,
            }}
          >
            ↵
          </button>
          <button
            onClick={() => onInput?.("")}
            title={t("chSendEmpty")}
            style={{ background: "var(--border)", border: "none", color: "var(--text-muted)", padding: "3px 8px", borderRadius: 4, cursor: "pointer", fontSize: 10 }}
          >
            Enter
          </button>
          <button
            onClick={() => onInput?.("y")}
            title={t("chYes")}
            style={{ background: "rgba(63,185,80,0.2)", border: "1px solid var(--green)", color: "var(--green)", padding: "3px 8px", borderRadius: 4, cursor: "pointer", fontSize: 10, fontWeight: 700 }}
          >
            Y
          </button>
          <button
            onClick={() => onInput?.("n")}
            title={t("chNo")}
            style={{ background: "rgba(248,81,73,0.15)", border: "1px solid var(--red)", color: "var(--red)", padding: "3px 8px", borderRadius: 4, cursor: "pointer", fontSize: 10, fontWeight: 700 }}
          >
            N
          </button>
        </div>
      )}
    </div>
  );
}

export default function ChatWindow({ messages, onShellInput }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px", display: "flex", flexDirection: "column", gap: 12 }}>
      {messages.length === 0 && (
        <div style={{ color: "var(--text-muted)", fontSize: 13, textAlign: "center", marginTop: 60 }}>
          <div style={{ fontSize: 24, marginBottom: 8 }}>◈</div>
          <div>{t("chReady")}</div>
          <div style={{ fontSize: 11, marginTop: 4, color: "var(--text-muted)" }}>
            {t("chReadyHint")}
          </div>
        </div>
      )}

      {messages.map((msg, i) => {
        if (msg.role === "shell") {
          return (
            <ShellStreamBlock
              key={i}
              msg={msg}
              onInput={onShellInput}
            />
          );
        }

        if (msg.role === "plan") {
          return (
            <div key={i} style={{
              alignSelf: "center", maxWidth: "92%", width: "100%",
              background: "rgba(127,184,154,0.06)", border: "1px dashed var(--accent)",
              borderRadius: 8, padding: "8px 12px", margin: "2px 0",
              fontSize: 12, color: "var(--text-muted)", whiteSpace: "pre-wrap",
              fontFamily: "var(--font-mono, monospace)",
            }}>
              {msg.content}
            </div>
          );
        }

        return (
          <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: msg.role === "user" ? "flex-end" : "flex-start" }}>
            {/* Attachements */}
            {msg.attachments && msg.attachments.length > 0 && (
              <div style={{ display: "flex", gap: 4, marginBottom: 4, justifyContent: msg.role === "user" ? "flex-end" : "flex-start" }}>
                {msg.attachments.map((a, j) => (
                  <span key={j} style={{ fontSize: 10, background: "var(--border)", padding: "2px 6px", borderRadius: 4, color: "var(--text-muted)" }}>
                    {a.type === "image" ? "🖼" : "📄"} {a.name}
                  </span>
                ))}
              </div>
            )}
            <div style={{
              maxWidth: "80%", padding: "10px 14px",
              borderRadius: msg.role === "user" ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
              background: msg.role === "user" ? "rgba(127,184,154,0.12)" : "var(--surface)",
              border: msg.role === "user" ? "1px solid var(--accent)" : "1px solid var(--border)",
              fontSize: 13, lineHeight: 1.6, wordBreak: "break-word",
              // L'utilisateur reste en texte brut (préserve les retours) ; l'assistant en Markdown.
              ...(msg.role === "user" ? { whiteSpace: "pre-wrap" as const } : {}),
            }}>
              {msg.role === "assistant"
                ? <Markdown content={msg.content} />
                : msg.content}
              {msg.streaming && i === messages.length - 1 && (
                <span style={{ color: "var(--accent)", animation: "blink 1s step-end infinite" }}>▋</span>
              )}
            </div>
            {msg.model && (
              <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 3, padding: "0 4px" }}>{msg.model}</div>
            )}
          </div>
        );
      })}

      <div ref={bottomRef} />
      <style>{`
        @keyframes blink { 50% { opacity: 0; } }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
