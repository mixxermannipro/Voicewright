use std::{
    ffi::c_void,
    path::Path,
    sync::atomic::{AtomicBool, Ordering},
};
use whisper_rs::{FullParams, SamplingStrategy, WhisperContext, WhisperContextParameters};

unsafe extern "C" fn abort(user_data: *mut c_void) -> bool {
    // The flag remains alive for the complete synchronous full() call.
    unsafe { &*user_data.cast::<AtomicBool>() }.load(Ordering::Relaxed)
}

pub fn transcribe(
    model: &Path,
    samples: &[f32],
    language: &str,
    vocabulary: &str,
    cancelled: &AtomicBool,
) -> Result<String, String> {
    if cancelled.load(Ordering::Relaxed) {
        return Err("cancelled".into());
    }
    let mut context = WhisperContextParameters::default();
    context.use_gpu(false);
    let model = WhisperContext::new_with_params(model, context)
        .map_err(|_| "Whisper could not load the selected model.".to_string())?;
    let mut state = model
        .create_state()
        .map_err(|_| "Whisper could not allocate recognition state.")?;
    let mut params = FullParams::new(SamplingStrategy::Greedy { best_of: 1 });
    let threads = std::thread::available_parallelism().map_or(1, |n| n.get().min(8)) as i32;
    params.set_n_threads(threads);
    params.set_language(Some(language));
    params.set_translate(false);
    params.set_print_progress(false);
    params.set_print_realtime(false);
    params.set_print_timestamps(false);
    params.set_print_special(false);
    if !vocabulary.trim().is_empty() {
        params.set_initial_prompt(vocabulary);
    }
    unsafe {
        params.set_abort_callback(Some(abort));
        params.set_abort_callback_user_data(std::ptr::from_ref(cancelled).cast_mut().cast());
    }
    state
        .full(params, samples)
        .map_err(|_| "Whisper could not transcribe the recording.")?;
    let mut text = String::new();
    for segment in state.as_iter() {
        text.push_str(
            &segment
                .to_str_lossy()
                .map_err(|_| "Whisper returned unreadable text.")?,
        );
    }
    Ok(text.trim().to_string())
}
