use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, TrayIconBuilder, TrayIconEvent},
    Manager, WindowEvent,
};

fn show_main(app: &tauri::AppHandle) {
    if let Some(w) = app.get_webview_window("main") {
        let _ = w.show();
        let _ = w.unminimize();
        let _ = w.set_focus();
    }
}

// Bascule la visibilité de la fenêtre principale (utilisé par le raccourci global).
#[cfg(desktop)]
fn toggle_main(app: &tauri::AppHandle) {
    if let Some(w) = app.get_webview_window("main") {
        if w.is_visible().unwrap_or(false) && w.is_focused().unwrap_or(false) {
            let _ = w.hide();
        } else {
            show_main(app);
        }
    }
}

// ───────────────────────── Backend géré par l'appli (autonomie) ─────────────
// Si le backend n'est pas déjà actif (ex. service systemd), l'appli le démarre
// elle-même depuis le venv local et l'arrête en quittant. Pour ta machine où
// systemd sert déjà le backend, c'est un no-op. Désactivable : MS_NO_BACKEND_SPAWN.
#[cfg(desktop)]
mod backend {
    use std::net::{SocketAddr, TcpStream};
    use std::path::PathBuf;
    use std::process::{Child, Command, Stdio};
    use std::time::Duration;

    pub const PORT: u16 = 8000;

    pub fn is_up(port: u16) -> bool {
        let addr: SocketAddr = ([127, 0, 0, 1], port).into();
        TcpStream::connect_timeout(&addr, Duration::from_millis(400)).is_ok()
    }

    // Trouve le dossier backend selon le mode d'installation :
    // - /opt : <prefix>/bin/mi-saina  -> <prefix>/backend
    // - dev  : <repo>/frontend/src-tauri/target/{debug,release}/mi-saina -> <repo>/backend
    fn backend_dir() -> Option<PathBuf> {
        let exe = std::env::current_exe().ok()?;
        let mut candidates: Vec<PathBuf> = Vec::new();
        if let Some(prefix) = exe.parent().and_then(|b| b.parent()) {
            candidates.push(prefix.join("backend")); // install /opt
        }
        if let Some(repo) = exe.ancestors().nth(5) {
            candidates.push(repo.join("backend")); // dépôt source
        }
        candidates.into_iter().find(|d| d.join("main.py").exists())
    }

    fn find_uvicorn() -> Option<PathBuf> {
        // venv embarqué d'une install /opt (<prefix>/venv), à côté de bin/.
        if let Ok(exe) = std::env::current_exe() {
            if let Some(prefix) = exe.parent().and_then(|b| b.parent()) {
                let p = prefix.join("venv").join("bin").join("uvicorn");
                if p.exists() {
                    return Some(p);
                }
            }
        }
        if let Some(home) = std::env::var_os("HOME") {
            for venv in ["mi-saina-env", "localmind-env"] {
                let p = PathBuf::from(&home).join(venv).join("bin").join("uvicorn");
                if p.exists() {
                    return Some(p);
                }
            }
        }
        None
    }

    // Démarre le backend si possible. Renvoie le process enfant à arrêter en sortie.
    pub fn spawn(port: u16) -> Option<Child> {
        let dir = backend_dir()?;
        let uvicorn = find_uvicorn()?;
        let mut cmd = Command::new(uvicorn);
        cmd.args(["main:app", "--host", "127.0.0.1", "--port", &port.to_string()])
            .current_dir(dir)
            .stdout(Stdio::null())
            .stderr(Stdio::null());

        // Linux : si l'appli meurt (même par SIGTERM/SIGKILL, ex. fin de session),
        // le noyau envoie SIGTERM au backend → pas d'orphelin sur le port 8000.
        #[cfg(target_os = "linux")]
        {
            use std::os::unix::process::CommandExt;
            unsafe {
                cmd.pre_exec(|| {
                    libc::prctl(libc::PR_SET_PDEATHSIG, libc::SIGTERM);
                    Ok(())
                });
            }
        }

        cmd.spawn().ok()
    }
}

// Process backend géré, arrêté proprement à la fermeture de l'appli.
#[cfg(desktop)]
struct BackendProc(std::sync::Mutex<Option<std::process::Child>>);

pub fn run() {
    let mut builder = tauri::Builder::default();

    // Instance unique : si mi-saina tourne déjà (ex. lancé au démarrage dans le
    // tray), relancer depuis le menu Applications ramène la fenêtre existante au
    // lieu d'ouvrir un 2e processus. Doit être enregistré en PREMIER.
    #[cfg(desktop)]
    {
        builder = builder.plugin(tauri_plugin_single_instance::init(|app, _argv, _cwd| {
            show_main(app);
        }));
    }

    builder = builder
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_notification::init());

    // Lancement au démarrage (opt-in côté UI) + raccourci global, desktop seulement.
    #[cfg(desktop)]
    {
        use tauri_plugin_autostart::MacosLauncher;
        builder = builder
            .plugin(tauri_plugin_autostart::init(
                MacosLauncher::LaunchAgent,
                Some(vec!["--minimized"]),
            ))
            .plugin(tauri_plugin_global_shortcut::Builder::new().build());
    }

    let app = builder
        .setup(|app| {
            // Backend autonome : démarre le serveur s'il n'est pas déjà actif.
            #[cfg(desktop)]
            {
                let spawn_allowed = std::env::var_os("MS_NO_BACKEND_SPAWN").is_none();
                let child = if spawn_allowed && !backend::is_up(backend::PORT) {
                    backend::spawn(backend::PORT)
                } else {
                    None
                };
                app.manage(BackendProc(std::sync::Mutex::new(child)));
            }

            // Menu de l'icône de la barre système (tray)
            let show = MenuItem::with_id(app, "show", "Afficher mi-saina", true, None::<&str>)?;
            let quit = MenuItem::with_id(app, "quit", "Quitter", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show, &quit])?;

            TrayIconBuilder::with_id("main-tray")
                .icon(app.default_window_icon().unwrap().clone())
                .tooltip("mi-saina")
                .menu(&menu)
                .show_menu_on_left_click(false)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "show" => show_main(app),
                    "quit" => app.exit(0),
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        ..
                    } = event
                    {
                        show_main(tray.app_handle());
                    }
                })
                .build(app)?;

            // Raccourci global : Ctrl+Alt+M affiche/masque mi-saina depuis n'importe où.
            #[cfg(desktop)]
            {
                use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Modifiers, Shortcut, ShortcutState};
                let toggle = Shortcut::new(Some(Modifiers::CONTROL | Modifiers::ALT), Code::KeyM);
                app.global_shortcut().on_shortcut(toggle, move |app, _scut, event| {
                    if event.state() == ShortcutState::Pressed {
                        toggle_main(app);
                    }
                })?;
            }

            // Lancé au démarrage de session avec --minimized : démarrer dans le
            // tray (fenêtre masquée) au lieu d'ouvrir la fenêtre.
            #[cfg(desktop)]
            if std::env::args().any(|a| a == "--minimized") {
                if let Some(w) = app.get_webview_window("main") {
                    let _ = w.hide();
                }
            }

            Ok(())
        })
        // Fermer la fenêtre = la réduire dans le tray (mi-saina reste en fond).
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                let _ = window.hide();
                api.prevent_close();
            }
        })
        .build(tauri::generate_context!())
        .expect("erreur au démarrage de mi-saina");

    app.run(|_app_handle, _event| {
        // À la sortie de l'appli, arrête le backend qu'on a éventuellement démarré.
        #[cfg(desktop)]
        if let tauri::RunEvent::Exit = _event {
            if let Some(state) = _app_handle.try_state::<BackendProc>() {
                if let Ok(mut guard) = state.0.lock() {
                    if let Some(child) = guard.as_mut() {
                        let _ = child.kill();
                        let _ = child.wait();
                    }
                }
            }
        }
    });
}
