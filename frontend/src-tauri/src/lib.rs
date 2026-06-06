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

    builder
        .setup(|app| {
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
        .run(tauri::generate_context!())
        .expect("erreur au démarrage de mi-saina");
}
