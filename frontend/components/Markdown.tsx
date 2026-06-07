"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Rendu Markdown des réponses de l'assistant (titres, listes, gras, code,
// tableaux GFM, liens…). Styles dans .ms-md (globals.css), thème clair/sombre.
export default function Markdown({ content }: { content: string }) {
  return (
    <div className="ms-md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Les liens s'ouvrent dans un nouvel onglet, en sécurité.
          a: (props) => <a {...props} target="_blank" rel="noreferrer noopener" />,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
