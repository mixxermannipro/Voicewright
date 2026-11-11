use serde::{Deserialize, Serialize};
use std::{
    path::Path,
    process::Stdio,
    sync::atomic::{AtomicBool, Ordering},
    time::Duration,
};
use tokio::io::{AsyncReadExt, AsyncWriteExt};

const MAX_REQUEST_BYTES: usize = 256 * 1024;
const MAX_RESPONSE_BYTES: usize = 128 * 1024;
const CLEANUP_TIMEOUT: Duration = Duration::from_secs(240);
const MEMORY_POLL_INTERVAL: Duration = Duration::from_millis(250);
const MIN_MEMORY_LIMIT: u64 = 3 * 1024 * 1024 * 1024;
const MEMORY_OVERHEAD: u64 = 3 * 1024 * 1024 * 1024;
const MAX_MEMORY_LIMIT: u64 = 8 * 1024 * 1024 * 1024;

#[derive(Serialize)]
struct Request<'a> {
    model: &'a Path,
    system: &'a str,
    transcript: &'a str,
}

#[derive(Deserialize)]
#[serde(untagged)]
enum Response {
    Success { text: String },
    Failure { error: String },
}

pub async fn wait_for_cancel(cancelled: &AtomicBool) {
    while !cancelled.load(Ordering::Relaxed) {
        tokio::time::sleep(Duration::from_millis(40)).await;
    }
}

pub async fn local(
    model: &Path,
    system: &str,
    transcript: &str,
    cancelled: &AtomicBool,
) -> Result<String, String> {
    let binary = std::env::current_exe()
        .map_err(|_| "Could not locate the cleanup engine.")?
        .with_file_name(format!(
            "voicewright-cleanup{}",
            std::env::consts::EXE_SUFFIX
        ));
    run_with_limits(
        &binary,
        model,
        system,
        transcript,
        cancelled,
        CLEANUP_TIMEOUT,
    )
    .await
}

async fn run_with_limits(
    binary: &Path,
    model: &Path,
    system: &str,
    transcript: &str,
    cancelled: &AtomicBool,
    timeout: Duration,
) -> Result<String, String> {
    let request = serde_json::to_vec(&Request {
        model,
        system,
        transcript,
    })
    .map_err(|_| "Invalid cleanup request.")?;
    if request.len() > MAX_REQUEST_BYTES {
        return Err("The transcript is too large for local cleanup.".into());
    }
    if cancelled.load(Ordering::Relaxed) {
        return Err("cancelled".into());
    }
    let mut command = tokio::process::Command::new(binary);
    #[cfg(windows)]
    command.creation_flags(0x08000000);
    let mut child = command
        .kill_on_drop(true)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|_| "Could not start the bundled cleanup engine.")?;
    let mut stdin = child.stdin.take().ok_or("Could not open cleanup input.")?;
    let mut stdout = child
        .stdout
        .take()
        .ok_or("Could not open cleanup output.")?
        .take(MAX_RESPONSE_BYTES as u64 + 1);
    let memory_watch = watch_memory(child.id().map(sysinfo::Pid::from_u32), memory_limit(model));
    let result = tokio::select! {
        _ = wait_for_cancel(cancelled) => Err("cancelled".into()),
        _ = memory_watch => Err("Local cleanup exceeded its memory limit.".into()),
        result = tokio::time::timeout(timeout, async {
            let ((), bytes) = tokio::try_join!(
                async move { stdin.write_all(&request).await?; stdin.shutdown().await },
                async move {
                    let mut output = Vec::new();
                    stdout.read_to_end(&mut output).await?;
                    Ok(output)
                }
            ).map_err(|_: std::io::Error| "Could not communicate with the cleanup engine.")?;
            if bytes.len() > MAX_RESPONSE_BYTES { return Err("The cleanup engine response was too large.".into()); }
            let status = child.wait().await.map_err(|_| "The cleanup engine could not finish.")?;
            if !status.success() { return Err("The cleanup engine stopped unexpectedly.".into()); }
            match serde_json::from_slice(&bytes).map_err(|_| "The cleanup engine returned invalid data.")? {
                Response::Success { text } if !text.trim().is_empty() => Ok(text),
                Response::Failure { error } => Err(error),
                _ => Err("The cleanup engine returned no text.".into()),
            }
        }) => result.unwrap_or_else(|_| Err("Local cleanup took too long.".into())),
    };
    if result.is_err() {
        let _ = child.kill().await;
    }
    result
}

async fn watch_memory(pid: Option<sysinfo::Pid>, limit: u64) {
    let Some(pid) = pid else {
        std::future::pending::<()>().await;
        return;
    };
    let mut system = sysinfo::System::new();
    loop {
        tokio::time::sleep(MEMORY_POLL_INTERVAL).await;
        system.refresh_processes(sysinfo::ProcessesToUpdate::Some(&[pid]), true);
        if system
            .process(pid)
            .is_some_and(|process| process.memory() > limit)
        {
            return;
        }
    }
}

fn memory_limit(model: &Path) -> u64 {
    let model_bytes = model.metadata().map_or(0, |metadata| metadata.len());
    model_bytes
        .saturating_add(MEMORY_OVERHEAD)
        .clamp(MIN_MEMORY_LIMIT, MAX_MEMORY_LIMIT)
}

#[cfg(test)]
mod tests {
    use super::{memory_limit, run_with_limits, MAX_MEMORY_LIMIT, MIN_MEMORY_LIMIT};
    use std::{
        path::Path,
        sync::{
            atomic::{AtomicBool, Ordering},
            Arc,
        },
        time::Duration,
    };

    #[cfg(unix)]
    fn script(body: &str) -> (tempfile::TempDir, std::path::PathBuf) {
        use std::os::unix::fs::PermissionsExt;
        let directory = tempfile::tempdir().unwrap();
        let path = directory.path().join("voicewright-cleanup");
        std::fs::write(&path, format!("#!/bin/sh\n{body}\n")).unwrap();
        let mut permissions = std::fs::metadata(&path).unwrap().permissions();
        permissions.set_mode(0o755);
        std::fs::set_permissions(&path, permissions).unwrap();
        (directory, path)
    }

    #[test]
    fn memory_limit_has_a_floor_and_a_ceiling() {
        assert_eq!(memory_limit(Path::new("/missing.gguf")), MIN_MEMORY_LIMIT);
        let directory = tempfile::tempdir().unwrap();
        let large = directory.path().join("large.gguf");
        std::fs::File::create(&large)
            .unwrap()
            .set_len(MAX_MEMORY_LIMIT + 1)
            .unwrap();
        assert_eq!(memory_limit(&large), MAX_MEMORY_LIMIT);
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn runs_a_sidecar_and_returns_its_text() {
        let (_directory, binary) = script("cat >/dev/null\nprintf '{\"text\":\"ok\"}'");
        let cancelled = AtomicBool::new(false);
        let result = run_with_limits(
            &binary,
            Path::new("/missing.gguf"),
            "system",
            "transcript",
            &cancelled,
            Duration::from_secs(5),
        )
        .await;
        assert_eq!(result, Ok("ok".into()));
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn reports_sidecar_errors_and_invalid_output() {
        let (_directory, binary) = script("cat >/dev/null\nprintf '{\"error\":\"boom\"}'");
        let cancelled = AtomicBool::new(false);
        let result = run_with_limits(
            &binary,
            Path::new("/missing.gguf"),
            "system",
            "transcript",
            &cancelled,
            Duration::from_secs(5),
        )
        .await;
        assert_eq!(result, Err("boom".into()));

        let (_directory, binary) = script("cat >/dev/null\nprintf 'not json'");
        let result = run_with_limits(
            &binary,
            Path::new("/missing.gguf"),
            "system",
            "transcript",
            &cancelled,
            Duration::from_secs(5),
        )
        .await;
        assert!(result.unwrap_err().contains("invalid data"));
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn reports_nonzero_exit_and_oversized_output() {
        let (_directory, binary) = script("cat >/dev/null\nprintf '{\"text\":\"ok\"}'\nexit 3");
        let cancelled = AtomicBool::new(false);
        let result = run_with_limits(
            &binary,
            Path::new("/missing.gguf"),
            "system",
            "transcript",
            &cancelled,
            Duration::from_secs(5),
        )
        .await;
        assert!(result.unwrap_err().contains("stopped unexpectedly"));

        let (_directory, binary) =
            script("cat >/dev/null\nhead -c 200000 /dev/zero | tr '\\0' 'a'");
        let result = run_with_limits(
            &binary,
            Path::new("/missing.gguf"),
            "system",
            "transcript",
            &cancelled,
            Duration::from_secs(5),
        )
        .await;
        assert!(result.unwrap_err().contains("too large"));
    }

    #[cfg(unix)]
    #[tokio::test]
    async fn stops_a_sidecar_on_timeout_and_cancel() {
        let (_directory, binary) = script("cat >/dev/null\nsleep 5");
        let cancelled = AtomicBool::new(false);
        let result = run_with_limits(
            &binary,
            Path::new("/missing.gguf"),
            "system",
            "transcript",
            &cancelled,
            Duration::from_millis(100),
        )
        .await;
        assert!(result.unwrap_err().contains("took too long"));

        let (_directory, binary) = script("cat >/dev/null\nsleep 5");
        let cancelled = Arc::new(AtomicBool::new(false));
        let signal = cancelled.clone();
        tokio::spawn(async move {
            tokio::time::sleep(Duration::from_millis(100)).await;
            signal.store(true, Ordering::Relaxed);
        });
        let result = run_with_limits(
            &binary,
            Path::new("/missing.gguf"),
            "system",
            "transcript",
            &cancelled,
            Duration::from_secs(5),
        )
        .await;
        assert_eq!(result, Err("cancelled".into()));
    }

    #[cfg(target_os = "linux")]
    #[tokio::test]
    async fn leaves_no_sidecar_process_after_a_timeout() {
        let directory = tempfile::tempdir().unwrap();
        let pidfile = directory.path().join("pid");
        let binary = directory.path().join("voicewright-cleanup");
        std::fs::write(
            &binary,
            format!(
                "#!/bin/sh\ncat >/dev/null\necho $$ > '{}'\nsleep 5\n",
                pidfile.display()
            ),
        )
        .unwrap();
        {
            use std::os::unix::fs::PermissionsExt;
            let mut permissions = std::fs::metadata(&binary).unwrap().permissions();
            permissions.set_mode(0o755);
            std::fs::set_permissions(&binary, permissions).unwrap();
        }
        let cancelled = AtomicBool::new(false);
        let result = run_with_limits(
            &binary,
            Path::new("/missing.gguf"),
            "system",
            "transcript",
            &cancelled,
            Duration::from_millis(200),
        )
        .await;
        assert!(result.is_err());
        let pid = std::fs::read_to_string(&pidfile).unwrap().trim().to_owned();
        tokio::time::sleep(Duration::from_millis(100)).await;
        assert!(
            !Path::new(&format!("/proc/{pid}")).exists(),
            "sidecar {pid} still exists"
        );
    }
}
