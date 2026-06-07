// Libellés et tags « jolis » pour les modèles connus. Partagé entre le sélecteur
// du header et le panneau Modèles. Pour un modèle inconnu : libellé = nom brut
// légèrement embelli.

export const MODEL_DESCRIPTIONS: Record<string, { label: string; tags: string[] }> = {
  "deepseek-r1:8b": { label: "DeepSeek R1 8B", tags: ["raisonnement", "8B"] },
  "deepseek-r1:14b": { label: "DeepSeek R1 14B", tags: ["raisonnement", "14B"] },
  "gemma3:1b": { label: "Gemma 3 1B", tags: ["Google", "1B"] },
  "gemma3:4b": { label: "Gemma 3 4B", tags: ["Google", "4B"] },
  "gemma3:12b": { label: "Gemma 3 12B", tags: ["Google", "12B"] },
  "phi4-reasoning:latest": { label: "Phi-4 Reasoning+", tags: ["Microsoft", "14B"] },
  "gpt-oss:20b": { label: "GPT-OSS 20B", tags: ["OpenAI", "20B"] },
  "magistral:small": { label: "Magistral Small", tags: ["Mistral", "24B"] },
  "qwen2.5:3b": { label: "Qwen 2.5 3B", tags: ["Qwen", "3B"] },
  "qwen3:8b": { label: "Qwen 3 8B", tags: ["Qwen", "8B"] },
  "qwen3:14b": { label: "Qwen 3 14B", tags: ["Qwen", "14B"] },
  "qwen3.5:9b": { label: "Qwen 3.5 9B", tags: ["Qwen", "9B"] },
  "llama3.2:3b": { label: "Llama 3.2 3B", tags: ["Meta", "3B"] },
  "mistral:7b": { label: "Mistral 7B", tags: ["Mistral", "7B"] },
  "nomic-embed-text:latest": { label: "Nomic Embed", tags: ["embeddings"] },
};

export function modelDesc(name: string): { label: string; tags: string[] } {
  return MODEL_DESCRIPTIONS[name] ?? { label: prettifyModel(name), tags: [] };
}

export function modelLabel(name: string): string {
  return modelDesc(name).label;
}

// Embellit un nom brut « qwen3.5:9b » → « Qwen3.5 9B » sans table.
function prettifyModel(name: string): string {
  if (!name) return name;
  const [base, tag] = name.split(":");
  const cap = base.charAt(0).toUpperCase() + base.slice(1);
  return tag ? `${cap} ${tag.toUpperCase()}` : cap;
}
