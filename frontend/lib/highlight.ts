// Coloration syntaxique SANS dépendance (zéro ajout au bundle — dans l'esprit du
// projet, qui a retiré torch/sentence-transformers pour rester léger).
//
// Un scanner à passe unique, paramétré par langage, couvrant ce que les modèles
// locaux produisent le plus : shell, python, js/ts, json — plus un repli
// générique (chaînes / nombres / commentaires) pour tout le reste. Le rendu
// passe par des <span class="tok-*"> dont les couleurs sont des variables CSS
// (thème clair/sombre géré dans globals.css). Tout est échappé → pas d'injection.

export function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

type Grammar = {
  line: string[];                 // débuts de commentaire de ligne
  block?: [string, string];       // commentaire de bloc [ouvre, ferme]
  quotes: string[];               // délimiteurs de chaîne
  keywords: Set<string>;
  literals?: Set<string>;         // true/false/null/None…
  vars?: boolean;                 // surligner $VAR / ${...} (shell)
};

const KW = (s: string) => new Set(s.split(/\s+/).filter(Boolean));

const SHELL: Grammar = {
  line: ["#"],
  quotes: ['"', "'", "`"],
  keywords: KW(`if then elif else fi for while until do done case esac in function
    select return break continue local export source alias set unset shift`),
  vars: true,
};

const PYTHON: Grammar = {
  line: ["#"],
  quotes: ['"', "'"],
  keywords: KW(`def class return if elif else for while try except finally with as
    import from lambda pass break continue yield global nonlocal assert del raise
    in is not and or async await match case`),
  literals: KW("None True False self"),
};

const JS: Grammar = {
  line: ["//"],
  block: ["/*", "*/"],
  quotes: ['"', "'", "`"],
  keywords: KW(`const let var function return if else for while do switch case break
    continue new class extends super this typeof instanceof in of try catch finally
    throw async await yield import from export default void delete static get set`),
  literals: KW("null undefined true false NaN Infinity"),
};

const JSON_G: Grammar = {
  line: [],
  quotes: ['"'],
  keywords: new Set<string>(),
  literals: KW("true false null"),
};

const GENERIC: Grammar = {
  line: ["#", "//"],
  block: ["/*", "*/"],
  quotes: ['"', "'", "`"],
  keywords: new Set<string>(),
};

const ALIASES: Record<string, Grammar> = {
  sh: SHELL, shell: SHELL, bash: SHELL, zsh: SHELL, console: SHELL,
  py: PYTHON, python: PYTHON,
  js: JS, jsx: JS, javascript: JS, ts: JS, tsx: JS, typescript: JS,
  json: JSON_G, jsonc: JSON_G,
};

export function grammarFor(lang?: string): Grammar {
  return ALIASES[(lang || "").toLowerCase()] || GENERIC;
}

const isWordStart = (c: string) => /[A-Za-z_$]/.test(c);
const isWord = (c: string) => /[A-Za-z0-9_$]/.test(c);
const isDigit = (c: string) => c >= "0" && c <= "9";

function span(cls: string, text: string): string {
  return `<span class="tok-${cls}">${escapeHtml(text)}</span>`;
}

/** Retourne du HTML échappé et coloré pour `code` selon `lang`. */
export function highlight(code: string, lang?: string): string {
  const g = grammarFor(lang);
  let out = "";
  let i = 0;
  const n = code.length;
  const startsWith = (s: string) => code.startsWith(s, i);

  while (i < n) {
    const c = code[i];

    // Commentaire de bloc
    if (g.block && startsWith(g.block[0])) {
      const end = code.indexOf(g.block[1], i + g.block[0].length);
      const stop = end === -1 ? n : end + g.block[1].length;
      out += span("com", code.slice(i, stop));
      i = stop;
      continue;
    }
    // Commentaire de ligne
    const lc = g.line.find((m) => startsWith(m));
    if (lc) {
      const end = code.indexOf("\n", i);
      const stop = end === -1 ? n : end;
      out += span("com", code.slice(i, stop));
      i = stop;
      continue;
    }
    // Chaîne (avec échappements)
    if (g.quotes.includes(c)) {
      let j = i + 1;
      while (j < n) {
        if (code[j] === "\\") { j += 2; continue; }
        if (code[j] === c) { j++; break; }
        j++;
      }
      out += span("str", code.slice(i, Math.min(j, n)));
      i = Math.min(j, n);
      continue;
    }
    // Variable shell $VAR / ${...}
    if (g.vars && c === "$" && i + 1 < n) {
      let j = i + 1;
      if (code[j] === "{") {
        const end = code.indexOf("}", j);
        j = end === -1 ? n : end + 1;
      } else {
        while (j < n && isWord(code[j])) j++;
      }
      out += span("var", code.slice(i, j));
      i = j;
      continue;
    }
    // Nombre
    if (isDigit(c) || (c === "." && isDigit(code[i + 1] || ""))) {
      let j = i;
      while (j < n && /[0-9a-fA-FxX._]/.test(code[j])) j++;
      out += span("num", code.slice(i, j));
      i = j;
      continue;
    }
    // Mot (mot-clé / littéral / fonction / identifiant)
    if (isWordStart(c)) {
      let j = i + 1;
      while (j < n && isWord(code[j])) j++;
      const word = code.slice(i, j);
      let k = j;
      while (k < n && (code[k] === " " || code[k] === "\t")) k++;
      const isCall = code[k] === "(";
      if (g.keywords.has(word)) out += span("kw", word);
      else if (g.literals?.has(word)) out += span("lit", word);
      else if (isCall) out += span("fn", word);
      else out += escapeHtml(word);
      i = j;
      continue;
    }
    // Ponctuation / autre caractère
    out += escapeHtml(c);
    i++;
  }
  return out;
}
