// Intégrations natives Tauri (notifications, lancement au démarrage). Tout est
// gardé par isTauri() : en mode web, ces fonctions sont des no-op silencieux et
// les plugins ne sont jamais chargés (import dynamique).

export function isTauri(): boolean {
  return typeof window !== "undefined" &&
    ("__TAURI_INTERNALS__" in window || "__TAURI__" in window);
}

// Envoie une notification système. No-op hors desktop ou si la permission est refusée.
export async function notify(title: string, body: string): Promise<void> {
  if (!isTauri()) return;
  try {
    const { isPermissionGranted, requestPermission, sendNotification } =
      await import("@tauri-apps/plugin-notification");
    let granted = await isPermissionGranted();
    if (!granted) granted = (await requestPermission()) === "granted";
    if (granted) sendNotification({ title, body });
  } catch { /* plugin indisponible */ }
}

export async function isAutostartEnabled(): Promise<boolean> {
  if (!isTauri()) return false;
  try {
    const { isEnabled } = await import("@tauri-apps/plugin-autostart");
    return await isEnabled();
  } catch { return false; }
}

export async function setAutostart(on: boolean): Promise<void> {
  if (!isTauri()) return;
  try {
    const { enable, disable } = await import("@tauri-apps/plugin-autostart");
    if (on) await enable(); else await disable();
  } catch { /* plugin indisponible */ }
}
