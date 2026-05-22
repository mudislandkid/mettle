//! Mettle desktop shell.
//!
//! Responsibilities:
//!   * Spawn the bundled `mettle-sidecar` (PyInstaller-frozen FastAPI) on launch.
//!   * Parse its `MettleReady port=NNNN token=XXXX` handshake from stdout.
//!   * Hand the resolved {port, token} pair to the Vue frontend via the
//!     `get_sidecar` invoke command.
//!   * Kill the sidecar cleanly on window close.

use std::sync::Arc;
use std::time::Duration;

use serde::Serialize;
use tauri::{Manager, RunEvent};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;
use tokio::sync::{watch, Mutex};
use tokio::time::timeout;

/// Resolved sidecar coordinates, served to the frontend via `get_sidecar`.
#[derive(Clone, Debug, Serialize)]
struct SidecarHandshake {
    port: u16,
    token: String,
}

/// Managed Tauri state.
///
/// The WebView typically loads JavaScript faster than the Python sidecar
/// can boot (PyInstaller one-file extraction + alembic migrations take a
/// few seconds on a cold launch). A naive `Mutex<Option<_>>` would let
/// `get_sidecar` return None to the frontend during that gap, the
/// frontend would fall back to relative URLs, and every API call would
/// fail.
///
/// `watch::Sender<Option<_>>` solves that: `get_sidecar` subscribes and
/// awaits the first Some value, so the frontend's `initRuntime()` call
/// blocks until the handshake actually lands.
struct SidecarState {
    handshake: watch::Sender<Option<SidecarHandshake>>,
    child: Mutex<Option<CommandChild>>,
}

impl SidecarState {
    fn new() -> Self {
        let (tx, _rx) = watch::channel(None);
        Self {
            handshake: tx,
            child: Mutex::new(None),
        }
    }
}

#[tauri::command]
async fn get_sidecar(state: tauri::State<'_, Arc<SidecarState>>) -> Result<SidecarHandshake, String> {
    // Subscribe to the handshake watch. If the value is already Some,
    // return it. Otherwise wait for the next change, with a 45s cap so a
    // hung sidecar surfaces as a real error instead of an infinite spinner.
    let mut rx = state.handshake.subscribe();
    if let Some(hs) = rx.borrow().clone() {
        return Ok(hs);
    }
    let result = timeout(Duration::from_secs(45), async move {
        loop {
            if let Some(hs) = rx.borrow().clone() {
                return Ok::<SidecarHandshake, String>(hs);
            }
            rx.changed()
                .await
                .map_err(|e| format!("handshake channel closed: {e}"))?;
        }
    })
    .await;
    match result {
        Ok(Ok(hs)) => Ok(hs),
        Ok(Err(e)) => Err(e),
        Err(_) => Err("timed out waiting for sidecar handshake".into()),
    }
}

/// Parse a `MettleReady port=NNNN token=hex` stdout line.
fn parse_handshake(line: &str) -> Option<SidecarHandshake> {
    if !line.starts_with("MettleReady") {
        return None;
    }
    let mut port: Option<u16> = None;
    let mut token: Option<String> = None;
    for tok in line.split_whitespace().skip(1) {
        if let Some(v) = tok.strip_prefix("port=") {
            port = v.parse().ok();
        } else if let Some(v) = tok.strip_prefix("token=") {
            token = Some(v.to_string());
        }
    }
    Some(SidecarHandshake { port: port?, token: token? })
}

/// Boot the bundled sidecar binary and wait for the handshake line.
async fn spawn_sidecar(app: &tauri::AppHandle, state: Arc<SidecarState>) -> Result<(), String> {
    // The sidecar writes mettle.db into the user data dir; resolving it here
    // and passing via env lets the Python side stay platform-agnostic.
    let data_dir = app
        .path()
        .app_data_dir()
        .map_err(|e| format!("resolve app_data_dir: {e}"))?;
    std::fs::create_dir_all(&data_dir).map_err(|e| format!("create data dir: {e}"))?;

    let sidecar = app
        .shell()
        .sidecar("mettle-sidecar")
        .map_err(|e| format!("locate sidecar: {e}"))?
        .env("METTLE_DATA_DIR", data_dir.to_string_lossy().to_string())
        .env("PYTHONUNBUFFERED", "1");

    let (mut rx, child) = sidecar.spawn().map_err(|e| format!("spawn sidecar: {e}"))?;

    {
        let mut slot = state.child.lock().await;
        *slot = Some(child);
    }

    // Pump stdout. The first MettleReady line populates the watch channel
    // (which `get_sidecar` is blocked on); we keep reading after that so
    // the sidecar's stdio pipe doesn't fill and block.
    let state_for_task = state.clone();
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    let line = String::from_utf8_lossy(&bytes).trim().to_string();
                    if !line.is_empty() {
                        eprintln!("[sidecar] {line}");
                    }
                    if let Some(hs) = parse_handshake(&line) {
                        let _ = state_for_task.handshake.send(Some(hs));
                    }
                }
                CommandEvent::Stderr(bytes) => {
                    let line = String::from_utf8_lossy(&bytes).trim().to_string();
                    if !line.is_empty() {
                        eprintln!("[sidecar:stderr] {line}");
                    }
                }
                CommandEvent::Error(err) => {
                    eprintln!("[sidecar] error: {err}");
                }
                CommandEvent::Terminated(payload) => {
                    eprintln!("[sidecar] terminated: {:?}", payload);
                    break;
                }
                _ => {}
            }
        }
    });

    // Wait until the handshake watch transitions to Some, with a 45s cap.
    let mut rx = state.handshake.subscribe();
    let wait = async move {
        loop {
            if rx.borrow().is_some() {
                return Ok::<(), String>(());
            }
            rx.changed()
                .await
                .map_err(|e| format!("handshake channel closed: {e}"))?;
        }
    };
    match timeout(Duration::from_secs(45), wait).await {
        Ok(Ok(())) => Ok(()),
        Ok(Err(e)) => Err(e),
        Err(_) => Err("timed out waiting for sidecar handshake".into()),
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let state = Arc::new(SidecarState::new());
    let state_for_setup = state.clone();
    let state_for_exit = state.clone();

    // Updater plugin. If METTLE_UPDATER_PAT is set at build time (CI does
    // this from a GitHub Actions secret) we add it as a Bearer header so the
    // plugin can fetch the manifest + release assets from a private GitHub
    // repo. Without the PAT (e.g. local dev builds) we register the plugin
    // without auth — the updater will 404 against private endpoints but
    // local dev doesn't usually exercise the update flow.
    //
    // The PAT is read via `option_env!` at compile time so it ends up baked
    // into the binary. That's the inherent trade-off of this approach —
    // anyone with a shipped `.app` can extract the token. Mitigation: scope
    // the PAT to a fine-grained read-only access to just this repo, and
    // rotate periodically. Once the repo is public this whole branch goes
    // away and the plugin needs no auth.
    let updater_plugin = {
        let builder = tauri_plugin_updater::Builder::new();
        let builder = match option_env!("METTLE_UPDATER_PAT") {
            Some(pat) if !pat.is_empty() => builder
                .header("Authorization", format!("Bearer {pat}"))
                .expect("invalid PAT header value"),
            _ => builder,
        };
        builder.build()
    };

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(updater_plugin)
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(state)
        .invoke_handler(tauri::generate_handler![get_sidecar])
        .setup(move |app| {
            eprintln!("[mettle] setup hook entered");
            let app_handle = app.handle().clone();
            let state = state_for_setup.clone();
            tauri::async_runtime::spawn(async move {
                eprintln!("[mettle] spawn_sidecar task starting");
                if let Err(e) = spawn_sidecar(&app_handle, state).await {
                    eprintln!("[mettle] sidecar startup failed: {e}");
                    // Surface a fatal error to the user; the WebView can't do
                    // anything useful without the backend.
                    use tauri_plugin_dialog::DialogExt;
                    app_handle
                        .dialog()
                        .message(format!(
                            "Mettle backend failed to start.\n\n{e}\n\n\
                             Please file an issue with the log if this persists."
                        ))
                        .title("Mettle")
                        .blocking_show();
                    app_handle.exit(1);
                }
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("failed to build tauri application")
        .run(move |_app_handle, event| {
            if let RunEvent::ExitRequested { .. } | RunEvent::Exit = &event {
                // Kill the sidecar synchronously so the user doesn't see a
                // dangling Python process after quitting.
                let state = state_for_exit.clone();
                tauri::async_runtime::block_on(async move {
                    let mut child = state.child.lock().await;
                    if let Some(c) = child.take() {
                        let _ = c.kill();
                    }
                });
            }
        });
}
