"use client";

export interface Artifact {
  id: string;
  title: string;
  lang: string;
  content: string;
}

const EXT: Record<string, string> = {
  python: "py", py: "py", javascript: "js", js: "js", typescript: "ts", ts: "ts",
  tsx: "tsx", jsx: "jsx", bash: "sh", sh: "sh", shell: "sh", json: "json",
  html: "html", css: "css", c: "c", cpp: "cpp", java: "java", go: "go", rust: "rs",
  rs: "rs", sql: "sql", yaml: "yaml", yml: "yml", markdown: "md", md: "md", tex: "tex",
};

// Extrait les blocs de code ```lang\n…``` d'un texte → artefacts (titre = lang + 1re ligne).
export function extractArtifacts(text: string): Omit<Artifact, "id">[] {
  const out: Omit<Artifact, "id">[] = [];
  const re = /```([\w+-]*)\n([\s\S]*?)```/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    const lang = (m[1] || "txt").toLowerCase();
    const content = m[2].replace(/\s+$/, "");
    if (content.trim().length < 8) continue;   // ignore les fragments triviaux
    const firstLine = content.split("\n")[0].slice(0, 40).trim();
    out.push({ title: firstLine || lang, lang, content });
  }
  return out;
}

interface Props {
  artifacts: Artifact[];
  onClose: () => void;
  onRemove: (id: string) => void;
  onClear: () => void;
  labels: { title: string; empty: string; copy: string; download: string; remove: string; clear: string };
}

export default function ArtifactsPanel({ artifacts, onClose, onRemove, onClear, labels }: Props) {
  const download = (a: Artifact) => {
    const ext = EXT[a.lang] || "txt";
    const blob = new Blob([a.content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${(a.title || "artefact").replace(/[^\w.-]+/g, "_").slice(0, 32)}.${ext}`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div style={{
      width: "38%", minWidth: 300, maxWidth: 560, display: "flex", flexDirection: "column",
      borderLeft: "1px solid var(--border)", background: "var(--surface)",
    }}>
      <div style={{
        padding: "6px 12px", borderBottom: "1px solid var(--border)",
        display: "flex", alignItems: "center", gap: 8, flexShrink: 0,
      }}>
        <span style={{ fontSize: 11, color: "var(--text-muted)", letterSpacing: 0.5, flex: 1 }}>
          ❖ {labels.title} ({artifacts.length})
        </span>
        {artifacts.length > 0 && (
          <button onClick={onClear} title={labels.clear}
            style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: 11 }}>
            {labels.clear}
          </button>
        )}
        <button onClick={onClose} title="✕"
          style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: 14 }}>
          ✕
        </button>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: 10, display: "flex", flexDirection: "column", gap: 10 }}>
        {artifacts.length === 0 && (
          <div className="ms-empty"><span className="ms-empty-icon">❖</span><div>{labels.empty}</div></div>
        )}
        {artifacts.map(a => (
          <div key={a.id} className="ms-card" style={{ overflow: "hidden" }}>
            <div style={{
              display: "flex", alignItems: "center", gap: 6, padding: "5px 8px",
              background: "var(--surface-2)", borderBottom: "1px solid var(--border)",
            }}>
              <span style={{ fontSize: 9, color: "var(--accent)", textTransform: "uppercase" }}>{a.lang}</span>
              <span style={{ flex: 1, fontSize: 11, color: "var(--text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{a.title}</span>
              <button onClick={() => navigator.clipboard.writeText(a.content)} title={labels.copy}
                style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: 12 }}>⎘</button>
              <button onClick={() => download(a)} title={labels.download}
                style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: 12 }}>⬇</button>
              <button onClick={() => onRemove(a.id)} title={labels.remove}
                style={{ background: "none", border: "none", color: "var(--red)", cursor: "pointer", fontSize: 12 }}>✕</button>
            </div>
            <pre style={{
              margin: 0, padding: "8px 10px", maxHeight: 240, overflow: "auto", fontSize: 11,
              fontFamily: "var(--font-mono)", color: "var(--text)", whiteSpace: "pre-wrap", wordBreak: "break-word",
            }}>{a.content}</pre>
          </div>
        ))}
      </div>
    </div>
  );
}
