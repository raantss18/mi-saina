"use client";

import { useState } from "react";
import { highlight } from "../lib/highlight";

// Bloc de code : coloration syntaxique (sans dépendance) + bouton copier + label
// de langage. Utilisé par le rendu Markdown des réponses de l'assistant.
export default function CodeBlock({ code, lang }: { code: string; lang?: string }) {
  const [copied, setCopied] = useState(false);
  const html = highlight(code.replace(/\n$/, ""), lang);

  const copy = () => {
    navigator.clipboard?.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    }).catch(() => {});
  };

  return (
    <div className="ms-code">
      <div className="ms-code-bar">
        <span className="ms-code-lang">{lang || "code"}</span>
        <button className="ms-code-copy" onClick={copy} title="Copier">
          {copied ? "✓ copié" : "⎘ copier"}
        </button>
      </div>
      <pre>
        <code dangerouslySetInnerHTML={{ __html: html }} />
      </pre>
    </div>
  );
}
