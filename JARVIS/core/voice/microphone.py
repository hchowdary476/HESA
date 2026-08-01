"""Microphone diagnostics and callback-based sounddevice audio capture source."""

from __future__ import annotations

import logging
import queue
import sys
import time
from collections.abc import Callable, Iterable

import sounddevice as sd
import speech_recognition as sr

from JARVIS.core.system.utils.service_heartbeat import update_subcomponent_heartbeat
from JARVIS.core.voice.voice_calibration import build_calibration_recommendation

logger = logging.getLogger("jarvis.audio")


# ── Host API auto-selection ──────────────────────────────────────────────────
# Preference order: WASAPI > DirectSound > MME (Windows).
# On non-Windows platforms the system default is used as-is.
_WINDOWS_HOSTAPI_PREFERENCE = ["Windows WASAPI", "Windows DirectSound", "MME"]


def _log_all_input_devices() -> None:
    """Enumerate and log every input device and host API for diagnostics."""
    try:
        host_apis = sd.query_hostapis()
        devices = sd.query_devices()
        logger.info("[VOICE] === Audio Device Enumeration ===")
        for idx, ha in enumerate(host_apis):
            logger.info("[VOICE]   Host API %d: %s (default input device: %s)", idx, ha["name"], ha.get("default_input_device", "none"))
        for idx, dev in enumerate(devices):
            if dev["max_input_channels"] > 0:
                ha_name = host_apis[dev["hostapi"]]["name"] if dev["hostapi"] < len(host_apis) else "?"
                logger.info(
                    "[VOICE]   Input Device %d: '%s' [%s] channels=%d samplerate=%.0f",
                    idx,
                    dev["name"],
                    ha_name,
                    dev["max_input_channels"],
                    dev["default_samplerate"],
                )
        logger.info("[VOICE] === End Device Enumeration ===")
    except Exception as exc:
        logger.warning("[VOICE] Could not enumerate audio devices: %s", exc)


def _resolve_best_input_device(requested_device: int | None = None) -> tuple[int | None, str]:
    """Return (device_index, host_api_name) for the best available input device.

    Strategy:
    1. If a specific device_index was requested, use it directly.
    2. On Windows, walk the preference list (WASAPI > DirectSound > MME)
       and pick the first host API that has a valid default input device.
    3. Fallback: return (None, 'system-default') to let PortAudio decide.
    """
    if requested_device is not None:
        try:
            dev_info = sd.query_devices(requested_device)
            ha_info = sd.query_hostapis(dev_info["hostapi"])
            logger.info("[VOICE] Using explicitly requested device %d '%s' [%s]", requested_device, dev_info["name"], ha_info["name"])
            return (requested_device, ha_info["name"])
        except Exception as exc:
            logger.warning("[VOICE] Requested device %d is invalid (%s), falling back to auto-select", requested_device, exc)

    if sys.platform == "win32":
        try:
            host_apis = sd.query_hostapis()
            devices = sd.query_devices()

            for preferred_name in _WINDOWS_HOSTAPI_PREFERENCE:
                for ha_idx, ha in enumerate(host_apis):
                    if preferred_name.lower() not in ha["name"].lower():
                        continue
                    # Find an input device on this host API
                    default_dev = ha.get("default_input_device", -1)
                    if default_dev is not None and default_dev >= 0:
                        dev = devices[default_dev]
                        if dev["max_input_channels"] > 0:
                            logger.info(
                                "[VOICE] Auto-selected device %d '%s' on preferred host API '%s'", default_dev, dev["name"], ha["name"]
                            )
                            return (default_dev, ha["name"])
                    # No default — look for any input device on this host API
                    for dev_idx, dev in enumerate(devices):
                        if dev["hostapi"] == ha_idx and dev["max_input_channels"] > 0:
                            logger.info("[VOICE] Auto-selected device %d '%s' on preferred host API '%s'", dev_idx, dev["name"], ha["name"])
                            return (dev_idx, ha["name"])
        except Exception as exc:
            logger.warning("[VOICE] Host API auto-selection failed (%s), using system default", exc)

    logger.info("[VOICE] Using system-default input device (no host API preference applied)")
    return (None, "system-default")


def _try_open_input_stream(*, samplerate, channels, dtype, blocksize, device, callback, **extra_kwargs):
    """Attempt to open an sd.InputStream, trying the resolved device first,
    then falling back through all available host APIs on failure.

    Returns the opened (and started) sd.InputStream, or raises if all fail.
    """
    errors = {}

    # First attempt: the resolved/requested device
    try:
        stream = sd.InputStream(
            samplerate=samplerate,
            channels=channels,
            dtype=dtype,
            blocksize=blocksize,
            device=device,
            callback=callback,
            **extra_kwargs,
        )
        stream.start()
        dev_info = sd.query_devices(device) if device is not None else {}
        logger.info("[VOICE] InputStream opened successfully on device=%s '%s'", device, dev_info.get("name", "system-default"))
        return stream
    except Exception as exc:
        errors[f"device={device}"] = str(exc)
        logger.warning("[VOICE] Primary device %s failed: %s — trying fallback strategies", device, exc)

    # Second attempt: if WASAPI rejected our sample rate, try the device's native rate
    if device is not None:
        try:
            dev_info = sd.query_devices(device)
            native_rate = dev_info.get("default_samplerate")
            if native_rate and native_rate != samplerate:
                logger.info("[VOICE] Retrying device %s at native sample rate %.0f Hz", device, native_rate)
                stream = sd.InputStream(
                    samplerate=native_rate,
                    channels=channels,
                    dtype=dtype,
                    blocksize=blocksize,
                    device=device,
                    callback=callback,
                    **extra_kwargs,
                )
                stream.start()
                logger.info(
                    "[VOICE] InputStream opened on device=%s '%s' at native %.0f Hz", device, dev_info.get("name", "?"), native_rate
                )
                return stream
        except Exception as exc:
            errors[f"device={device} (native_rate)"] = str(exc)
            logger.warning("[VOICE] Native rate retry on device %s also failed: %s", device, exc)

    # Fallback: iterate all host APIs and try each default input device
    try:
        host_apis = sd.query_hostapis()
        devices_list = sd.query_devices()
        tried_devices = {device}

        for ha_idx, ha in enumerate(host_apis):
            fallback_dev = ha.get("default_input_device", -1)
            if fallback_dev is None or fallback_dev < 0 or fallback_dev in tried_devices:
                continue
            if devices_list[fallback_dev]["max_input_channels"] <= 0:
                continue
            tried_devices.add(fallback_dev)
            # Try requested rate first, then native rate
            rates_to_try = [samplerate]
            native = devices_list[fallback_dev].get("default_samplerate")
            if native and native != samplerate:
                rates_to_try.append(native)
            for rate in rates_to_try:
                try:
                    stream = sd.InputStream(
                        samplerate=rate,
                        channels=channels,
                        dtype=dtype,
                        blocksize=blocksize,
                        device=fallback_dev,
                        callback=callback,
                        **extra_kwargs,
                    )
                    stream.start()
                    logger.info(
                        "[VOICE] InputStream opened on FALLBACK device %d '%s' [%s] at %.0f Hz",
                        fallback_dev,
                        devices_list[fallback_dev]["name"],
                        ha["name"],
                        rate,
                    )
                    return stream
                except Exception as fb_err:
                    errors[f"device={fallback_dev} ({ha['name']}, {rate}Hz)"] = str(fb_err)
                    logger.warning("[VOICE] Fallback device %d [%s] at %.0f Hz failed: %s", fallback_dev, ha["name"], rate, fb_err)
    except Exception as enum_err:
        logger.error("[VOICE] Failed to enumerate fallback devices: %s", enum_err)

    # All attempts failed — log full device table for diagnostics
    _log_all_input_devices()
    err_summary = "; ".join(f"{k}: {v}" for k, v in errors.items())
    raise sd.PortAudioError(f"All audio input devices failed. Tried: {err_summary}")


class SoundDeviceMicrophone(sr.AudioSource):
    """
    Custom speech_recognition AudioSource that captures audio using sounddevice callbacks and queues.
    Eliminates all native PyAudio dependencies and prevents process blocks.
    """

    def __init__(self, device_index=None, sample_rate=16000, chunk_size=1024):
        self.device_index = device_index
        self.SAMPLE_RATE = sample_rate
        self.SAMPLE_WIDTH = 2  # 16-bit PCM
        self.format = self.SAMPLE_WIDTH
        self.CHUNK = chunk_size
        self.stream = None
        self.sd_stream = None
        self.queue = None
        self._buffer = b""
        self._data_received_logged = False

    def __enter__(self):
        self.queue = queue.Queue()
        self._buffer = b""
        self._data_received_logged = False

        def callback(indata, frames, time_info, status):
            if status:
                logger.warning(f"[VOICE] Audio input status: {status}")

            # indata is a numpy array of shape (frames, channels), dtype int16
            raw_bytes = indata.tobytes()
            if self.queue is not None:
                self.queue.put(raw_bytes)

            # Print and log on first actual chunk received
            if not self._data_received_logged:
                print("[VOICE] MIC DATA RECEIVED")
                logger.info("MIC DATA RECEIVED")
                self._data_received_logged = True

            # Update audio_stream heartbeat (throttled to once every 5 seconds to prevent callback overflows)
            now = time.time()
            if not hasattr(self, "_last_hb_time") or now - self._last_hb_time > 5.0:
                self._last_hb_time = now
                update_subcomponent_heartbeat(
                    "audio_stream",
                    status="healthy",
                    details={"frames": frames, "time": time_info.inputBufferAdcTime, "data_received": True},
                )

        # Resolve the best input device (prefers WASAPI on Windows)
        resolved_device, host_api_name = _resolve_best_input_device(self.device_index)

        self.sd_stream = _try_open_input_stream(
            samplerate=self.SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=self.CHUNK,
            device=resolved_device,
            callback=callback,
        )
        self.stream = self
        print(f"[VOICE] MIC STARTED (host_api={host_api_name})")
        logger.info("MIC STARTED (host_api=%s, device=%s)", host_api_name, resolved_device)

        # Publish initial healthy heartbeat
        update_subcomponent_heartbeat("audio_stream", status="healthy")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.sd_stream:
            try:
                self.sd_stream.stop()
                self.sd_stream.close()
            except Exception:
                pass
        self.sd_stream = None
        self.stream = None
        self.queue = None
        self._buffer = b""
        update_subcomponent_heartbeat("audio_stream", status="stopped")

    def read(self, num_frames):
        needed_bytes = num_frames * self.SAMPLE_WIDTH
        while len(self._buffer) < needed_bytes:
            if self.queue is None:
                return b""
            try:
                # Block until we get a chunk from the callback queue
                chunk = self.queue.get(timeout=1.0)
                self._buffer += chunk
            except queue.Empty:
                if not self._buffer:
                    return b"\x00" * needed_bytes
                break

        ret = self._buffer[:needed_bytes]
        self._buffer = self._buffer[needed_bytes:]
        return ret

    @staticmethod
    def list_microphone_names():
        try:
            return [d["name"] for d in sd.query_devices() if d["max_input_channels"] > 0]
        except Exception:
            return []


Probe = Callable[[], bool]


def _default_microphone_probe() -> bool:
    try:
        return bool(SoundDeviceMicrophone.list_microphone_names())
    except Exception:
        return False


def microphone_available(probe: Probe | None = None) -> bool:
    try:
        return bool((probe or _default_microphone_probe)())
    except Exception:
        return False


def build_microphone_status(probe: Probe | None = None) -> dict[str, object]:
    available = microphone_available(probe)
    return {
        "available": available,
        "status": "ready" if available else "unavailable",
        "message": "[INFO] Microphone ready." if available else "[WARN] Microphone unavailable. Voice input disabled.",
    }


def build_voice_calibration_status(samples: Iterable[float], *, safety_margin: int = 100) -> dict[str, object]:
    return dict(build_calibration_recommendation(list(samples), safety_margin=safety_margin))
