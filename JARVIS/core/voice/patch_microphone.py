import subprocess
import sys

import speech_recognition as sr

from JARVIS.core.voice.microphone import SoundDeviceMicrophone

# ── Subprocess creation flags patch for Windows ─────────────────────────────
# Spawning console applications (like flac.exe) inside detached processes (like
# pythonw.exe services) without CREATE_NO_WINDOW causes WinError 50.
_orig_popen = subprocess.Popen


class PatchedPopen(_orig_popen):
    def __init__(self, *args, **kwargs):
        if sys.platform == "win32":
            flags = kwargs.get("creationflags", 0)
            flags |= subprocess.CREATE_NO_WINDOW
            kwargs["creationflags"] = flags

            # Prevent inheriting parent's standard handles to avoid DuplicateHandle WinError 50
            for stream in ("stdin", "stdout", "stderr"):
                if kwargs.get(stream) is None:
                    kwargs[stream] = subprocess.DEVNULL
        super().__init__(*args, **kwargs)


subprocess.Popen = PatchedPopen

# Apply the monkey patch
sr.Microphone = SoundDeviceMicrophone
print("[PATCH] speech_recognition.Microphone monkey-patched with sounddevice successfully.")
