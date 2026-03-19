// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::net::TcpListener;
use std::time::{Duration, Instant};

use tauri::Manager;

use fortuna_lib::SidecarState;

/// Find a free TCP port by binding to port 0.
fn find_free_port() -> u16 {
    TcpListener::bind("127.0.0.1:0")
        .expect("Failed to bind to find free port")
        .local_addr()
        .expect("Failed to get local addr")
        .port()
}

/// Poll the Streamlit health endpoint until it responds OK or timeout.
fn wait_for_health(port: u16, timeout: Duration) -> bool {
    let url = format!("http://127.0.0.1:{}/_stcore/health", port);
    let start = Instant::now();
    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
        .unwrap();

    while start.elapsed() < timeout {
        if let Ok(resp) = client.get(&url).send() {
            if resp.status().is_success() {
                return true;
            }
        }
        std::thread::sleep(Duration::from_millis(500));
    }
    false
}

/// Resolve the path to the sidecar binary.
/// In dev mode: src-tauri/binaries/fortuna-server-<triple>
/// In production (macOS): Fortuna.app/Contents/Resources/binaries/fortuna-server-<triple>
/// In production (Windows): <install-dir>/binaries/fortuna-server-<triple>.exe
fn resolve_sidecar_path() -> std::path::PathBuf {
    let target_triple = std::env!("TAURI_ENV_TARGET_TRIPLE");

    #[cfg(target_os = "windows")]
    let exe_name = format!("fortuna-server-{}.exe", target_triple);
    #[cfg(not(target_os = "windows"))]
    let exe_name = format!("fortuna-server-{}", target_triple);

    // In dev mode, the binary is in src-tauri/binaries/
    let dev_path = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("binaries")
        .join(&exe_name);
    if dev_path.exists() {
        return dev_path;
    }

    // In production, check resource paths
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            // macOS: Fortuna.app/Contents/MacOS/<exe> -> ../Resources/binaries/
            let macos_path = dir.join("../Resources/binaries").join(&exe_name);
            if macos_path.exists() {
                return macos_path;
            }
            // Windows/Linux: same directory as executable
            let sibling = dir.join("binaries").join(&exe_name);
            if sibling.exists() {
                return sibling;
            }
            // Direct sibling (fallback)
            let direct = dir.join(&exe_name);
            if direct.exists() {
                return direct;
            }
        }
    }

    // Fallback to dev path
    dev_path
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_opener::init())
        .manage(SidecarState::new())
        .setup(|app| {
            // Find a free port for the Streamlit server
            let port = find_free_port();
            println!("Fortuna: starting sidecar on port {}", port);

            // Resolve and spawn sidecar binary directly
            let sidecar_path = resolve_sidecar_path();
            println!("Fortuna: sidecar path: {:?}", sidecar_path);

            let child = match std::process::Command::new(&sidecar_path)
                .arg(port.to_string())
                .stdout(std::process::Stdio::piped())
                .stderr(std::process::Stdio::piped())
                .spawn()
            {
                Ok(child) => child,
                Err(e) => {
                    eprintln!("Fortuna: failed to spawn sidecar: {}", e);
                    return Ok(());
                }
            };
            println!("Fortuna: sidecar spawned (pid: {})", child.id());

            // Store child process handle
            {
                let state = app.handle().state::<SidecarState>();
                *state.child.lock().unwrap() = Some(child);
            }

            // Spawn a thread to wait for health and navigate
            let window = app.get_webview_window("main").unwrap();
            std::thread::spawn(move || {
                let timeout = Duration::from_secs(30);
                if wait_for_health(port, timeout) {
                    let url = format!("http://127.0.0.1:{}", port);
                    println!("Fortuna: Streamlit ready at {}", url);
                    let _ = window.navigate(url.parse().unwrap());
                } else {
                    eprintln!("Fortuna: Streamlit failed to start within {:?}", timeout);
                    let _ = window.navigate(
                        "data:text/html,<h1 style='color:white;background:#0E1117;padding:2em;font-family:sans-serif'>Fortuna failed to start. Please restart the application.</h1>"
                            .parse()
                            .unwrap(),
                    );
                }
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                let state = window.state::<SidecarState>();
                let mut guard = state.child.lock().unwrap();
                if let Some(mut child) = guard.take() {
                    println!("Fortuna: killing sidecar process (pid: {})", child.id());
                    let _ = child.kill();
                    let _ = child.wait();
                }
                drop(guard);
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running Fortuna");
}
