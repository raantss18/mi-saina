"use client";

interface ShellEntry {
  command: string;
  output: string;
  status: string;
  timestamp: string;
}

interface Props {
  entries: ShellEntry[];
}

export default function ShellOutput({ entries }: Props) {
  if (entries.length === 0) return null;

  return (
    <div style={{
      background: "var(--bg)",
      border: "1px solid var(--border)",
      borderRadius: 6,
      padding: "8px 12px",
      marginTop: 8,
      fontSize: 12,
    }}>
      <div style={{ color: "var(--text-muted)", fontSize: 10, marginBottom: 6, letterSpacing: 0.5 }}>SHELL</div>
      {entries.slice(-5).map((e, i) => (
        <div key={i} style={{ marginBottom: 8 }}>
          <div style={{ color: "var(--yellow)" }}>$ {e.command}</div>
          <pre style={{
            color: e.status === "ok" ? "var(--text)" : "var(--red)",
            margin: "2px 0 0 12px",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            fontSize: 11,
          }}>
            {e.output}
          </pre>
        </div>
      ))}
    </div>
  );
}
