"""Pure voice state machine used by optional voice UX flows."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class VoiceState(StrEnum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    LISTENING_FOR_WAKE_WORD = "LISTENING_FOR_WAKE_WORD"
    WAKE_WORD_DETECTED = "WAKE_WORD_DETECTED"
    LISTENING_FOR_COMMAND = "LISTENING_FOR_COMMAND"
    TRANSCRIBING = "TRANSCRIBING"
    THINKING = "THINKING"
    PROCESSING_COMMAND = "PROCESSING_COMMAND"
    SPEAKING = "SPEAKING"
    SPEAKING_RESPONSE = "SPEAKING_RESPONSE"
    ERROR = "ERROR"
    ERROR_RECOVERY = "ERROR_RECOVERY"
    DISABLED = "DISABLED"


ALL_STATES = set(VoiceState)

ALLOWED_TRANSITIONS: dict[VoiceState, set[VoiceState]] = {
    VoiceState.IDLE: ALL_STATES,
    VoiceState.LISTENING: ALL_STATES,
    VoiceState.LISTENING_FOR_WAKE_WORD: ALL_STATES,
    VoiceState.WAKE_WORD_DETECTED: ALL_STATES,
    VoiceState.LISTENING_FOR_COMMAND: ALL_STATES,
    VoiceState.TRANSCRIBING: ALL_STATES,
    VoiceState.THINKING: ALL_STATES,
    VoiceState.PROCESSING_COMMAND: ALL_STATES,
    VoiceState.SPEAKING: ALL_STATES,
    VoiceState.SPEAKING_RESPONSE: ALL_STATES,
    VoiceState.ERROR: ALL_STATES,
    VoiceState.ERROR_RECOVERY: ALL_STATES,
    VoiceState.DISABLED: ALL_STATES,
}


UI_STATE_BY_VOICE_STATE: dict[VoiceState, str] = {
    VoiceState.IDLE: "STANDBY",
    VoiceState.LISTENING: "LISTENING",
    VoiceState.LISTENING_FOR_WAKE_WORD: "STANDBY",
    VoiceState.WAKE_WORD_DETECTED: "LISTENING",
    VoiceState.LISTENING_FOR_COMMAND: "LISTENING",
    VoiceState.TRANSCRIBING: "TRANSCRIBING",
    VoiceState.THINKING: "THINKING",
    VoiceState.PROCESSING_COMMAND: "PROCESSING",
    VoiceState.SPEAKING: "SPEAKING",
    VoiceState.SPEAKING_RESPONSE: "SPEAKING",
    VoiceState.ERROR: "ERROR",
    VoiceState.ERROR_RECOVERY: "ERROR",
    VoiceState.DISABLED: "OFFLINE",
}


def _coerce_state(state: VoiceState | str) -> VoiceState:
    if isinstance(state, VoiceState):
        return state
    return VoiceState[str(state)]


def transition_voice_state(current: VoiceState | str, target: VoiceState | str, *, detail: str = "") -> dict[str, object]:
    """Validate a voice state transition without touching UI/runtime code."""

    source = _coerce_state(current)
    destination = _coerce_state(target)
    allowed = destination in ALLOWED_TRANSITIONS[source]
    reason = "valid transition" if allowed else f"invalid transition from {source.value} to {destination.value}"
    return {
        "ok": allowed,
        "from": source.value,
        "to": destination.value,
        "reason": reason,
        "detail": detail,
    }


def voice_state_to_ui_state(state: VoiceState | str) -> str:
    return UI_STATE_BY_VOICE_STATE[_coerce_state(state)]


@dataclass
class VoiceStateMachine:
    state: VoiceState = VoiceState.IDLE

    def transition(self, target: VoiceState | str, *, detail: str = "") -> dict[str, object]:
        result = transition_voice_state(self.state, target, detail=detail)
        if result["ok"]:
            self.state = _coerce_state(target)
        return result

    def force(self, target: VoiceState | str, *, detail: str = "") -> dict[str, object]:
        previous = self.state
        self.state = _coerce_state(target)
        return {
            "ok": True,
            "from": previous.value,
            "to": self.state.value,
            "reason": "forced transition",
            "detail": detail,
        }
