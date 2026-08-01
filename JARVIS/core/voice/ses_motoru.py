"""
VOICE ENGINE - Microsoft Edge TTS
Manages JARVIS speech output with lazy loading for fast startup.
"""

import asyncio
import io
import os
import tempfile
import ctypes
import time
import threading

# Lazy import edge_tts to avoid 1.7s startup penalty
# import edge_tts  # REMOVED - now lazy loaded

from JARVIS.runtime.ui_bridge import send_log, send_state
from JARVIS.core.system.utils.jarvis_logging import get_file_logger

VOICE = "en-GB-RyanNeural"  # Closest to Iron Man JARVIS voice
RATE = "-8%"
PITCH = "-12Hz"

_tts_logger = get_file_logger("jarvis.tts")


def _play_mp3_mci(filepath: str):
    """Play an MP3 file using the Windows MCI interface, with cross-platform fallback."""
    if os.name == 'nt':
        try:
            buf = ctypes.create_unicode_buffer(260)
            ctypes.windll.kernel32.GetShortPathNameW(filepath, buf, 260)
            short_path = buf.value
            
            # Stop and close any previous instance
            ctypes.windll.winmm.mciSendStringW("stop jarvis_tts", None, 0, 0)
            ctypes.windll.winmm.mciSendStringW("close jarvis_tts", None, 0, 0)
            
            # Open, play, and close
            ctypes.windll.winmm.mciSendStringW(f"open {short_path} alias jarvis_tts", None, 0, 0)
            ctypes.windll.winmm.mciSendStringW("play jarvis_tts wait", None, 0, 0)
            ctypes.windll.winmm.mciSendStringW("close jarvis_tts", None, 0, 0)
        except Exception as e:
            print(f"[MCI] Error playing audio: {e}")
            send_log(f"[WARN] MCI player error: {e}")
    else:
        # Non-Windows fallback (e.g. using pygame if imported)
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(filepath)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
        except Exception as e:
            print(f"[Fallback Player] Fallback error: {e}")


class VoiceEngine:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_engine()
            return cls._instance

    def _init_engine(self):
        import queue
        self.queue = queue.Queue()
        self.worker_thread = None
        self.is_running = False
        self.speaking = False
        self.pid = os.getpid()
        self.current_speaker = "en-GB-RyanNeural"
        self.listener_state = "STANDBY"
        
        # Kill duplicate instances is handled via PortManager lock; commenting out to prevent circular SIGTERM loops
        # import sys
        # if any("voice_service" in arg or "voice_engine" in arg for arg in sys.argv):
        #     self.terminate_duplicate_voice_services()
        
        # Start worker thread
        self.start_worker()
        self.write_diagnostics()

    def terminate_duplicate_voice_services(self):
        try:
            import psutil
            current_pid = os.getpid()
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.pid == current_pid:
                        continue
                    cmdline = proc.info.get('cmdline')
                    if cmdline:
                        cmd_str = " ".join(cmdline).lower()
                        if "jarvis.services.voice_service" in cmd_str or "jarvis.services.voice_engine" in cmd_str or "listener_service.py" in cmd_str:
                            proc.terminate()
                            try:
                                proc.wait(timeout=0.5)
                            except Exception:
                                proc.kill()
                except Exception:
                    pass
        except Exception:
            pass

    def start_worker(self):
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def stop(self):
        self.is_running = False
        self.stop_speaking()
        self.write_diagnostics()

    def stop_speaking(self):
        """Stop current audio playback and clear queued speech (for barge-in / interruption)."""
        with self.queue.mutex:
            self.queue.queue.clear()
        self.speaking = False
        if os.name == 'nt':
            try:
                ctypes.windll.winmm.mciSendStringW("stop jarvis_tts", None, 0, 0)
                ctypes.windll.winmm.mciSendStringW("close jarvis_tts", None, 0, 0)
            except Exception:
                pass
        self.write_diagnostics()


    def set_listener_state(self, state: str):
        if self.listener_state == state:
            return
        self.listener_state = state
        self.write_diagnostics()

    def _worker_loop(self):
        while self.is_running:
            try:
                item = self.queue.get(timeout=0.2)
            except Exception:
                continue

            text, event = item
            self.speaking = True
            self.write_diagnostics()

            try:
                from JARVIS.core.system.utils.activity_tracker import set_activity
                set_activity("tts_playback", True)
                try:
                    from JARVIS.core.system.utils.telugu_formatter import format_telugu_response, contains_telugu_script, detect_language
                    from JARVIS.core.memory.memory_short_term import get_short_term

                    last_user_cmd = ""
                    try:
                        for memory_item in reversed(get_short_term()):
                            if memory_item["role"] == "user":
                                last_user_cmd = memory_item["content"]
                                break
                    except Exception:
                        pass

                    text = format_telugu_response(text, last_user_cmd)
                    
                    if contains_telugu_script(text) or detect_language(text) == "telugu":
                        self.current_speaker = "te-IN-MohanNeural"
                    else:
                        self.current_speaker = "en-US-AriaNeural"

                    send_state("SPEAKING", "Voice response active")
                    send_log(f"[SPEAKING] Speaking started: {text[:120]}")
                    print(f"HESA: {text}")
                    print("[VOICE] TTS RESPONSE GENERATED")
                    import logging
                    logging.getLogger("jarvis.voice").info("Voice response generated")
                    logging.getLogger("jarvis.voice").info("TTS RESPONSE GENERATED")
                    
                    self.write_diagnostics()
                    print("[VOICE] TTS STARTED", flush=True)
                    print("[TTS] TTS STARTED", flush=True)
                    logging.getLogger("jarvis.voice").info("[VOICE] TTS STARTED")
                    try:
                        asyncio.run(self._speak_async_direct(text, self.current_speaker))
                        print("[VOICE] TTS COMPLETED", flush=True)
                        print("[TTS] TTS COMPLETED", flush=True)
                        logging.getLogger("jarvis.voice").info("[VOICE] TTS COMPLETED")
                    except Exception as exc:
                        send_log(f"[WARN] Voice output failed: {exc}")
                        logging.getLogger("jarvis.voice").error("[VOICE] TTS FAILED: %s", exc)
                    finally:
                        send_log("[OK] Speaking completed")
                finally:
                    set_activity("tts_playback", False)
            except Exception:
                pass
            finally:
                self.speaking = False
                self.queue.task_done()
                event.set()
                self.write_diagnostics()

    async def _speak_async_direct(self, text: str, voice: str):
        """Try TTS backends in priority order: Edge TTS → pyttsx3 → gTTS → Windows SAPI.
        Logs backend selection, latency, and failures to logs/tts.log.
        Can never silently fail — Windows SAPI is the guaranteed hard fallback.
        """
        import time as _ttime
        from JARVIS.core.voice.pronunciation_engine import get_pronunciation_engine
        p_engine = get_pronunciation_engine()

        # Priority 1: Edge TTS
        try:
            import edge_tts
            _t0 = _ttime.perf_counter()
            
            debug_info = p_engine.process_for_tts_debug(text, provider="edge")
            payload = debug_info["final_text_sent_to_tts"]
            is_ssml = debug_info.get("ssml_generated", False) or payload.strip().startswith("<speak")
            input_type = "SSML" if is_ssml else "Plain Text"

            _tts_logger.info("[TTS PRE-SYNTHESIS] Provider=Edge TTS Voice=%s InputType=%s Payload=%r", voice, input_type, payload)
            print(f"[TTS DEBUG] Provider: Edge TTS | Voice: {voice} | Input Type: {input_type} | Payload: {payload}", flush=True)

            audio_data = b""
            try:
                communicate = edge_tts.Communicate(payload, voice=voice, rate=RATE, pitch=PITCH)
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data += chunk["data"]
                if not audio_data:
                    raise ValueError("Edge TTS generated empty audio data")
            except Exception as stream_err:
                # Requirement 2 & 5: If provider rejects SSML tags, automatically fall back without speaking XML tags
                if is_ssml:
                    fallback_text = p_engine.process_for_tts(text, provider="edge_fallback")
                    if not fallback_text or "<" in fallback_text:
                        fallback_text = re.sub(r'<[^>]+>', '', payload).strip()
                    _tts_logger.warning("[TTS FALLBACK] Edge TTS SSML failed (%s). Retrying with plain spoken form: %r", stream_err, fallback_text)
                    print(f"[TTS FALLBACK] Retrying Edge TTS with plain spoken form: {fallback_text}", flush=True)

                    communicate = edge_tts.Communicate(fallback_text, voice=voice, rate=RATE, pitch=PITCH)
                    audio_data = b""
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            audio_data += chunk["data"]
                    if not audio_data:
                        raise ValueError("Edge TTS fallback generated empty audio data")
                else:
                    raise stream_err

            fd, temp_path = tempfile.mkstemp(suffix=".mp3")
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(audio_data)
                await asyncio.to_thread(_play_mp3_mci, temp_path)
                _lat = (_ttime.perf_counter() - _t0) * 1000
                _tts_logger.info("[TTS] COMPLETED backend=EDGE latency=%.0fms", _lat)
                print("[TTS] COMPLETED", flush=True)
                return
            finally:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
        except Exception as e:
            import logging
            _tts_logger.warning("[TTS] FAILED backend=EDGE error=%s: %s", type(e).__name__, e)
            logging.getLogger("jarvis.voice").warning("Edge TTS failed, falling back to pyttsx3: %s", e)

        # Priority 2: pyttsx3
        try:
            import pyttsx3
            _t0 = _ttime.perf_counter()
            _tts_logger.info("[TTS] TRYING pyttsx3")
            print("[TTS] USING PYTTSX3", flush=True)
            tts_text_plain = p_engine.process_for_tts(text, provider="pyttsx3")
            def run_pyttsx3():
                engine = pyttsx3.init()
                engine.say(tts_text_plain)
                engine.runAndWait()
            await asyncio.to_thread(run_pyttsx3)
            _lat = (_ttime.perf_counter() - _t0) * 1000
            _tts_logger.info("[TTS] COMPLETED backend=PYTTSX3 latency=%.0fms", _lat)
            print("[TTS] COMPLETED", flush=True)
            return
        except Exception as e:
            import logging
            _tts_logger.warning("[TTS] FAILED backend=PYTTSX3 error=%s: %s", type(e).__name__, e)
            logging.getLogger("jarvis.voice").warning("pyttsx3 failed, falling back to gTTS: %s", e)

        # Priority 3: gTTS
        try:
            from gtts import gTTS
            _t0 = _ttime.perf_counter()
            _tts_logger.info("[TTS] TRYING gTTS")
            print("[TTS] USING GTTS", flush=True)
            tts_text_plain = p_engine.process_for_tts(text, provider="gtts")
            lang_code = "te" if "te-IN" in voice else "en"
            tts = gTTS(text=tts_text_plain, lang=lang_code)
            fd, temp_path = tempfile.mkstemp(suffix=".mp3")
            try:
                tts.save(temp_path)
                await asyncio.to_thread(_play_mp3_mci, temp_path)
                _lat = (_ttime.perf_counter() - _t0) * 1000
                _tts_logger.info("[TTS] COMPLETED backend=GTTS latency=%.0fms", _lat)
                print("[TTS] COMPLETED", flush=True)
                return
            finally:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
        except Exception as e:
            import logging
            _tts_logger.warning("[TTS] FAILED backend=GTTS error=%s: %s", type(e).__name__, e)
            logging.getLogger("jarvis.voice").error("gTTS failed: %s", e)

        # Priority 4: Windows SAPI hard fallback (guaranteed — built into Windows)
        # This path executes via PowerShell and requires no Python audio library.
        _tts_logger.error("[TTS] ALL PRIMARY BACKENDS FAILED — using Windows SAPI fallback")
        print("[TTS] USING WINDOWS SAPI FALLBACK", flush=True)
        try:
            import subprocess
            tts_text_sapi = p_engine.process_for_tts(text, provider="sapi")
            # Escape single quotes in text for PowerShell
            safe_text = tts_text_sapi.replace("'", "''").replace('"', '')
            ps_cmd = (
                f"Add-Type -AssemblyName System.Speech; "
                f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$s.Rate = -2; $s.Speak('{safe_text}')"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd],
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            _tts_logger.info("[TTS] COMPLETED backend=WINDOWS_SAPI")
            print("[TTS] COMPLETED (SAPI)", flush=True)
        except Exception as e:
            _tts_logger.error("[TTS] ALL TTS BACKENDS FAILED including SAPI: %s", e)
            print("[TTS] ALL TTS BACKENDS FAILED", flush=True)

    def speak(self, text: str):
        event = threading.Event()
        self.queue.put((text, event))
        self.write_diagnostics()
        event.wait()

    def write_diagnostics(self):
        import sys
        import json
        # Only write diagnostics if we are the voice service or main jarvis process
        if not any("voice_service" in arg or "voice_engine" in arg or "jarvis" in arg for arg in sys.argv):
            return
        diag_dir = "logs"
        os.makedirs(diag_dir, exist_ok=True)
        diag_path = os.path.join(diag_dir, "voice_diagnostics.json")
        try:
            with open(diag_path, "w") as f:
                json.dump({
                    "status": "HEALTHY" if self.is_running else "OFFLINE",
                    "pid": self.pid,
                    "speaker": self.current_speaker,
                    "queue_length": self.queue.qsize(),
                    "speaking_state": "SPEAKING" if self.speaking else "STANDBY",
                    "listener_state": self.listener_state
                }, f)
        except Exception:
            pass


    # ── Backward Compatibility Helpers ──
async def _speak_async(text: str, voice: str | None = None):
    """Asynchronous module-level speak function matching legacy test footprints."""
    if voice is None:
        from JARVIS.core.system.utils.telugu_formatter import contains_telugu_script, detect_language
        if contains_telugu_script(text) or detect_language(text) == "telugu":
            voice = "te-IN-MohanNeural"
        else:
            voice = "en-US-AriaNeural"
    await VoiceEngine()._speak_async_direct(text, voice)


def speak(text: str):
    """Refactored entrypoint routing through VoiceEngine singleton."""
    VoiceEngine().speak(text)


def stop_playback():
    """Stop active TTS playback immediately (for barge-in)."""
    VoiceEngine().stop_speaking()


if __name__ == "__main__":
    speak("All systems online. Hesa is ready, sir.")

