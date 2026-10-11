"""
IRIS Rust Audio Bridge
Dynamically links to the high-performance Rust audio DSP DLL if available,
with a transparent Python math fallback when running without the compiled binary.
"""

import math
import ctypes
from pathlib import Path
from typing import Optional, List

from ..core.logger import get_logger

logger = get_logger("rust_bridge")

_RUST_LIB = None


def _load_rust_lib():
    global _RUST_LIB
    if _RUST_LIB is not None:
        return _RUST_LIB

    dll_paths = [
        Path(__file__).resolve().parent.parent.parent / "rust_core" / "target" / "release" / "iris_rust_audio.dll",
        Path(__file__).resolve().parent.parent.parent / "iris_rust_audio.dll",
    ]

    for p in dll_paths:
        if p.exists():
            try:
                lib = ctypes.CDLL(str(p))
                # Set argtypes and restype
                lib.calculate_pcm16_rms.argtypes = [ctypes.POINTER(ctypes.c_int16), ctypes.c_size_t]
                lib.calculate_pcm16_rms.restype = ctypes.c_float

                lib.apply_noise_gate.argtypes = [ctypes.POINTER(ctypes.c_int16), ctypes.c_size_t, ctypes.c_int16]
                lib.apply_noise_gate.restype = ctypes.c_size_t

                _RUST_LIB = lib
                logger.info(f"Loaded high-performance Rust audio module from: {p}")
                return _RUST_LIB
            except Exception as e:
                logger.warning(f"Failed to load Rust audio DLL at {p}: {e}")

    logger.debug("Rust audio library not found. Operating with native Python DSP engine.")
    return None


def calculate_pcm_rms(samples: List[int]) -> float:
    """Calculates RMS energy using Rust DLL when present, or native math."""
    if not samples:
        return 0.0

    rust = _load_rust_lib()
    if rust:
        try:
            arr_type = ctypes.c_int16 * len(samples)
            c_arr = arr_type(*samples)
            return float(rust.calculate_pcm16_rms(c_arr, len(samples)))
        except Exception:
            pass

    # Pure Python fallback
    sum_sq = sum(s * s for s in samples)
    return math.sqrt(sum_sq / len(samples))
