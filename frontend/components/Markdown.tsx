"use client";

import type { ComponentPropsWithoutRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import CodeBlock from "./CodeBlock";

// Rendu Markdown des réponses de l'assistant (titres, listes, gras, code coloré,
// tableaux GFM, liens…). Styles dans .ms-md (globals.css), thème clair/sombre.

// Récupère le texte brut d'un nœud de code (les enfants peuvent être imbriqués).
function nodeText(children: React.ReactNode): string {
  if (children == null) return "";
  if (typeof children === "string") return children;
  if (Array.isArray(children)) return children.map(nodeText).join("");
  if (typeof children === "object" && "props" in (children as never)) {
    return nodeText((children as { props: { children?: React.ReactNode } }).props.children);
  }
  return String(children);
}

export default function Markdown({ content }: { content: string }) {
  return (
    <div className="ms-md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Les liens s'ouvrent dans un nouvel onglet, en sécurité.
          a: (props) => <a {...props} target="_blank" rel="noreferrer noopener" />,
          // Code : inline reste tel quel ; les blocs (```lang) passent par CodeBlock
          // (coloration syntaxique + bouton copier). En react-markdown v9, un bloc
          // fencé porte une className "language-xxx".
          code(props: ComponentPropsWithoutRef<"code"> & { node?: unknown }) {
            const { className, children } = props;
            const match = /language-(\w+)/.exec(className || "");
            const text = nodeText(children);
            // Bloc si un langage est déclaré OU si le contenu tient sur plusieurs
            // lignes (fence sans langage) ; sinon code inline.
            if (match || text.includes("\n")) {
              return <CodeBlock code={text} lang={match?.[1]} />;
            }
            return <code className={className}>{children}</code>;
          },
          // On laisse CodeBlock fournir son propre <pre> : ici on évite le double
          // encadrement en rendant le contenu tel quel.
          pre: (props) => <>{props.children}</>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
