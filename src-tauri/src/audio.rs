use cpal::{
    traits::{DeviceTrait, HostTrait, StreamTrait},
    Device, FromSample, SampleFormat, SizedSample,
};
use serde::Serialize;
use std::{
    sync::{
        atomic::{AtomicBool, AtomicU32, Ordering},
        Arc, Mutex,
    },
    thread,
    time::{Duration, Instant},
};

pub const TARGET_RATE: usize = 16_000;
const LIMIT: Duration = Duration::from_secs(120);

#[derive(Serialize)]
pub struct InputDevice {
    id: String,
    label: String,
}

pub fn devices() -> Result<Vec<InputDevice>, String> {
    Ok(cpal::default_host()
        .input_devices()
        .map_err(|_| "Could not list microphones.".to_string())?
        .filter_map(|device| {
            Some(InputDevice {
                id: device.id().ok()?.to_string(),
                label: device.description().ok()?.name().to_owned(),
            })
        })
        .collect())
}

fn select_device(id: Option<&str>) -> Result<Device, String> {
    let host = cpal::default_host();
    if let Some(id) = id {
        return host
            .input_devices()
            .map_err(|_| "Could not list microphones.")?
            .find(|device| device.id().is_ok_and(|current| current.to_string() == id))
            .ok_or_else(|| "The selected microphone is unavailable.".into());
    }
    host.default_input_device()
        .ok_or_else(|| "No default microphone is available.".into())
}

#[derive(Default)]
pub struct Capture {
    pub stop: AtomicBool,
    pub cancelled: AtomicBool,
    pub level: AtomicU32,
}

fn input<T>(
    device: &Device,
    config: &cpal::StreamConfig,
    frames: Arc<Mutex<Vec<f32>>>,
    control: Arc<Capture>,
    fault: Arc<AtomicBool>,
) -> Result<cpal::Stream, cpal::BuildStreamError>
where
    T: SizedSample,
    f32: FromSample<T>,
{
    let channels = usize::from(config.channels);
    let max_samples = config.sample_rate as usize * LIMIT.as_secs() as usize;
    device.build_input_stream(
        config,
        move |data: &[T], _| {
            if control.stop.load(Ordering::Relaxed) {
                return;
            }
            let Ok(mut frames) = frames.lock() else {
                return;
            };
            let remaining = max_samples.saturating_sub(frames.len());
            let start = frames.len();
            frames.extend(data.chunks_exact(channels).take(remaining).map(|frame| {
                frame
                    .iter()
                    .map(|sample| sample.to_sample::<f32>())
                    .sum::<f32>()
                    / channels as f32
            }));
            let level = frames[start..]
                .iter()
                .fold(0.0_f32, |peak, value| peak.max(value.abs()));
            control.level.store(level.to_bits(), Ordering::Relaxed);
        },
        move |_| {
            fault.store(true, Ordering::Relaxed);
        },
        None,
    )
}

pub fn record(id: Option<&str>, control: Arc<Capture>) -> Result<Vec<f32>, String> {
    let device = select_device(id)?;
    let supported = device
        .default_input_config()
        .map_err(|_| "Could not configure the microphone.")?;
    let config = supported.config();
    let rate = config.sample_rate as usize;
    if config.channels == 0 || !(8_000..=384_000).contains(&rate) {
        return Err("The microphone uses an unsupported audio format.".into());
    }
    let frames = Arc::new(Mutex::new(Vec::with_capacity(rate * 2)));
    let fault = Arc::new(AtomicBool::new(false));
    let stream = match supported.sample_format() {
        SampleFormat::F32 => input::<f32>(
            &device,
            &config,
            frames.clone(),
            control.clone(),
            fault.clone(),
        ),
        SampleFormat::F64 => input::<f64>(
            &device,
            &config,
            frames.clone(),
            control.clone(),
            fault.clone(),
        ),
        SampleFormat::I16 => input::<i16>(
            &device,
            &config,
            frames.clone(),
            control.clone(),
            fault.clone(),
        ),
        SampleFormat::U16 => input::<u16>(
            &device,
            &config,
            frames.clone(),
            control.clone(),
            fault.clone(),
        ),
        SampleFormat::I32 => input::<i32>(
            &device,
            &config,
            frames.clone(),
            control.clone(),
            fault.clone(),
        ),
        SampleFormat::U32 => input::<u32>(
            &device,
            &config,
            frames.clone(),
            control.clone(),
            fault.clone(),
        ),
        _ => return Err("The microphone uses an unsupported sample format.".into()),
    }
    .map_err(|_| "Could not open the microphone. Check device permissions.")?;
    stream
        .play()
        .map_err(|_| "Could not start the microphone.")?;
    let started = Instant::now();
    while !control.stop.load(Ordering::Relaxed)
        && !fault.load(Ordering::Relaxed)
        && started.elapsed() < LIMIT
    {
        thread::sleep(Duration::from_millis(12));
    }
    drop(stream);
    control.level.store(0, Ordering::Relaxed);
    if control.cancelled.load(Ordering::Relaxed) {
        return Err("cancelled".into());
    }
    if fault.load(Ordering::Relaxed) {
        return Err("The microphone disconnected during recording.".into());
    }
    let frames = frames
        .lock()
        .map_err(|_| "Could not read captured audio.")?;
    Ok(resample(&frames, rate))
}

fn resample(samples: &[f32], rate: usize) -> Vec<f32> {
    if rate == TARGET_RATE {
        return samples.to_vec();
    }
    (0..samples.len() * TARGET_RATE / rate)
        .map(|index| {
            let start = index * rate / TARGET_RATE;
            let end = ((index + 1) * rate / TARGET_RATE).max(start + 1);
            samples[start..end].iter().sum::<f32>() / (end - start) as f32
        })
        .collect()
}

pub fn has_voice(samples: &[f32]) -> bool {
    samples.len() >= TARGET_RATE / 4
        && samples
            .as_chunks::<{ TARGET_RATE / 50 }>()
            .0
            .iter()
            .filter(|frame| {
                frame.iter().map(|value| value * value).sum::<f32>() / frame.len() as f32
                    > 0.000_025
            })
            .take(4)
            .count()
            == 4
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn downmix_rate_conversion_averages_frames() {
        let output = resample(&[0.0, 0.3, 0.6, 0.3, 0.6, 0.9], 48_000);
        assert!((output[0] - 0.3).abs() < 1e-6 && (output[1] - 0.6).abs() < 1e-6);
        assert_eq!(resample(&[1.0, 0.0], 8_000), vec![1.0, 1.0, 0.0, 0.0]);
    }

    #[test]
    fn rejects_silence_and_taps_but_accepts_sustained_sound() {
        let mut samples = vec![0.0; TARGET_RATE];
        samples[0] = 1.0;
        assert!(!has_voice(&samples));
        samples[1600..3200].fill(0.2);
        assert!(has_voice(&samples));
    }
}
