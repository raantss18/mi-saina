// URL de base de l'API backend. Configurable via NEXT_PUBLIC_API_BASE pour
// permettre un port non standard (quand 8000 est déjà occupé). Défaut : 8000.
export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

// URL WebSocket dérivée (http→ws, https→wss).
export const WS_BASE = API_BASE.replace(/^http/, "ws");
