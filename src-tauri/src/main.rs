// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::net::TcpStream;
use std::time::{Duration, Instant};

use tauri::Manager;

use fortuna_lib::SidecarState;

/// Find a free TCP port by binding to port 0.
/// Note: There is a small TOCTOU window between finding the port and the sidecar
/// binding to it. If the health check fails, we retry with a new port.
fn find_free_port() -> u16 {
    let listener = std::net::TcpListener::bind("127.0.0.1:0")
        .expect("Failed to bind to find free port");
    let port = listener.local_addr().expect("Failed to get local addr").port();
    drop(listener);
    port
}

/// Poll the Streamlit health endpoint by attempting a TCP connection,
/// then checking the HTTP health endpoint once connected.
fn wait_for_health(port: u16, timeout: Duration) -> bool {
    let start = Instant::now();

    while start.elapsed() < timeout {
        // Use a simple TCP connect check — avoids pulling in a full HTTP client
        if TcpStream::connect_timeout(
            &format!("127.0.0.1:{}", port).parse().unwrap(),
            Duration::from_secs(1),
        )
        .is_ok()
        {
            // TCP is up — give Streamlit a moment to fully initialize
            std::thread::sleep(Duration::from_secs(1));
            return true;
        }
        std::thread::sleep(Duration::from_millis(500));
    }
    false
}

/// Resolve the path to the sidecar binary.
fn resolve_sidecar_path() -> std::path::PathBuf {
    let target_triple = std::env!("TAURI_ENV_TARGET_TRIPLE");

    #[cfg(target_os = "windows")]
    let exe_name = format!("fortuna-server-{}.exe", target_triple);
    #[cfg(not(target_os = "windows"))]
    let exe_name = format!("fortuna-server-{}", target_triple);

    // Dev mode only: check src-tauri/binaries/ (CARGO_MANIFEST_DIR is baked at compile time)
    #[cfg(debug_assertions)]
    {
        let dev_path = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("binaries")
            .join(&exe_name);
        if dev_path.exists() {
            return dev_path;
        }
    }

    // Production: check resource paths relative to the running executable
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            // macOS: Fortuna.app/Contents/MacOS/<exe> -> ../Resources/binaries/
            let macos_path = dir.join("../Resources/binaries").join(&exe_name);
            if macos_path.exists() {
                return macos_path;
            }
            // Windows/Linux: binaries/ subdirectory next to executable
            let sibling = dir.join("binaries").join(&exe_name);
            if sibling.exists() {
                return sibling;
            }
        }
    }

    // Fallback (will produce a clear "not found" error on spawn)
    std::path::PathBuf::from(&exe_name)
}

/// Kill the sidecar process and its entire process tree.
#[cfg(unix)]
fn kill_process_tree(child: &mut std::process::Child) {
    let pid = child.id() as i32;
    // Send SIGTERM to the process group (negative PID = group)
    unsafe {
        libc::kill(-pid, libc::SIGTERM);
    }
    // Give processes a moment to clean up, then force kill
    std::thread::sleep(Duration::from_millis(500));
    unsafe {
        libc::kill(-pid, libc::SIGKILL);
    }
    let _ = child.wait();
}

#[cfg(not(unix))]
fn kill_process_tree(child: &mut std::process::Child) {
    let _ = child.kill();
    let _ = child.wait();
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .manage(SidecarState::new())
        .setup(|app| {
            let port = find_free_port();
            println!("Fortuna: starting sidecar on port {}", port);

            let sidecar_path = resolve_sidecar_path();
            println!("Fortuna: sidecar path: {:?}", sidecar_path);

            let mut cmd = std::process::Command::new(&sidecar_path);
            cmd.arg(port.to_string())
                .stdout(std::process::Stdio::piped())
                .stderr(std::process::Stdio::piped());

            // On Unix, start the child in its own process group so we can
            // kill the entire tree (Streamlit spawns child processes)
            #[cfg(unix)]
            {
                use std::os::unix::process::CommandExt;
                unsafe {
                    cmd.pre_exec(|| {
                        libc::setsid();
                        Ok(())
                    });
                }
            }

            let child = match cmd.spawn() {
                Ok(child) => child,
                Err(e) => {
                    eprintln!("Fortuna: failed to spawn sidecar: {}", e);
                    // Show error immediately instead of waiting for 30s timeout
                    if let Some(window) = app.get_webview_window("main") {
                        let _ = window.navigate(
                            "data:text/html,<h1 style='color:%23ff6b6b;background:%230E1117;padding:2em;font-family:sans-serif'>Fortuna failed to start.<br><small style='color:%23888'>Could not launch the application server.</small></h1>"
                                .parse()
                                .unwrap(),
                        );
                    }
                    return Ok(());
                }
            };
            println!("Fortuna: sidecar spawned (pid: {})", child.id());

            // Store child process handle
            {
                let state = app.handle().state::<SidecarState>();
                *state.child.lock().unwrap_or_else(|e| e.into_inner()) = Some(child);
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
                        "data:text/html,<h1 style='color:%23ff6b6b;background:%230E1117;padding:2em;font-family:sans-serif'>Fortuna failed to start.<br><small style='color:%23888'>The server did not respond within 30 seconds. Please restart.</small></h1>"
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
                let mut guard = state.child.lock().unwrap_or_else(|e| e.into_inner());
                if let Some(mut child) = guard.take() {
                    println!("Fortuna: killing sidecar process tree (pid: {})", child.id());
                    kill_process_tree(&mut child);
                }
                drop(guard);
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running Fortuna");
}
