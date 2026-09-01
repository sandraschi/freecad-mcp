use std::fs::{self, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::net::{SocketAddr, TcpStream};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::str::FromStr;
use std::sync::Mutex;
use std::thread;
use std::time::Duration;

use tauri::path::BaseDirectory;
use tauri::{AppHandle, Emitter, Manager};

pub struct BackendProcess(pub Mutex<Option<Child>>);

const BACKEND_NAME: &str = "freecad-mcp-backend.exe";
const BACKEND_PORT: u16 = 10944;
const BACKEND_TAG: &str = "freecad-mcp-backend-x86_64-pc-windows-msvc.exe";
const ENV_PORT: &str = "MCP_PORT";
const ENV_HOST: &str = "MCP_HOST";
const ENV_TAURI: &str = "FREECAD_TAURI";

fn dev_backend_path() -> Option<PathBuf> {
    if !cfg!(debug_assertions) { return None; }
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("binaries")
        .join(BACKEND_TAG);
    path.exists().then_some(path)
}

fn log_line(app: &AppHandle, message: &str) {
    eprintln!("[backend] {message}");
    // primary: app_log_dir (Tauri managed, e.g. %LOCALAPPDATA%\ai.fleet.freecad-mcp\logs\)
    let mut logged = false;
    if let Ok(dir) = app.path().app_log_dir() {
        if fs::create_dir_all(&dir).is_ok() {
            let log_path = dir.join("backend-spawn.log");
            if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(&log_path) {
                let _ = writeln!(file, "{} {}", chrono_time(), message);
                logged = true;
            }
        }
    }
    // fallback: exe_dir/logs and %LOCALAPPDATA%\ai.fleet.freecad-mcp\logs (when app_log_dir not yet ready in setup thread)
    if !logged {
        for fallback in [
            std::env::current_exe().ok().and_then(|p| p.parent().map(|d| d.join("logs"))),
            dirs_fallback_log_dir(),
        ]
        .into_iter()
        .flatten()
        {
            if fs::create_dir_all(&fallback).is_ok() {
                let p = fallback.join("backend-spawn.log");
                if let Ok(mut f) = OpenOptions::new().create(true).append(true).open(p) {
                    let _ = writeln!(f, "{} {}", chrono_time(), message);
                    break;
                }
            }
        }
    }
}

fn chrono_time() -> String {
    // lightweight timestamp without extra deps
    if let Ok(t) = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH) {
        format!("[{}]", t.as_secs())
    } else {
        "[?]".to_string()
    }
}

fn dirs_fallback_log_dir() -> Option<PathBuf> {
    std::env::var("LOCALAPPDATA")
        .ok()
        .map(|v| PathBuf::from(v).join("ai.fleet.freecad-mcp").join("logs"))
}

fn resolve_bundled_backend(app: &AppHandle) -> Result<PathBuf, String> {
    let mut tried = Vec::new();
    if let Ok(path) = app.path().resolve(BACKEND_NAME, BaseDirectory::Resource) {
        tried.push(path.display().to_string());
        if path.exists() { return Ok(path); }
    }
    let resources_path = format!("resources/{BACKEND_NAME}");
    if let Ok(path) = app.path().resolve(&resources_path, BaseDirectory::Resource) {
        tried.push(path.display().to_string());
        if path.exists() { return Ok(path); }
    }
    // Tauri Resource fallback: resource_dir() is the actual bundle resources dir
    if let Ok(dir) = app.path().resource_dir() {
        let p = dir.join(BACKEND_NAME);
        tried.push(p.display().to_string());
        if p.exists() { return Ok(p); }
        let p2 = dir.join(&resources_path);
        tried.push(p2.display().to_string());
        if p2.exists() { return Ok(p2); }
    }
    // exe_dir fallback: NSIS installs to %LOCALAPPDATA%\FreeCAD MCP\ with resources\ subdir
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            let p = dir.join(BACKEND_NAME);
            tried.push(p.display().to_string());
            if p.exists() { return Ok(p); }
            let p2 = dir.join(&resources_path);
            tried.push(p2.display().to_string());
            if p2.exists() { return Ok(p2); }
            let p3 = dir.join("resources").join(BACKEND_NAME);
            tried.push(p3.display().to_string());
            if p3.exists() { return Ok(p3); }
        }
    }
    Err(format!("bundled backend missing (tried: {})", tried.join("; ")))
}

pub fn materialize_backend(app: &AppHandle) -> Result<PathBuf, String> {
    if let Some(dev_path) = dev_backend_path() {
        log_line(app, &format!("using dev backend: {}", dev_path.display()));
        return Ok(dev_path);
    }
    let bundled = resolve_bundled_backend(app)?;
    log_line(app, &format!("using bundled backend: {}", bundled.display()));
    Ok(bundled)
}

fn free_port(port: u16) -> bool {
    // Fast but real: kill stale backend/native, check port up to 10s, then return true anyway so setup doesn't block forever
    #[cfg(windows)]
    {
        let img_kill = "Stop-Process -Name 'freecad-mcp-backend' -Force -ErrorAction SilentlyContinue; Stop-Process -Name 'freecad-mcp-native' -Force -ErrorAction SilentlyContinue; taskkill /F /IM freecad-mcp-backend.exe /T 2>$null; taskkill /F /IM freecad-mcp-native.exe /T 2>$null";
        let _ = Command::new("powershell.exe").args(["-NoProfile", "-Command", img_kill]).stdout(Stdio::null()).stderr(Stdio::null()).status();
        let port_kill = format!("Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | ForEach-Object {{ taskkill /F /PID $_.OwningProcess /T 2>$null }}");
        let _ = Command::new("powershell.exe").args(["-NoProfile", "-Command", &port_kill]).stdout(Stdio::null()).stderr(Stdio::null()).status();
        for i in 0..10 {
            let poll = format!("if (Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue) {{ 1 }} else {{ 0 }}");
            let out = Command::new("powershell.exe").args(["-NoProfile", "-Command", &poll]).stdout(Stdio::piped()).stderr(Stdio::null()).output();
            let occ = out.ok().and_then(|o| String::from_utf8(o.stdout).ok().and_then(|s| s.trim().parse::<u32>().ok())).unwrap_or(1);
            if occ == 0 { return true; }
            if i == 2 { let _ = Command::new("powershell.exe").args(["-NoProfile", "-Command", img_kill]).status(); let _ = Command::new("powershell.exe").args(["-NoProfile", "-Command", &port_kill]).status(); }
            thread::sleep(Duration::from_secs(1));
        }
        return true;
    }
    #[cfg(not(windows))] { true }
}

fn stop_managed_child(state: &BackendProcess) {
    if let Some(mut child) = state.0.lock().unwrap().take() {
        let _ = child.kill();
        let _ = child.wait();
    }
}

pub fn spawn_backend(app: AppHandle, state: &BackendProcess) -> Result<String, String> {
    stop_managed_child(state);
    if !free_port(BACKEND_PORT) {
        let msg = format!("Could not free port {BACKEND_PORT} after 240s — TIME_WAIT not cleared");
        log_line(&app, &msg);
        return Err(msg);
    }

    let backend_path = materialize_backend(&app)?;
    log_line(&app, &format!("spawning {} on port {}", backend_path.display(), BACKEND_PORT));

    let mut command = Command::new(&backend_path);
    command
        .env(ENV_PORT, BACKEND_PORT.to_string())
        .env(ENV_HOST, "127.0.0.1")
        .env(ENV_TAURI, "1")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        command.creation_flags(CREATE_NO_WINDOW);
    }

    let mut child = command
        .spawn()
        .map_err(|e| format!("Failed to spawn {}: {e}", backend_path.display()))?;

    let stdout = child.stdout.take();
    let stderr = child.stderr.take();
    state.0.lock().unwrap().replace(child);

    if let Some(out) = stdout {
        let handle = app.clone();
        thread::spawn(move || watch_backend_stream(out, handle));
    }
    if let Some(err) = stderr {
        let handle = app.clone();
        thread::spawn(move || watch_backend_stream(err, handle));
    }

    // Poll backend TCP port to confirm it's listening
    let addr = SocketAddr::from_str(&format!("127.0.0.1:{BACKEND_PORT}")).unwrap();
    let app_health = app.clone();
    thread::spawn(move || {
        for attempt in 0..30 {
            thread::sleep(Duration::from_secs(2));
            match TcpStream::connect_timeout(&addr, Duration::from_secs(2)) {
                Ok(_) => {
                    log_line(&app_health, &format!("Backend health check PASSED on port {BACKEND_PORT} (attempt {})", attempt + 1));
                    let _ = app_health.emit("backend-status", "ready");
                    return;
                }
                Err(e) => {
                    log_line(&app_health, &format!("Backend health check: {e} (attempt {})", attempt + 1));
                }
            }
        }
        log_line(&app_health, &format!("Backend health check FAILED — not listening on port {BACKEND_PORT} after 30 attempts"));
        let _ = app_health.emit("backend-status", "error: backend not reachable");
    });

    Ok(format!("Backend starting on port {BACKEND_PORT}"))
}

fn watch_backend_stream<R: std::io::Read + Send + 'static>(stream: R, app: AppHandle) {
    let reader = BufReader::new(stream);
    let mut ready = false;
    for line in reader.lines().map_while(Result::ok) {
        log_line(&app, &line);
        if !ready && (line.contains("Uvicorn running") || line.contains("Application startup complete")) {
            ready = true;
            let _ = app.emit("backend-status", "ready");
        }
    }
}
