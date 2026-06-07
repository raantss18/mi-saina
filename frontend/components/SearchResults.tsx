"use client";
import { t } from "../lib/i18n";

interface SearchResult {
  title: string;
  url: string;
  snippet: string;
}

interface Props {
  results: SearchResult[];
  query: string;
  onClose: () => void;
}

export default function SearchResults({ results, query, onClose }: Props) {
  if (results.length === 0) return null;

  return (
    <div style={{
      background: "var(--surface)",
      border: "1px solid var(--border)",
      borderRadius: 6,
      padding: "10px 12px",
      marginTop: 8,
      fontSize: 12,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
        <span style={{ color: "var(--accent)", fontSize: 10, letterSpacing: 0.5 }}>
          {t("srResults")} {query}
        </span>
        <button onClick={onClose} style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: 12 }}>✕</button>
      </div>
      {results.map((r, i) => (
        <div key={i} style={{ marginBottom: 10 }}>
          <a
            href={r.url}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: "var(--accent)", textDecoration: "none", fontSize: 12 }}
          >
            {r.title}
          </a>
          <div style={{ color: "var(--text-muted)", fontSize: 10, marginTop: 1 }}>{r.url}</div>
          <div style={{ color: "var(--text)", fontSize: 11, marginTop: 3 }}>{r.snippet}</div>
        </div>
      ))}
    </div>
  );
}
