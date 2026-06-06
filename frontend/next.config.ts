import type { NextConfig } from "next";

// Export statique pour la fenêtre desktop (Tauri) : `next build` génère ./out.
// N'affecte PAS `next dev` (la version web continue de tourner normalement).
// Activé seulement quand on builde pour le desktop (MS_DESKTOP=1) afin de ne pas
// changer le comportement du build web par défaut.
const desktop = process.env.MS_DESKTOP === "1";

const nextConfig: NextConfig = {
  ...(desktop
    ? { output: "export", images: { unoptimized: true } }
    : {}),
};

export default nextConfig;
