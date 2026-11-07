use serde::{Deserialize, Serialize};
use std::{
    path::Path,
    process::Stdio,
    sync::atomic::{AtomicBool, Ordering},
    time::Duration,
};
use tokio::io::{AsyncReadExt, AsyncWriteExt};

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
    let request = serde_json::to_vec(&Request {
        model,
        system,
        transcript,
    })
    .map_err(|_| "Invalid cleanup request.")?;
    if request.len() > 256 * 1024 {
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
        .take(128 * 1024 + 1);
    let result = tokio::select! {
        _ = wait_for_cancel(cancelled) => Err("cancelled".into()),
        result = tokio::time::timeout(Duration::from_secs(240), async {
            let ((), bytes) = tokio::try_join!(
                async move { stdin.write_all(&request).await?; stdin.shutdown().await },
                async move {
                    let mut output = Vec::new();
                    stdout.read_to_end(&mut output).await?;
                    Ok(output)
                }
            ).map_err(|_: std::io::Error| "Could not communicate with the cleanup engine.")?;
            if bytes.len() > 128 * 1024 { return Err("The cleanup engine response was too large.".into()); }
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
