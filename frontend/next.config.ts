import type { NextConfig } from "next";

// Export statique pour la fenêtre desktop (Tauri) : `next build` génère ./out.
// N'affecte PAS `next dev` (la version web continue de tourner normalement).
// Activé seulement quand on builde pour le desktop (MS_DESKTOP=1) afin de ne pas
// changer le comportement du build web par défaut.
const desktop = process.env.MS_DESKTOP === "1";

// Sous-chemin quand l'appli est servie derriere un reverse proxy (ex: Caddy sur
// /mi-saina). Vide par defaut : sans MS_BASE_PATH, rien ne change.
// Incompatible avec le build desktop, qui sert toujours depuis la racine.
const basePath = !desktop ? (process.env.MS_BASE_PATH ?? "") : "";

const nextConfig: NextConfig = {
  ...(desktop
    ? { output: "export", images: { unoptimized: true } }
    : {}),
  ...(basePath ? { basePath, assetPrefix: basePath } : {}),
};

export default nextConfig;
