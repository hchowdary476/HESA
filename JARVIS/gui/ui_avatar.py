"""
JARVIS living holographic avatar — headless state engine.

This module drives ALL facial animation math (eye blinking, pupil micro-movements,
lip-sync phonemes, eyebrow lift, jaw drop, cheek stretch, breathing) but performs
NO canvas rendering. It exposes a single `get_frame()` method that returns the
current animation state as a plain dict, ready to be consumed by the QML
FaceEngine at 60 FPS via JarvisBridge.poll_avatar_frame().
"""

from __future__ import annotations

import math
import random
import time


class JarvisAvatarState:
    """
    Pure-Python animation state machine — no GUI dependencies.

    Consumed by JarvisBridge which polls get_frame() at 60 FPS and emits
    the values as Qt signals into QML FaceEngine.qml.
    """

    def __init__(self):
        self.is_alive = True
        self.state    = "STANDBY"

        # Eyelids & Blinking
        self.eyelids_scale      = 1.0
        self.blink_state        = "open"
        self.blink_timer        = random.uniform(3.0, 7.0)
        self.blink_progress     = 0.0

        # Pupil focus shifts (micro-saccades)
        self.pupil_x            = 0.0
        self.pupil_y            = 0.0
        self.pupil_x_target     = 0.0
        self.pupil_y_target     = 0.0
        self.pupil_timer        = random.uniform(1.0, 2.5)

        # Mouth / Lip geometry
        self.mouth_w            = 28.0
        self.mouth_h            = 1.0
        self.mouth_w_target     = 28.0
        self.mouth_h_target     = 1.0

        # Cheek muscles
        self.cheek_lx           = -48.0
        self.cheek_ly           =  15.0
        self.cheek_rx           =  48.0
        self.cheek_ry           =  15.0
        self.cheek_lx_target    = -48.0
        self.cheek_ly_target    =  15.0
        self.cheek_rx_target    =  48.0
        self.cheek_ry_target    =  15.0

        # Eyebrows & Jaw
        self.eyebrow_lift        = 0.0
        self.eyebrow_lift_target = 0.0
        self.jaw_drop            = 0.0
        self.jaw_drop_target     = 0.0

        # Speech
        self.speaking_text       = ""
        self.speech_start_time   = 0.0

        # Breathing / scale
        self.breathing_phase     = 0.0
        self.breathing_rate      = 1.5
        self.scale               = 1.0

        # Ring rotation (exported so QML can animate HUD rings)
        self.ring_phase_1        = 0.0
        self.ring_phase_2        = 0.0

        self.last_time           = time.time()

    # ── Public API ────────────────────────────────────────────────────────

    def set_state(self, state: str):
        self.state = state.upper()
        if self.state == "PROCESSING":
            self.breathing_rate = 3.5
        elif self.state == "EXECUTING":
            self.breathing_rate = 4.0
        else:
            self.breathing_rate = 1.5

    def set_speaking_text(self, text: str):
        self.speaking_text     = text
        self.speech_start_time = time.time()
        self.set_state("SPEAKING")

    def tick(self) -> None:
        """Advance the simulation by one frame (called externally at 60 FPS)."""
        if not self.is_alive:
            return
        t  = time.time()
        dt = min(t - self.last_time, 0.1)   # clamp dt to avoid jump on lag
        self.last_time = t

        self.ring_phase_1 += 0.5  * dt
        self.ring_phase_2 -= 0.8  * dt

        self._update_blinking(dt)
        self._update_focus_shifts(dt)
        self._update_speech_mouth(t, dt)

    def get_frame(self) -> dict:
        """
        Advance simulation by one tick and return current animation state.
        Called by JarvisBridge at 60 FPS.
        """
        self.tick()
        t = time.time()
        return {
            "eyelids_scale": self.eyelids_scale,
            "mouth_w":       self.mouth_w,
            "mouth_h":       self.mouth_h,
            "pupil_x":       self.pupil_x,
            "pupil_y":       self.pupil_y,
            "eyebrow_lift":  self.eyebrow_lift,
            "jaw_drop":      self.jaw_drop,
            "cheek_lx":      self.cheek_lx,
            "cheek_rx":      self.cheek_rx,
            "cheek_ly":      self.cheek_ly,
            "cheek_ry":      self.cheek_ry,
            "scale":         self.scale,
            "ring_phase_1":  math.degrees(self.ring_phase_1) % 360,
            "ring_phase_2":  math.degrees(self.ring_phase_2) % 360,
            "drift_x":       2.5 * math.sin(t * 0.8),
            "drift_y":       1.8 * math.cos(t * 0.5),
        }

    def stop(self):
        self.is_alive = False

    # ── Phoneme mouth shapes ──────────────────────────────────────────────

    def _get_phoneme_mouth_shape(self, char: str) -> tuple[float, float]:
        """Convert character to viseme mouth shape (width, height)."""
        char = char.lower()
        if char == 'a': return 35.0, 25.0
        if char == 'e': return 38.0, 15.0
        if char == 'i': return 40.0, 10.0
        if char == 'o': return 26.0, 26.0
        if char == 'u': return 22.0, 18.0
        if char in ('m', 'b', 'p'): return 28.0, 0.5
        if char in ('f', 'v'):      return 30.0, 3.5
        if char in ('l', 'n', 't', 'd'): return 32.0, 8.0
        if char in (' ', ',', '.', '!', '?'): return 30.0, 1.0
        return 34.0, 8.0

    # ── Internal updaters ─────────────────────────────────────────────────

    def _update_blinking(self, dt: float):
        if self.blink_state == "open":
            self.blink_timer -= dt
            if self.blink_timer <= 0:
                self.blink_state    = "closing"
                self.blink_progress = 0.0
        elif self.blink_state == "closing":
            self.blink_progress += dt / 0.12
            if self.blink_progress >= 1.0:
                self.blink_progress = 1.0
                self.blink_state    = "closed"
                self.blink_timer    = 0.03
            self.eyelids_scale = 1.0 - self.blink_progress
        elif self.blink_state == "closed":
            self.blink_timer -= dt
            if self.blink_timer <= 0:
                self.blink_state    = "opening"
                self.blink_progress = 0.0
            self.eyelids_scale = 0.0
        elif self.blink_state == "opening":
            self.blink_progress += dt / 0.12
            if self.blink_progress >= 1.0:
                self.blink_progress = 1.0
                self.blink_state    = "open"
                self.blink_timer    = random.uniform(3.0, 7.0)
            self.eyelids_scale = self.blink_progress

    def _update_focus_shifts(self, dt: float):
        self.pupil_timer -= dt
        if self.pupil_timer <= 0:
            if self.state in ("SPEAKING", "LISTENING"):
                self.pupil_x_target = random.uniform(-0.8, 0.8)
                self.pupil_y_target = random.uniform(-0.5, 0.5)
                self.pupil_timer    = random.uniform(0.8, 1.8)
            else:
                self.pupil_x_target = random.uniform(-2.0, 2.0)
                self.pupil_y_target = random.uniform(-1.2, 1.2)
                self.pupil_timer    = random.uniform(1.2, 3.0)
        self.pupil_x += (self.pupil_x_target - self.pupil_x) * 0.15
        self.pupil_y += (self.pupil_y_target - self.pupil_y) * 0.15

    def _update_speech_mouth(self, t: float, dt: float):
        self.breathing_phase += self.breathing_rate * dt
        self.scale = 1.0 + 0.006 * math.sin(t * 1.6)

        if self.state == "SPEAKING" and self.speaking_text:
            char_idx = int((t - self.speech_start_time) * 16)
            if char_idx < len(self.speaking_text):
                char = self.speaking_text[char_idx]
                w_t, h_t = self._get_phoneme_mouth_shape(char)
                self.mouth_w_target     = w_t
                self.mouth_h_target     = h_t
                self.eyebrow_lift_target = 1.0 + (h_t / 25.0) * 3.0
            else:
                self.mouth_w_target      = 28.0
                self.mouth_h_target      = 1.0
                self.eyebrow_lift_target = 0.0

            self.jaw_drop_target = self.mouth_h_target * 0.4
            cheek_stretch = (self.mouth_w_target - 28.0) * 0.4
            self.cheek_lx_target = -48.0 - cheek_stretch
            self.cheek_rx_target =  48.0 + cheek_stretch
            self.cheek_ly_target =  15.0 - (self.mouth_h_target * 0.15)
            self.cheek_ry_target =  15.0 - (self.mouth_h_target * 0.15)

        elif self.state == "SPEAKING":
            self.mouth_w_target      = 34.0 + 4.0 * math.sin(t * 12.0)
            self.mouth_h_target      = 8.0  + 7.0 * math.cos(t * 14.0)
            self.eyebrow_lift_target = 1.5  + 1.5 * math.sin(t * 5.0)
            self.jaw_drop_target     = self.mouth_h_target * 0.4
            cheek_stretch = (self.mouth_w_target - 28.0) * 0.4
            self.cheek_lx_target = -48.0 - cheek_stretch
            self.cheek_rx_target =  48.0 + cheek_stretch
            self.cheek_ly_target =  15.0 - (self.mouth_h_target * 0.15)
            self.cheek_ry_target =  15.0 - (self.mouth_h_target * 0.15)
        else:
            self.mouth_w_target      = 28.0
            self.mouth_h_target      = 1.0
            self.eyebrow_lift_target = 0.0
            self.jaw_drop_target     = 0.0
            self.cheek_lx_target = -48.0
            self.cheek_ly_target =  15.0
            self.cheek_rx_target =  48.0
            self.cheek_ry_target =  15.0

        self.mouth_w     += (self.mouth_w_target     - self.mouth_w)     * 0.3
        self.mouth_h     += (self.mouth_h_target     - self.mouth_h)     * 0.3
        self.cheek_lx    += (self.cheek_lx_target    - self.cheek_lx)    * 0.2
        self.cheek_ly    += (self.cheek_ly_target    - self.cheek_ly)    * 0.2
        self.cheek_rx    += (self.cheek_rx_target    - self.cheek_rx)    * 0.2
        self.cheek_ry    += (self.cheek_ry_target    - self.cheek_ry)    * 0.2
        self.eyebrow_lift += (self.eyebrow_lift_target - self.eyebrow_lift) * 0.25
        self.jaw_drop    += (self.jaw_drop_target    - self.jaw_drop)    * 0.2


# ── Backwards compatibility shim for existing imports / tests ─────────────────
# The old JarvisAvatar class is kept as a thin wrapper over JarvisAvatarState
# so that any code that imports `JarvisAvatar` still works.

class JarvisAvatar(JarvisAvatarState):
    """
    Legacy compatibility class.

    Old code imported JarvisAvatar(canvas). Since we no longer render to
    a canvas, the canvas argument is accepted but ignored. All animation
    math is still driven by the parent JarvisAvatarState class.
    Tests that use MockCanvas can continue to pass without modification.
    """

    def __init__(self, canvas=None):
        super().__init__()
        # Store canvas ref for tests that inspect it, but never draw to it
        self._canvas_compat = canvas
