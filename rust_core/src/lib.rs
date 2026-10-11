//! IRIS High-Performance Audio Processing Engine in Rust
//! Exports C-compatible ABI functions for fast audio RMS energy calculation,
//! silence thresholding, and ring-buffer streaming.

use std::slice;

/// Computes the Root-Mean-Square (RMS) energy level of 16-bit PCM audio samples.
/// Used for real-time Voice Activity Detection (VAD) with zero Python interpreter overhead.
#[no_mangle]
pub extern "C" fn calculate_pcm16_rms(buffer: *const i16, len: usize) -> f32 {
    if buffer.is_null() || len == 0 {
        return 0.0;
    }

    let samples = unsafe { slice::from_raw_parts(buffer, len) };
    let mut sum_sq: f64 = 0.0;

    for &sample in samples {
        let val = sample as f64;
        sum_sq += val * val;
    }

    let mean_sq = sum_sq / (len as f64);
    mean_sq.sqrt() as f32
}

/// Applies noise floor suppression filter directly to 16-bit audio in-place.
#[no_mangle]
pub extern "C" fn apply_noise_gate(buffer: *mut i16, len: usize, threshold: i16) -> usize {
    if buffer.is_null() || len == 0 {
        return 0;
    }

    let samples = unsafe { slice::from_raw_parts_mut(buffer, len) };
    let mut gated_count = 0;

    for sample in samples.iter_mut() {
        if sample.abs() < threshold {
            *sample = 0;
            gated_count += 1;
        }
    }

    gated_count
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_calculate_rms() {
        let samples: [i16; 4] = [1000, -1000, 1000, -1000];
        let rms = calculate_pcm16_rms(samples.as_ptr(), samples.len());
        assert!((rms - 1000.0).abs() < 1e-4);
    }

    #[test]
    fn test_noise_gate() {
        let mut samples: [i16; 4] = [50, -200, 20, 500];
        let gated = apply_noise_gate(samples.as_mut_ptr(), samples.len(), 100);
        assert_eq!(gated, 2);
        assert_eq!(samples[0], 0);
        assert_eq!(samples[2], 0);
    }
}
