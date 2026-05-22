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
use tokio::sync::{oneshot, Mutex};
use tokio::time::timeout;

/// Resolved sidecar coordinates, served to the frontend via `get_sidecar`.
#[derive(Clone, Debug, Serialize)]
struct SidecarHandshake {
    port: u16,
    token: String,
}

/// Managed Tauri state. The handshake is resolved once at startup; subsequent
/// reads of `get_sidecar` clone the result.
struct SidecarState {
    inner: Mutex<Option<SidecarHandshake>>,
    child: Mutex<Option<CommandChild>>,
}

impl SidecarState {
    fn new() -> Self {
        Self {
            inner: Mutex::new(None),
            child: Mutex::new(None),
        }
    }
}

#[tauri::command]
async fn get_sidecar(state: tauri::State<'_, Arc<SidecarState>>) -> Result<SidecarHandshake, String> {
    let guard = state.inner.lock().await;
    guard
        .clone()
        .ok_or_else(|| "sidecar handshake not yet completed".to_string())
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

    // Pump stdout. The first MettleReady line resolves the handshake; we keep
    // reading after that so the sidecar's stdio pipe doesn't fill and block.
    let (ready_tx, ready_rx) = oneshot::channel::<SidecarHandshake>();
    let state_for_task = state.clone();
    tauri::async_runtime::spawn(async move {
        let mut ready_tx = Some(ready_tx);
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    let line = String::from_utf8_lossy(&bytes).trim().to_string();
                    if !line.is_empty() {
                        eprintln!("[sidecar] {line}");
                    }
                    if let Some(hs) = parse_handshake(&line) {
                        {
                            let mut slot = state_for_task.inner.lock().await;
                            *slot = Some(hs.clone());
                        }
                        if let Some(tx) = ready_tx.take() {
                            let _ = tx.send(hs);
                        }
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

    // Give the sidecar 45s to print MettleReady — PyInstaller one-file
    // extraction on a cold disk can be slow on first launch.
    match timeout(Duration::from_secs(45), ready_rx).await {
        Ok(Ok(_)) => Ok(()),
        Ok(Err(_)) => Err("sidecar stdout closed before handshake".into()),
        Err(_) => Err("timed out waiting for sidecar handshake".into()),
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let state = Arc::new(SidecarState::new());
    let state_for_setup = state.clone();
    let state_for_exit = state.clone();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
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
