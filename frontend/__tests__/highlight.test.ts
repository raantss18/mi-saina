import { describe, it, expect } from "vitest";
import { highlight, escapeHtml, grammarFor } from "../lib/highlight";

describe("escapeHtml", () => {
  it("échappe les caractères HTML dangereux", () => {
    expect(escapeHtml('<script>&"')).toBe("&lt;script&gt;&amp;\"");
  });
});

describe("grammarFor", () => {
  it("mappe les alias de langage", () => {
    expect(grammarFor("py")).toBe(grammarFor("python"));
    expect(grammarFor("ts")).toBe(grammarFor("js"));
    expect(grammarFor("bash")).toBe(grammarFor("sh"));
  });
  it("retombe sur la grammaire générique pour un langage inconnu", () => {
    expect(grammarFor("brainfuck")).toBe(grammarFor(""));
  });
});

describe("highlight", () => {
  it("colore les mots-clés shell", () => {
    const html = highlight("if true; then echo hi; fi", "bash");
    expect(html).toContain('<span class="tok-kw">if</span>');
    expect(html).toContain('<span class="tok-kw">then</span>');
  });

  it("colore les chaînes et les commentaires", () => {
    const html = highlight('echo "salut" # note', "bash");
    expect(html).toContain('<span class="tok-str">"salut"</span>');
    expect(html).toContain('<span class="tok-com"># note</span>');
  });

  it("colore les variables shell", () => {
    const html = highlight("echo $HOME ${PATH}", "sh");
    expect(html).toContain('<span class="tok-var">$HOME</span>');
    expect(html).toContain('<span class="tok-var">${PATH}</span>');
  });

  it("colore def python et les appels de fonction", () => {
    const html = highlight("def foo():\n    bar()", "python");
    expect(html).toContain('<span class="tok-kw">def</span>');
    expect(html).toContain('<span class="tok-fn">foo</span>');
    expect(html).toContain('<span class="tok-fn">bar</span>');
  });

  it("colore les littéraux JSON et les nombres", () => {
    const html = highlight('{"a": true, "n": 42}', "json");
    expect(html).toContain('<span class="tok-lit">true</span>');
    expect(html).toContain('<span class="tok-num">42</span>');
  });

  it("colore les commentaires de bloc js", () => {
    const html = highlight("/* x */ const a = 1;", "js");
    expect(html).toContain('<span class="tok-com">/* x */</span>');
    expect(html).toContain('<span class="tok-kw">const</span>');
  });

  it("n'injecte jamais de HTML brut (tout est échappé)", () => {
    const html = highlight('const x = "<img src=x onerror=alert(1)>";', "js");
    expect(html).not.toContain("<img");
    expect(html).toContain("&lt;img");
  });

  it("préserve le texte (une fois les balises retirées)", () => {
    const code = "for (let i = 0; i < 3; i++) count(i);";
    const stripped = highlight(code, "js").replace(/<[^>]+>/g, "")
      .replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&");
    expect(stripped).toBe(code);
  });
});
