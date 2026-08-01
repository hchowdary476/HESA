"""JARVIS Gesture Control Module — MediaPipe Tasks API + OpenCV + PyAutoGUI interaction."""

from __future__ import annotations

import os
import threading
import time

# Lazy loading variables and helpers
OPENCV_AVAILABLE = None
MEDIAPIPE_AVAILABLE = None
PYAUTOGUI_AVAILABLE = None

_cv2 = None
_mp = None
_python = None
_vision = None
_pyautogui = None


def _load_opencv():
    global OPENCV_AVAILABLE, _cv2
    if OPENCV_AVAILABLE is None:
        try:
            import cv2  # type: ignore

            _cv2 = cv2
            OPENCV_AVAILABLE = True
        except ImportError:
            OPENCV_AVAILABLE = False
    return OPENCV_AVAILABLE


def _load_mediapipe():
    global MEDIAPIPE_AVAILABLE, _mp, _python, _vision
    if MEDIAPIPE_AVAILABLE is None:
        try:
            import mediapipe as mp  # type: ignore
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision

            _mp = mp
            _python = python
            _vision = vision
            MEDIAPIPE_AVAILABLE = True
        except ImportError:
            MEDIAPIPE_AVAILABLE = False
    return MEDIAPIPE_AVAILABLE


def _load_pyautogui():
    global PYAUTOGUI_AVAILABLE, _pyautogui
    if PYAUTOGUI_AVAILABLE is None:
        try:
            import pyautogui  # type: ignore

            pyautogui.FAILSAFE = False
            _pyautogui = pyautogui
            PYAUTOGUI_AVAILABLE = True
        except ImportError:
            PYAUTOGUI_AVAILABLE = False
    return PYAUTOGUI_AVAILABLE


class GestureController:
    """Tracks hand gestures via camera and translates them into OS input controls."""

    def __init__(self) -> None:
        self.running = False
        self.thread = None
        self.app_instance = None
        self.cooldown_until = 0.0
        self.sensitivity = 1.8
        self.hud_name = "JARVIS — Gesture HUD"

    def is_supported(self) -> bool:
        """Returns True if OpenCV, MediaPipe, and PyAutoGUI are fully installed and the model is present."""
        _load_opencv()
        _load_mediapipe()
        _load_pyautogui()
        model_path = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")
        return bool(OPENCV_AVAILABLE and MEDIAPIPE_AVAILABLE and PYAUTOGUI_AVAILABLE and os.path.exists(model_path))

    def start(self, app_instance=None) -> bool:
        """Start the gesture tracking loop in a background thread."""
        if not self.is_supported():
            print("[GESTURE] Gesture control is not supported. Missing dependencies or model.")
            return False

        if self.running:
            return True

        self.app_instance = app_instance
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        print("[GESTURE] Gesture control daemon started.")
        return True

    def stop(self) -> None:
        """Stop gesture tracking and release resources."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
        print("[GESTURE] Gesture control daemon stopped.")

    def _loop(self) -> None:
        _load_opencv()
        _load_mediapipe()
        _load_pyautogui()

        # Initialize MediaPipe Tasks Hand Landmarker
        model_path = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")
        base_options = _python.BaseOptions(model_asset_path=model_path)
        options = _vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=1,
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.7,
            min_tracking_confidence=0.7,
        )
        detector = _vision.HandLandmarker.create_from_options(options)

        from JARVIS.core.system.utils.camera_tracker import TrackedVideoCapture, has_higher_priority_owner

        cap = TrackedVideoCapture(0, owner="Gesture Engine")

        # Track cursor coordinates
        prev_x, prev_y = 0.0, 0.0
        initialized = False

        while self.running:
            # Handle preemption/re-acquisition
            if getattr(cap, "preempted", False) or not cap.isOpened():
                time.sleep(0.5)
                if not has_higher_priority_owner("Gesture Engine"):
                    cap = TrackedVideoCapture(0, owner="Gesture Engine")
                continue

            ret, frame = cap.read()
            if not ret:
                if getattr(cap, "preempted", False):
                    continue
                time.sleep(0.01)
                continue

            # Mirror the frame horizontally for intuitive interaction
            frame = _cv2.flip(frame, 1)
            h, w, _ = frame.shape

            # Convert to RGB for MediaPipe Tasks
            rgb_frame = _cv2.cvtColor(frame, _cv2.COLOR_BGR2RGB)
            mp_image = _mp.Image(image_format=_mp.ImageFormat.SRGB, data=rgb_frame)

            # Detect
            detection_result = detector.detect(mp_image)

            gesture_label = "IDLE (NO HAND)"
            confidence = 0.0

            if detection_result.hand_landmarks:
                for hand_landmarks, hand_info in zip(detection_result.hand_landmarks, detection_result.handedness):
                    confidence = hand_info[0].score * 100
                    landmarks = hand_landmarks
                    hand_label = hand_info[0].category_name

                    # 1. Neon blue skeleton drawing
                    self._draw_hud_landmarks(frame, landmarks, w, h)

                    # 2. Extract specific points
                    wrist = landmarks[0]
                    thumb_tip = landmarks[4]
                    thumb_ip = landmarks[3]
                    index_tip = landmarks[8]
                    index_pip = landmarks[6]
                    middle_tip = landmarks[12]
                    middle_pip = landmarks[10]
                    ring_tip = landmarks[16]
                    ring_pip = landmarks[14]
                    pinky_tip = landmarks[20]
                    pinky_pip = landmarks[18]

                    # 3. Check finger extensions
                    def get_dist(p1, p2):
                        return ((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2) ** 0.5

                    fingers = [
                        get_dist(wrist, thumb_tip) > get_dist(wrist, thumb_ip),
                        get_dist(wrist, index_tip) > get_dist(wrist, index_pip),
                        get_dist(wrist, middle_tip) > get_dist(wrist, middle_pip),
                        get_dist(wrist, ring_tip) > get_dist(wrist, ring_pip),
                        get_dist(wrist, pinky_tip) > get_dist(wrist, pinky_pip),
                    ]
                    extended_count = sum(1 for f in fingers if f)

                    # Check for palm gesture
                    is_palm = all(fingers[1:])

                    # 4. Check pinch
                    pinch_dist = ((thumb_tip.x - index_tip.x) ** 2 + (thumb_tip.y - index_tip.y) ** 2) ** 0.5
                    is_pinching = pinch_dist < 0.045

                    # Determine and map actions
                    now = time.time()

                    if extended_count == 0:
                        gesture_label = "PAUSED (FIST)"
                    elif is_pinching:
                        gesture_label = "SELECT (PINCH)"
                        if now > self.cooldown_until:
                            _pyautogui.click()
                            self.cooldown_until = now + 0.5
                    elif is_palm:
                        gesture_label = "PALM DETECTED - WAKING JARVIS"
                        if now > self.cooldown_until:
                            # Trigger the full wake event on the running UI
                            if self.app_instance:
                                self.app_instance.after(0, lambda: self.app_instance._on_activation_event("palm_gesture"))
                            # Call Python UI hook to launch OS dashboard
                            from JARVIS.gui.ui_jarvis_os import launch_os_window

                            launch_os_window()
                            self.cooldown_until = now + 2.0
                    elif extended_count == 1 and fingers[1]:
                        gesture_label = "CURSOR (1 FINGER)"
                        # Smooth mouse move based on relative movement
                        curr_x, curr_y = index_tip.x * w, index_tip.y * h
                        if not initialized:
                            prev_x, prev_y = curr_x, curr_y
                            initialized = True

                        dx = curr_x - prev_x
                        dy = curr_y - prev_y

                        # Apply deadzone and sensitivity
                        if abs(dx) > 1 or abs(dy) > 1:
                            _pyautogui.moveRel(int(dx * self.sensitivity), int(dy * self.sensitivity))
                        prev_x, prev_y = curr_x, curr_y
                    elif extended_count == 2 and fingers[1] and fingers[2]:
                        gesture_label = "CLICK (2 FINGERS)"
                        if now > self.cooldown_until:
                            _pyautogui.click()
                            self.cooldown_until = now + 0.6
                    elif extended_count == 3 and fingers[1] and fingers[2] and fingers[3]:
                        gesture_label = "RIGHT CLICK (3 FINGERS)"
                        if now > self.cooldown_until:
                            _pyautogui.rightClick()
                            self.cooldown_until = now + 0.8
                    elif extended_count == 4 and not fingers[4]:
                        gesture_label = "MENU (4 FINGERS)"
                        if now > self.cooldown_until:
                            _pyautogui.press("win")
                            self.cooldown_until = now + 1.0
                    elif fingers[0] and extended_count == 1:
                        gesture_label = "CONFIRM (THUMB ONLY)"
                        if now > self.cooldown_until:
                            _pyautogui.press("enter")
                            self.cooldown_until = now + 0.8
                    else:
                        gesture_label = f"UNKNOWN ({extended_count} FINGERS)"
            else:
                initialized = False

            # Draw HUD panel on frame
            resized_frame = _cv2.resize(frame, (300, 240))
            self._draw_hud_overlay(resized_frame, gesture_label, confidence)

            # Display HUD overlay
            _cv2.imshow(self.hud_name, resized_frame)

            # CV2 Keypress polling
            key = _cv2.waitKey(1) & 0xFF
            if key == ord("q") or key == 27:  # q or ESC to stop
                break

        # Cleanup opencv windows and camera
        cap.release()
        _cv2.destroyWindow(self.hud_name)
        self.running = False

    def _draw_hud_landmarks(self, frame, landmarks, w, h) -> None:
        """Draw holographic lines connecting joints."""
        # MediaPipe Connections
        connections = [
            (0, 1),
            (1, 2),
            (2, 3),
            (3, 4),  # Thumb
            (0, 5),
            (5, 6),
            (6, 7),
            (7, 8),  # Index
            (9, 10),
            (10, 11),
            (11, 12),  # Middle
            (13, 14),
            (14, 15),
            (15, 16),  # Ring
            (0, 17),
            (17, 18),
            (18, 19),
            (19, 20),  # Pinky
            (5, 9),
            (9, 13),
            (13, 17),  # Palm base
        ]

        # Draw lines
        for start, end in connections:
            x1, y1 = int(landmarks[start].x * w), int(landmarks[start].y * h)
            x2, y2 = int(landmarks[end].x * w), int(landmarks[end].y * h)
            _cv2.line(frame, (x1, y1), (x2, y2), (255, 191, 0), 2)  # Neon Blue

        # Draw joints
        for lm in landmarks:
            cx, cy = int(lm.x * w), int(lm.y * h)
            _cv2.circle(frame, (cx, cy), 4, (0, 255, 255), -1)  # Cyan Core

    def _draw_hud_overlay(self, frame, label: str, confidence: float) -> None:
        """Draw HUD frame border, status labels, and indicators."""
        h, w, _ = frame.shape
        # Outer border
        _cv2.rectangle(frame, (5, 5), (w - 5, h - 5), (255, 191, 0), 1)
        # Scanline look
        _cv2.rectangle(frame, (10, 10), (w - 10, h - 10), (255, 191, 0), 1)

        # Draw text panels
        _cv2.putText(frame, f"GESTURE: {label}", (15, 30), _cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, _cv2.LINE_AA)
        _cv2.putText(frame, f"CONFIDENCE: {confidence:.1f}%", (15, 50), _cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 127), 1, _cv2.LINE_AA)
        _cv2.putText(frame, "JARVIS SYSTEM GESTURE HUD", (15, h - 15), _cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 191, 255), 1, _cv2.LINE_AA)


# Singleton instance
gesture_controller = GestureController()
