"""Speech recognition helpers with an optional offline Vosk fallback."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from json import JSONDecodeError
from pathlib import Path

import speech_recognition as sr
from dotenv import load_dotenv

try:
    load_dotenv(".env")
    # Resolve project root relative to this file
    proj_root = Path(__file__).resolve().parents[3]
    load_dotenv(proj_root / ".env")
except Exception:
    pass


def _candidate_model_roots() -> list[Path]:
    candidates = []

    env_path = os.getenv("JARVIS_VOSK_MODEL_PATH") or os.getenv("VOSK_MODEL_PATH")
    if env_path:
        candidates.append(Path(env_path))

    home = Path.home()
    candidates.extend(
        [
            home / ".cache" / "vosk",
            home / ".JARVIS" / "vosk_models",
            home / ".JARVIS" / "vosk_model",
            home / "AppData" / "Local" / "Open.Jarvis" / "vosk_models",
            Path(__file__).resolve().parent / "model",
            Path(__file__).resolve().parent / "models" / "vosk-model-small-en-us-0.15",
        ]
    )

    return candidates


def _looks_like_model(path: Path) -> bool:
    if not path.exists() or not path.is_dir():
        return False
    return any((path / marker).exists() for marker in ["am", "graph", "conf"])


@lru_cache(maxsize=1)
def resolve_vosk_model_path() -> Path | None:
    """Resolve a usable Vosk model directory if one is available."""

    for root in _candidate_model_roots():
        if root.is_dir() and (root / "am").exists():
            return root
        if root.is_dir():
            for child in root.iterdir():
                if _looks_like_model(child):
                    return child
    return None


@lru_cache(maxsize=1)
def _load_vosk_model():
    model_path = resolve_vosk_model_path()
    if model_path is None:
        return None

    try:
        from vosk import Model

        return Model(str(model_path))
    except (ImportError, OSError, RuntimeError, ValueError):
        return None


def offline_stt_available() -> bool:
    """Return True when an offline model can be loaded."""

    return resolve_vosk_model_path() is not None


def transcribe_audio_offline(audio: sr.AudioData) -> str | None:
    """Transcribe audio using Vosk when available."""

    model = _load_vosk_model()
    if model is None:
        return None

    try:
        from vosk import KaldiRecognizer

        recognizer = KaldiRecognizer(model, 16000)
        recognizer.AcceptWaveform(audio.get_raw_data(convert_rate=16000, convert_width=2))
        result = json.loads(recognizer.FinalResult())
        text = result.get("text", "").strip()
        return text or None
    except (ImportError, OSError, RuntimeError, ValueError, JSONDecodeError):
        return None


def transcribe_audio(
    recognizer: sr.Recognizer,
    audio: sr.AudioData,
    language: str = "en-US",
    prefer_offline: bool = False,
) -> str | None:
    """
    Unified STT fallback chain with complete traceback logging and backend diagnostics.
    Priority order: Whisper tiny.en → Vosk → Google STT → OpenAI Whisper API
    """
    import io
    import time as _time
    import traceback
    import wave

    from JARVIS.core.system.utils.jarvis_logging import get_file_logger

    stt_logger = get_file_logger("jarvis.stt")
    _voice_logger = get_file_logger("jarvis.voice")

    from JARVIS.core.system.utils.service_heartbeat import update_subcomponent_heartbeat

    update_subcomponent_heartbeat(
        "speech_backend", status="healthy", details={"language": language, "audio_len_bytes": len(audio.frame_data)}
    )

    # Prepare diagnostic info
    dur = len(audio.frame_data) / (audio.sample_rate * audio.sample_width) if audio.sample_rate and audio.sample_width else 0.0
    sr_rate = audio.sample_rate

    def log_stt_failure(backend, exc):
        exc_type = type(exc).__name__
        exc_msg = str(exc)
        tb_str = traceback.format_exc()
        _voice_logger.error("[STT] FAILED backend=%s error=%s: %s", backend, exc_type, exc_msg)
        stt_logger.error(
            "[STT] FAILED backend=%s lang=%s dur=%.2fs error=%s: %s\nTraceback:\n%s",
            backend,
            language,
            dur,
            exc_type,
            exc_msg,
            tb_str,
        )
        print(f"[STT] FAILED backend={backend} error={exc_type}: {exc_msg}", flush=True)

    # Determine backend trial order:
    # 1. Faster-Whisper, 2. Whisper, 3. Vosk, 4. Google STT, 5. OpenAI Whisper API, 6. Groq
    order = ["FASTER_WHISPER", "WHISPER", "VOSK", "GOOGLE", "OPENAI_WHISPER", "GROQ"]

    stt_logger.info("[STT] STARTED lang=%s dur=%.2fs order=%s", language, dur, order)
    print(f"[VOICE] STT STARTED — order={order}", flush=True)
    _voice_logger.info("[VOICE] STT STARTED — backend selection in progress")

    # Execute backend trial loop
    for backend in order:
        _backend_start = _time.perf_counter()
        stt_logger.info("[STT] TRYING %s", backend)
        print(f"[STT] TRYING {backend}", flush=True)
        try:
            if backend == "FASTER_WHISPER":
                try:
                    from JARVIS.core.voice.faster_whisper_engine import get_faster_whisper_engine

                    fw_engine = get_faster_whisper_engine()
                    result = fw_engine.transcribe(audio, language=language)
                    if result and result.get("text"):
                        text = result["text"]
                        _lat = (_time.perf_counter() - _backend_start) * 1000
                        stt_logger.info('[STT] SUCCESS backend=FASTER_WHISPER latency=%.0fms result="%s"', _lat, text[:80])
                        _voice_logger.info("[VOICE] FASTER_WHISPER transcribed: '%s'", text)
                        print(f"[STT] USING FASTER_WHISPER — '{text}'", flush=True)
                        return text
                except Exception as e:
                    log_stt_failure(backend, e)
                    continue

            elif backend == "VOSK":
                if not offline_stt_available():
                    stt_logger.warning("[STT] VOSK offline model missing or unavailable — skipping")
                    _voice_logger.warning("[VOICE] VOSK offline model is missing or unavailable.")
                    continue
                print("[STT] USING VOSK", flush=True)
                text = transcribe_audio_offline(audio)
                if text:
                    _lat = (_time.perf_counter() - _backend_start) * 1000
                    stt_logger.info('[STT] SUCCESS backend=VOSK latency=%.0fms result="%s"', _lat, text[:80])
                    _voice_logger.info("[VOICE] USING BACKEND: VOSK — '%s'", text)
                    return text

            elif backend == "WHISPER":
                # Check for local whisper library
                try:
                    import whisper as _whisper_lib
                except ImportError:
                    logger.warning("[VOICE] Local Whisper library (openai-whisper) not installed.")
                    continue

                # Prefer tiny.en (already downloaded, fast) — fall back to base
                _whisper_model_name = "tiny.en"
                import os as _os

                _whisper_cache = _os.path.join(_os.path.expanduser("~"), ".cache", "whisper")
                _tiny_path = _os.path.join(_whisper_cache, "tiny.en.pt")
                if not _os.path.exists(_tiny_path):
                    # tiny.en not found — try base.en, then base
                    for _candidate in ("base.en.pt", "base.pt", "small.en.pt"):
                        if _os.path.exists(_os.path.join(_whisper_cache, _candidate)):
                            _whisper_model_name = _candidate.replace(".pt", "")
                            break
                    else:
                        logger.warning("[VOICE] No Whisper model cached. Skipping WHISPER backend.")
                        continue

                print("[STT] USING WHISPER", flush=True)
                print(f"[VOICE] USING BACKEND: WHISPER ({_whisper_model_name})", flush=True)
                _voice_logger.info("[VOICE] USING BACKEND: WHISPER (%s)", _whisper_model_name)

                # Feed raw float32 numpy array directly to whisper — bypasses ffmpeg subprocess.
                try:
                    import numpy as _np

                    # Convert PCM int16 → float32 in [-1, 1]
                    _pcm = _np.frombuffer(audio.frame_data, dtype=_np.int16).astype(_np.float32) / 32768.0
                    # Resample to 16 kHz if needed (whisper expects exactly 16000 Hz)
                    if audio.sample_rate != 16000:
                        import math

                        _ratio = 16000 / audio.sample_rate
                        _new_len = int(len(_pcm) * _ratio)
                        _pcm = _np.interp(
                            _np.linspace(0, len(_pcm) - 1, _new_len),
                            _np.arange(len(_pcm)),
                            _pcm,
                        ).astype(_np.float32)
                    _model = _whisper_lib.load_model(_whisper_model_name)
                    res = _model.transcribe(_pcm, language="en", fp16=False)
                    text = res.get("text", "").strip()
                    if text:
                        _lat = (_time.perf_counter() - _backend_start) * 1000
                        stt_logger.info('[STT] SUCCESS backend=WHISPER latency=%.0fms result="%s"', _lat, text[:80])
                        _voice_logger.info("[VOICE] WHISPER transcribed: '%s'", text)
                        return text
                    _voice_logger.warning("[VOICE] WHISPER returned empty text — skipping")
                except ImportError:
                    _voice_logger.warning("[VOICE] numpy not available — cannot use numpy-mode whisper")

            elif backend == "GOOGLE":
                print("[STT] USING GOOGLE", flush=True)
                try:
                    text = recognizer.recognize_google(audio, language=language)
                except sr.UnknownValueError:
                    _voice_logger.warning("[VOICE] GOOGLE: UnknownValueError — no speech recognised")
                    stt_logger.warning("[STT] FAILED backend=GOOGLE reason=UnknownValueError")
                    continue
                if text:
                    _lat = (_time.perf_counter() - _backend_start) * 1000
                    stt_logger.info('[STT] SUCCESS backend=GOOGLE latency=%.0fms result="%s"', _lat, text[:80])
                    _voice_logger.info("[VOICE] GOOGLE transcribed: '%s'", text)
                    return text

            elif backend == "OPENAI_WHISPER":
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    _voice_logger.warning("[VOICE] OPENAI_API_KEY not found — skipping OPENAI_WHISPER backend")
                    stt_logger.warning("[STT] SKIP backend=OPENAI_WHISPER reason=no_api_key")
                    continue
                print("[STT] USING OPENAI WHISPER", flush=True)
                try:
                    import requests

                    wav_io = io.BytesIO()
                    with wave.open(wav_io, "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(audio.sample_width)
                        wf.setframerate(audio.sample_rate)
                        wf.writeframes(audio.frame_data)
                    wav_io.seek(0)
                    wav_io.name = "audio.wav"
                    files = {"file": ("audio.wav", wav_io, "audio/wav")}
                    data = {"model": "whisper-1", "language": language[:2]}
                    headers = {"Authorization": f"Bearer {api_key}"}
                    res = requests.post(
                        "https://api.openai.com/v1/audio/transcriptions", headers=headers, files=files, data=data, timeout=15.0
                    )
                    res.raise_for_status()
                    text = res.json().get("text", "").strip()
                    if text:
                        _lat = (_time.perf_counter() - _backend_start) * 1000
                        stt_logger.info('[STT] SUCCESS backend=OPENAI_WHISPER latency=%.0fms result="%s"', _lat, text[:80])
                        _voice_logger.info("[VOICE] OPENAI WHISPER transcribed: '%s'", text)
                        return text
                except Exception as e:
                    log_stt_failure(backend, e)
                    continue

            elif backend == "GROQ":
                # Verify Groq setup
                api_key = os.getenv("GROQ_API_KEY")
                if not api_key:
                    logger.warning("[VOICE] GROQ_API_KEY not found in environment.")
                    continue
                try:
                    from groq import Groq
                except ImportError:
                    logger.warning("[VOICE] Groq library not installed.")
                    continue

                print("[VOICE] USING BACKEND: GROQ")
                import httpx

                client = Groq(api_key=api_key, http_client=httpx.Client(verify=False))

                # In-memory WAV file creation
                wav_io = io.BytesIO()
                with wave.open(wav_io, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(audio.sample_width)
                    wf.setframerate(audio.sample_rate)
                    wf.writeframes(audio.frame_data)
                wav_io.seek(0)
                wav_io.name = "audio.wav"

                translation = client.audio.transcriptions.create(
                    file=wav_io,
                    model="whisper-large-v3",
                    language=language[:2],
                )
                if isinstance(translation, str):
                    text = translation.strip()
                elif hasattr(translation, "text"):
                    text = translation.text.strip()
                elif isinstance(translation, dict):
                    text = translation.get("text", "").strip()
                else:
                    text = str(translation).strip()

                if text:
                    return text

        except sr.UnknownValueError:
            stt_logger.debug("[STT] %s: UnknownValueError (no recognisable speech)", backend)
            _voice_logger.debug("[VOICE] %s: UnknownValueError (no recognisable speech)", backend)
            continue
        except Exception as e:
            if "JSONDecodeError" in type(e).__name__ or "Expecting value" in str(e):
                _voice_logger.warning("[VOICE] %s: Empty HTTP response from Google STT (network issue)", backend)
                stt_logger.warning("[STT] %s: Empty HTTP response — network issue", backend)
            else:
                log_stt_failure(backend, e)
            continue

    stt_logger.error("[STT] ALL BACKENDS FAILED — no transcription produced")
    print("[VOICE] ALL STT BACKENDS FAILED TO TRANSCRIBE AUDIO", flush=True)
    return None


def recognition_mode() -> str:
    """Expose the currently available recognition mode for health checks."""

    return "offline" if offline_stt_available() else "online"
