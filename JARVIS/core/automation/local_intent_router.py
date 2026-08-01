"""Fast local command routing for common free-first assistant actions."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

ActionPayload = dict[str, Any]

APP_ALIASES = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "steam": "steam",
    "epic": "epic",
    "epic games": "epic",
    "spotify": "spotify",
    "vscode": "vscode",
    "visual studio code": "vscode",
    "vs code": "vscode",
    "notepad": "notepad",
    "calculator": "calculator",
    "explorer": "explorer",
    "settings": "settings",
    "task manager": "taskmgr",
    "discord": "discord",
    "whatsapp": "whatsapp",
    "word": "word",
    "excel": "excel",
    "powerpoint": "powerpoint",
    "paint": "paint",
    "cmd": "cmd",
}
SORTED_APP_ALIASES = tuple(sorted(APP_ALIASES, key=len, reverse=True))

DIRECT_ACTION_PATTERNS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("current time", "what time", "time now"), "get_time"),
    (("current date", "what date", "what day", "today date"), "get_date"),
    (("battery", "battery status"), "get_battery"),
    (("ram", "memory usage", "memory status"), "get_ram"),
    (("cpu", "processor usage", "cpu usage"), "get_cpu"),
    (("screenshot", "screen shot", "take screenshot"), "screenshot"),
    (("read clipboard", "clipboard read"), "read_clipboard"),
    (("summarize clipboard", "clipboard summary"), "summarize_clipboard"),
    (("read notes", "list notes"), "read_notes"),
    (("memory stats", "memory status"), "memory_stats"),
    (("memory summary",), "memory_summary"),
    (("memory health",), "memory_health"),
    (("memory habits", "my habits", "command habits"), "memory_habits"),
    (("daily summary", "daily briefing"), "daily_summary"),
    (("clean memory", "prune memory", "cleanup memory"), "prune_memory"),
    (("run diagnostics", "check system health", "scan for problems", "run health scan", "system health check"), "run_system_diagnostics"),
    (("run safe repairs", "system repair", "repair system"), "run_safe_repairs"),
    (("lock pc", "lock screen", "lock computer"), "lock_screen"),
    (("sleep pc", "sleep computer", "suspend pc"), "sleep"),
    (("shutdown", "shutdown pc", "shutdown computer", "turn off computer"), "shutdown"),
    (("restart", "restart pc", "restart computer"), "restart"),
)

TRAILING_SEARCH_WORDS = (" search",)
WEBSITE_ALIASES = {
    "youtube": "https://www.youtube.com",
    "github": "https://github.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "openai": "https://openai.com",
    "groq": "https://console.groq.com",
}
WINDOW_ACTIONS = {
    "minimize all windows": "minimize_all",
    "minimize all": "minimize_all",
    "show desktop": "minimize_all",
    "maximize window": "maximize_window",
    "maximize current window": "maximize_window",
    "close window": "close_window",
    "close current window": "close_window",
}
KEY_ACTIONS = {
    "mute volume": "volumemute",
    "unmute volume": "volumemute",
    "volume up": "volumeup",
    "turn volume up": "volumeup",
    "increase volume": "volumeup",
    "volume down": "volumedown",
    "turn volume down": "volumedown",
    "decrease volume": "volumedown",
}
SPOTIFY_ACTIONS = {
    "play music": "spotify_play",
    "resume music": "spotify_play",
    "pause music": "spotify_pause",
    "stop music": "spotify_pause",
    "next track": "spotify_next",
    "next song": "spotify_next",
    "previous track": "spotify_prev",
    "previous song": "spotify_prev",
    "what is playing on spotify": "spotify_current",
    "current spotify song": "spotify_current",
}

WORLD_MAP_ACTIONS: dict[str, str] = {
    "open world map": "worldmap_open",
    "show world map": "worldmap_open",
    "global command center": "worldmap_open",
    "open global map": "worldmap_open",
    "show global map": "worldmap_open",
    "open map": "worldmap_open",
    "enable satellite mode": "worldmap_satellite",
    "satellite mode": "worldmap_satellite",
    "show satellite view": "worldmap_satellite",
    "network mode": "worldmap_network",
    "show network activity": "worldmap_network",
    "show network mode": "worldmap_network",
    "security mode": "worldmap_security",
    "threat map": "worldmap_security",
    "show threat intelligence": "worldmap_security",
    "ai agent mode": "worldmap_ai",
    "show ai agents": "worldmap_ai",
    "communication mode": "worldmap_comms",
    "display global connections": "worldmap_comms",
    "show weather layer": "worldmap_weather",
    "show weather": "worldmap_weather",
    "zoom in": "worldmap_zoom_in",
    "zoom out": "worldmap_zoom_out",
    "reset map": "worldmap_reset",
    "globe reset": "worldmap_reset",
}
WORLD_MAP_FLY_PREFIXES = ("show ", "zoom to ", "fly to ", "navigate to ", "focus on ")
WORLD_MAP_COUNTRIES = (
    "india",
    "china",
    "usa",
    "uk",
    "japan",
    "russia",
    "germany",
    "france",
    "australia",
    "brazil",
    "canada",
    "south korea",
    "singapore",
    "dubai",
    "hyderabad",
    "mumbai",
    "delhi",
    "london",
    "new york",
    "tokyo",
    "paris",
    "sydney",
    "beijing",
    "moscow",
    "berlin",
    "bangkok",
    "los angeles",
    "seoul",
    "cairo",
    "toronto",
    "chicago",
)

TACTICAL_ACTIONS: dict[str, str] = {
    # Mode
    "activate tactical mode": "tactical_mode",
    "tactical mode": "tactical_mode",
    "tactical command mode": "tactical_mode",
    "enable tactical mode": "tactical_mode",
    "show tactical overlay": "tactical_mode",
    # ISS
    "track iss": "tactical_iss",
    "show iss": "tactical_iss",
    "iss tracking": "tactical_iss",
    "where is the iss": "tactical_iss",
    "international space station": "tactical_iss",
    # Aircraft
    "show aircraft": "tactical_aircraft",
    "show aircraft near me": "tactical_aircraft",
    "track aircraft": "tactical_aircraft",
    "show flights": "tactical_aircraft",
    "live flight tracking": "tactical_aircraft",
    # Earthquakes
    "show earthquakes": "tactical_quakes",
    "earthquake monitor": "tactical_quakes",
    "seismic activity": "tactical_quakes",
    "show seismic data": "tactical_quakes",
    # Cyber threats
    "show cyber threats": "tactical_cyber",
    "cyber threat intelligence": "tactical_cyber",
    "show cyber attacks": "tactical_cyber",
    "cyber attack map": "tactical_cyber",
    "threat intelligence": "tactical_cyber",
    "show attack map": "tactical_cyber",
    # Space weather
    "show space weather": "tactical_space",
    "space weather": "tactical_space",
    "solar weather": "tactical_space",
    "geomagnetic storm": "tactical_space",
    "show kp index": "tactical_space",
    "solar wind": "tactical_space",
    # Marine
    "show marine vessels": "tactical_marine",
    "marine tracking": "tactical_marine",
    "track ships": "tactical_marine",
    "vessel tracking": "tactical_marine",
    "show ship traffic": "tactical_marine",
    # Weather radar
    "display weather radar": "tactical_weather",
    "show weather radar": "tactical_weather",
    "weather radar": "tactical_weather",
    "live weather": "tactical_weather",
    # All layers
    "enable all layers": "tactical_all",
    "all tactical layers": "tactical_all",
    "full tactical display": "tactical_all",
    "maximum tactical": "tactical_all",
}

ACTIVATION_ACTIONS: dict[str, str] = {
    # Wake
    "hesa wake up": "wake_jarvis",
    "wake up hesa": "wake_jarvis",
    "activate hesa": "wake_jarvis",
    "hey hesa": "wake_jarvis",
    # Standby
    "hesa go to sleep": "sleep_mode",
    "hesa standby": "sleep_mode",
    "hesa hibernate": "sleep_mode",
    "sleep mode": "sleep_mode",
    # Emergency
    "hesa emergency": "emergency_mode",
    "emergency mode": "emergency_mode",
    "red alert": "emergency_mode",
    # Status
    "hesa status":               "status_report",
    "system status":               "status_report",
    "all systems check":           "status_report",
    # Language modes
    "telugu mode":                 "telugu_mode",
    "english mode":                "english_mode",
    "auto language mode":          "auto_language_mode",
}


def normalize_command(command: str) -> str:
    """Return a lowercase ASCII command string suitable for matching."""

    lowered = (command or "").strip().lower()
    decomposed = unicodedata.normalize("NFKD", lowered)
    ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    ascii_text = re.sub(r"['`]", " ", ascii_text)
    ascii_text = re.sub(r"[^a-z0-9:/?&.=+\- ]+", " ", ascii_text)
    return re.sub(r"\s+", " ", ascii_text).strip()


def _payload(action: str, params: dict[str, Any] | None = None, response: str = "") -> ActionPayload:
    return {"action": action, "params": params or {}, "response": response}


def _match_direct_action(normalized: str) -> ActionPayload | None:
    for patterns, action in DIRECT_ACTION_PATTERNS:
        if any(pattern in normalized for pattern in patterns):
            return _payload(action)
    return None


def _match_open_app(normalized: str) -> ActionPayload | None:
    for alias in SORTED_APP_ALIASES:
        app = APP_ALIASES[alias]
        if normalized in {f"{alias} open", f"open {alias}", f"launch {alias}"}:
            return _payload("open_app", {"app": app}, f"Opening {app}, sir.")
    return None


def _normalize_url(value: str) -> str:
    value = value.strip()
    if value.startswith(("http://", "https://")):
        return value
    return f"https://{value}"


def _match_open_web(normalized: str) -> ActionPayload | None:
    prefixes = ("open ", "go to ")
    for prefix in prefixes:
        if not normalized.startswith(prefix):
            continue
        target = normalized[len(prefix) :].strip()
        if target in WEBSITE_ALIASES:
            return _payload("open_web", {"url": WEBSITE_ALIASES[target]}, f"Opening {target}, sir.")
        if "." in target and " " not in target:
            return _payload("open_web", {"url": _normalize_url(target)}, f"Opening {target}, sir.")
    return None


def _strip_trailing_search_word(query: str) -> str:
    for suffix in TRAILING_SEARCH_WORDS:
        if query.endswith(suffix):
            return query[: -len(suffix)].strip()
    return query.strip()


def _match_google_search(normalized: str) -> ActionPayload | None:
    prefixes = ("google ", "search google for ", "google search ", "search for ", "look up ", "find ")
    for prefix in prefixes:
        if normalized.startswith(prefix):
            query = _strip_trailing_search_word(normalized[len(prefix) :])
            if query:
                return _payload("search_google", {"query": query}, f"Searching Google for {query}, sir.")
    return None


def _match_control_action(normalized: str) -> ActionPayload | None:
    if normalized in WINDOW_ACTIONS:
        return _payload(WINDOW_ACTIONS[normalized])
    if normalized in KEY_ACTIONS:
        return _payload("press_key", {"key": KEY_ACTIONS[normalized]})
    return None


def _match_spotify_action(normalized: str) -> ActionPayload | None:
    if normalized in SPOTIFY_ACTIONS:
        return _payload(SPOTIFY_ACTIONS[normalized])
    if normalized.startswith("play ") and normalized.endswith(" on spotify"):
        query = normalized.removeprefix("play ").removesuffix(" on spotify").strip()
        if query:
            return _payload("spotify_search", {"query": query}, f"Playing {query} on Spotify, sir.")
    return None


def _match_note_write(normalized: str) -> ActionPayload | None:
    prefixes = ("remember ", "add note ", "note ")
    for prefix in prefixes:
        if normalized.startswith(prefix):
            text = normalized[len(prefix) :].strip()
            if text:
                return _payload("add_note", {"text": text})
    return None


def _match_world_map(normalized: str) -> ActionPayload | None:
    """Match JARVIS world map voice commands."""
    # Direct action matches
    if normalized in WORLD_MAP_ACTIONS:
        action = WORLD_MAP_ACTIONS[normalized]
        return _payload(action, {"command": normalized}, f"Engaging {normalized}, sir.")
    # Fly-to / zoom-to patterns
    for prefix in WORLD_MAP_FLY_PREFIXES:
        if normalized.startswith(prefix):
            target = normalized[len(prefix) :].strip()
            if target in WORLD_MAP_COUNTRIES:
                return _payload(
                    "worldmap_fly_to",
                    {"location": target, "command": normalized},
                    f"Navigating to {target.title()}, sir.",
                )
    return None


def _match_tactical(normalized: str) -> ActionPayload | None:
    """Match AI Tactical Command Mode voice commands."""
    if normalized in TACTICAL_ACTIONS:
        action = TACTICAL_ACTIONS[normalized]
        label = normalized.replace("_", " ").title()
        return _payload(action, {"command": normalized}, f"Activating {label}, sir.")
    return None


def _match_activation(normalized: str) -> ActionPayload | None:
    """Match smart activation / standby / mode commands."""
    if normalized in ACTIVATION_ACTIONS:
        action = ACTIVATION_ACTIONS[normalized]
        if action == "telugu_mode":
            from JARVIS.core.memory.memory_preferences import set_preference
            set_preference("language_mode", "telugu")
            set_preference("preferred_language", "telugu")
            return _payload("talk", {}, "Telugu mode enabled sir.")
        if action == "english_mode":
            from JARVIS.core.memory.memory_preferences import set_preference
            set_preference("language_mode", "english")
            set_preference("preferred_language", "english")
            return _payload("talk", {}, "English mode enabled sir.")
        if action == "auto_language_mode":
            from JARVIS.core.memory.memory_preferences import set_preference
            set_preference("language_mode", "auto")
            return _payload("talk", {}, "Automatic language detection enabled sir.")
        return _payload(action, {"command": normalized}, f"Processing {action.replace('_', ' ')}, sir.")
    return None


def _match_close_app(normalized: str) -> ActionPayload | None:
    for alias in SORTED_APP_ALIASES:
        app = APP_ALIASES[alias]
        if normalized in {f"{alias} close", f"close {alias}", f"exit {alias}", f"quit {alias}"}:
            return _payload("close_app", {"app": app}, f"Closing {app}, sir.")
    return None


def _match_switch_window(normalized: str) -> ActionPayload | None:
    if normalized in {"switch window", "change window", "next window", "switch windows"}:
        return _payload("switch_window", {}, "Switching window, sir.")
    return None


def _match_search_files(normalized: str) -> ActionPayload | None:
    prefixes = ("find file ", "find files for ", "search computer for ")
    for prefix in prefixes:
        if normalized.startswith(prefix):
            query = normalized[len(prefix) :].strip()
            if query:
                return _payload("search_files", {"query": query}, f"Searching the system for {query}, sir.")
    return None


def _match_volume_control(normalized: str) -> ActionPayload | None:
    if normalized in {"mute", "mute volume", "silence"}:
        return _payload("control_volume", {"action": "mute"}, "Muting system audio, sir.")
    if normalized in {"unmute", "unmute volume"}:
        return _payload("control_volume", {"action": "unmute"}, "Restoring audio volume, sir.")
    match = re.search(r"(?:set )?volume (?:to )?(\d+)", normalized)
    if match:
        level = int(match.group(1))
        return _payload("control_volume", {"action": "set", "level": level}, f"Setting volume to {level} percent, sir.")
    if any(p in normalized for p in ["volume up", "increase volume", "louder"]):
        return _payload("control_volume", {"action": "up"}, "Increasing volume, sir.")
    if any(p in normalized for p in ["volume down", "decrease volume", "quieter"]):
        return _payload("control_volume", {"action": "down"}, "Lowering volume, sir.")
    return None


def _match_brightness_control(normalized: str) -> ActionPayload | None:
    match = re.search(r"(?:set )?brightness (?:to )?(\d+)", normalized)
    if match:
        level = int(match.group(1))
        return _payload("control_brightness", {"level": level}, f"Setting brightness to {level} percent, sir.")
    if any(p in normalized for p in ["brightness up", "increase brightness", "brighter"]):
        return _payload("control_brightness", {"action": "up"}, "Increasing brightness, sir.")
    if any(p in normalized for p in ["brightness down", "decrease brightness", "dimmer"]):
        return _payload("control_brightness", {"action": "down"}, "Dimming screen brightness, sir.")
    return None


def _match_wifi_control(normalized: str) -> ActionPayload | None:
    if normalized in {"enable wifi", "turn on wifi", "wifi on", "activate wifi"}:
        return _payload("control_wifi", {"action": "enable"}, "Enabling Wi-Fi adapter, sir.")
    if normalized in {"disable wifi", "turn off wifi", "wifi off", "deactivate wifi"}:
        return _payload("control_wifi", {"action": "disable"}, "Disabling Wi-Fi adapter, sir.")
    return None


def _match_bluetooth_control(normalized: str) -> ActionPayload | None:
    if normalized in {"enable bluetooth", "turn on bluetooth", "bluetooth on", "activate bluetooth"}:
        return _payload("control_bluetooth", {"action": "enable"}, "Enabling Bluetooth service, sir.")
    if normalized in {"disable bluetooth", "turn off bluetooth", "bluetooth off", "deactivate bluetooth"}:
        return _payload("control_bluetooth", {"action": "disable"}, "Disabling Bluetooth service, sir.")
    return None


def _match_media_control(normalized: str) -> ActionPayload | None:
    if normalized in {"play", "pause", "play music", "pause music", "toggle play"}:
        return _payload("control_media", {"action": "play_pause"}, "Toggling media playback, sir.")
    if normalized in {"next", "next track", "next song", "skip song"}:
        return _payload("control_media", {"action": "next"}, "Skipping to next track, sir.")
    if normalized in {"previous", "previous track", "previous song", "go back"}:
        return _payload("control_media", {"action": "prev"}, "Playing previous track, sir.")
    if normalized in {"stop", "stop music"}:
        return _payload("control_media", {"action": "stop"}, "Stopping media playback, sir.")
    return None


def _match_hardware_stats(normalized: str) -> ActionPayload | None:
    if normalized in {
        "hardware stats",
        "hardware status",
        "system usage",
        "system diagnostic",
        "system status",
        "diagnostics",
        "check system status",
    }:
        return _payload("get_hardware_stats", {}, "Querying hardware monitoring services, sir.")
    return None


def _match_pronunciation_setting(raw_command: str) -> ActionPayload | None:
    cmd = raw_command.strip()

    # Pattern 1: My name is X. Pronounce it like/as Y
    m1 = re.search(r"my name is ([a-zA-Z0-9_\-]+)\.? pronounce (?:it|name)? (?:like|as) (.+)", cmd, re.IGNORECASE)
    if m1:
        name = m1.group(1).strip()
        pron = m1.group(2).strip()
        try:
            from JARVIS.core.voice.pronunciation_engine import get_pronunciation_engine

            get_pronunciation_engine().set_native_script_pronunciation(name, pron)
        except Exception:
            pass
        return _payload(
            "set_personal_pronunciation",
            {"name": name, "replacement": pron},
            f"Understood. I will pronounce {name} as {pron} from now on, sir.",
        )

    # Pattern 2: Pronounce X as/like Y
    m2 = re.search(r"pronounce ([a-zA-Z0-9_\-]+) (?:as|like) (.+)", cmd, re.IGNORECASE)
    if m2:
        name = m2.group(1).strip()
        pron = m2.group(2).strip()
        try:
            from JARVIS.core.voice.pronunciation_engine import get_pronunciation_engine

            get_pronunciation_engine().set_native_script_pronunciation(name, pron)
        except Exception:
            pass
        return _payload(
            "set_personal_pronunciation",
            {"name": name, "replacement": pron},
            f"Understood. I will pronounce {name} as {pron} from now on, sir.",
        )

    return None


def _match_startup_registration(normalized: str) -> ActionPayload | None:
    if normalized in {"register startup", "enable startup", "activate auto start", "enable auto boot"}:
        return _payload("register_startup", {"enabled": True}, "Registering HESA at Windows startup, sir.")
    if normalized in {"remove startup", "disable startup", "disable auto start", "disable auto boot"}:
        return _payload("register_startup", {"enabled": False}, "Removing HESA from Windows startup, sir.")
    return None


def _match_cyber_and_ai(normalized: str) -> ActionPayload | None:
    """Match cyber security intelligence and multi-AI orchestration commands."""
    cmd = normalized.lower().strip().rstrip(".")
    if cmd.startswith("hesa "):
        cmd = cmd[5:].strip().rstrip(".")

    # AI Orchestrator patterns
    for prov in ["chatgpt", "gemini", "claude", "grok", "deepseek", "ollama"]:
        for prefix in [f"ask {prov} ", f"use {prov} "]:
            if cmd.startswith(prefix):
                prompt = cmd[len(prefix) :].strip()
                return _payload("ai_query", {"provider": prov, "prompt": prompt}, f"Querying {prov.title()} with prompt: {prompt}, sir.")

    # Debate patterns
    for prefix in ["compare all ais ", "compare ais ", "ai debate "]:
        if cmd.startswith(prefix):
            prompt = cmd[len(prefix) :].strip()
            return _payload("ai_debate", {"prompt": prompt}, "Initiating multi-AI debate session, sir.")

    # Failover patterns
    if cmd.startswith("query with failover "):
        prompt = cmd[len("query with failover ") :].strip()
        return _payload("ai_failover", {"prompt": prompt})

    # Cyber Security patterns
    if cmd in [
        "analyze logs",
        "analyze security logs",
        "analyze today s security logs",
        "analyze today's security logs",
        "audit logs",
        "analyze these logs",
    ]:
        return _payload("cyber_analyze_logs")

    if cmd in ["suspicious process check", "process audit", "suspicious processes", "check processes"]:
        return _payload("cyber_suspicious_processes")

    if cmd in ["prepare daily soc report", "soc report", "generate soc report", "create a soc report", "create soc report"]:
        return _payload("cyber_generate_soc")

    if cmd in ["create incident timeline", "incident timeline", "timeline audit"]:
        return _payload("cyber_create_timeline")

    if cmd in ["compare mitre techniques", "compare mitre", "mitre comparison"]:
        return _payload("cyber_compare_mitre")

    if cmd in ["review security architecture", "review architecture", "security architecture review", "review this security architecture"]:
        return _payload("cyber_review_arch")

    if cmd in [
        "threat landscape",
        "summarize threat landscape",
        "global threat landscape",
        "summarize today s threat landscape",
        "summarize today's threat landscape",
    ]:
        return _payload("cyber_threat_landscape")

    if cmd in ["explain packet capture", "pcap analysis", "analyze packet capture"]:
        return _payload("cyber_explain_pcap")

    if cmd in ["prepare me for security plus", "prepare me for security+", "security plus quiz", "security+ quiz"]:
        return _payload("cyber_prepare_secplus")

    if cmd in ["teach cloud security", "cloud security", "container security", "teach me cloud security"]:
        return _payload("cyber_teach_cloud")

    if cmd in ["explain dns", "dns query", "what is dns", "explain dns."]:
        return _payload("cyber_explain_dns")

    if cmd in ["teach me linux", "teach linux", "learn linux", "linux tutorial", "teach me linux."]:
        return _payload("cyber_teach_linux")

    if cmd in ["explain owasp top 10", "explain owasp", "owasp top 10", "owasp", "explain owasp top 10."]:
        return _payload("cyber_explain_owasp")

    if cmd in ["explain zero trust", "zero trust", "what is zero trust", "explain zero trust."]:
        return _payload("cyber_explain_zero_trust")

    # CVE explanation patterns
    cve_match = re.search(r"\bcve-\d{4}-\d+", cmd)
    if cve_match:
        cve_id = cve_match.group(0)
        return _payload("cyber_explain_cve", {"cve_id": cve_id})

    # Generic or specific CVE summarization
    if cmd in ["summarize this cve", "summarize cve", "cve summary"]:
        return _payload("cyber_explain_cve", {"cve_id": ""})

    # Malware behavior patterns
    malware_match = re.search(r"explain (?:this )?(\w+)? ?malware behavior|explain (?:this )?(\w+) behavior", cmd)
    if malware_match:
        m_name = malware_match.group(1) or malware_match.group(2) or ""
        return _payload("cyber_explain_malware", {"malware": m_name})

    if cmd in ["explain this malware behavior", "explain malware behavior"]:
        return _payload("cyber_explain_malware", {"malware": ""})

    # Roadmap patterns
    for prefix in [
        "learning roadmap for ",
        "roadmap for ",
        "prepare a ",
        "prepare ",
        "create a ",
        "create ",
    ]:
        if cmd.startswith(prefix):
            suffix = cmd[len(prefix) :].strip()
            topic = suffix
            if topic.endswith(" roadmap"):
                topic = topic[:-8].strip()
            elif topic.endswith(" study plan"):
                topic = topic[:-11].strip()

            # If the command makes sense as a roadmap command
            if "roadmap" in cmd or "study plan" in cmd:
                return _payload("cyber_learning_roadmap", {"topic": topic})

    return None


def route_local_intent(command: str) -> ActionPayload | None:
    """Return an action payload for common commands that do not need an LLM."""

    from JARVIS.core.system.utils.telugu_formatter import detect_language, match_telugu_intent, normalize_telugu_command

    if detect_language(command) == "telugu":
        # First try database matching
        match_res = match_telugu_intent(command)
        if match_res:
            intent = match_res.get("intent")
            target = match_res.get("target")
            confidence = match_res.get("confidence", 0.0)

            if confidence >= 0.60:
                if intent == "talk":
                    return _payload("talk", {}, target)
                elif intent == "system_query":
                    if target == "get_time":
                        return _payload("get_time")
                    elif target == "get_date":
                        return _payload("get_date")
                    elif target == "get_battery":
                        return _payload("get_battery")
                    elif target == "get_cpu":
                        return _payload("get_cpu")
                    elif target == "get_ram":
                        return _payload("get_ram")
                    elif target == "screenshot":
                        return _payload("screenshot")
                    elif target == "read_clipboard":
                        return _payload("read_clipboard")
                    elif target == "summarize_clipboard":
                        return _payload("summarize_clipboard")
                    elif target == "volume_up":
                        return _payload("control_volume", {"action": "up"}, "Increasing volume, sir.")
                    elif target == "volume_down":
                        return _payload("control_volume", {"action": "down"}, "Lowering volume, sir.")
                    elif target.startswith("open "):
                        app = target.removeprefix("open ").strip().lower()
                        if app in WEBSITE_ALIASES:
                            return _payload("open_web", {"url": WEBSITE_ALIASES[app]}, f"Opening {app}, sir.")
                        if "." in app and " " not in app:
                            return _payload("open_web", {"url": _normalize_url(app)}, f"Opening {app}, sir.")
                        app_name = APP_ALIASES.get(app, app)
                        return _payload("open_app", {"app": app_name}, f"Opening {app_name}, sir.")
                    elif target.startswith("close "):
                        app = target.removeprefix("close ").strip().lower()
                        app_name = APP_ALIASES.get(app, app)
                        return _payload("close_app", {"app": app_name}, f"Closing {app_name}, sir.")
                elif intent == "learned_command":
                    res = route_local_intent(target)
                    if res:
                        return res

        # Fallback to normalize_telugu_command
        command = normalize_telugu_command(command)

    pron_action = _match_pronunciation_setting(command)
    if pron_action is not None:
        return pron_action

    normalized = normalize_command(command)
    if not normalized:
        return None

    if normalized == "what are you doing":
        from JARVIS.core.memory.memory_preferences import get_preference

        resp = (
            "Mee commands kosam ready ga unnanu sir."
            if get_preference("preferred_language") == "telugu"
            else "I am processing system analytics and standing by for your instructions, sir."
        )
        return _payload("talk", {}, resp)
    if normalized == "how are you":
        from JARVIS.core.memory.memory_preferences import get_preference

        resp = (
            "Avunu sir, anni systems normal ga pani chestunnayi."
            if get_preference("preferred_language") == "telugu"
            else "All systems are operational and performing within optimal parameters, sir."
        )
        return _payload("talk", {}, resp)
    if normalized == "thanks":
        from JARVIS.core.memory.memory_preferences import get_preference

        resp = "Welcome sir." if get_preference("preferred_language") == "telugu" else "You are very welcome, sir."
        return _payload("talk", {}, resp)

    for matcher in (
        _match_cyber_and_ai,
        _match_tactical,
        _match_activation,
        _match_world_map,
        _match_note_write,
        _match_startup_registration,
        _match_close_app,
        _match_switch_window,
        _match_search_files,
        _match_control_action,
        _match_spotify_action,
        _match_volume_control,
        _match_brightness_control,
        _match_wifi_control,
        _match_bluetooth_control,
        _match_media_control,
        _match_hardware_stats,
        _match_open_app,
        _match_open_web,
        _match_google_search,
        _match_direct_action,
    ):
        action = matcher(normalized)
        if action is not None:
            # Mark dangerous actions that require user confirmation (Requirement #7)
            act_name = action.get("action", "")
            if act_name in {"shutdown", "restart", "delete_file", "format_drive", "kill_process"}:
                action["requires_confirmation"] = True
            return action
    return None


def classify_intent(command: str) -> tuple[str, ActionPayload | str]:
    """Classify command into one of 5 categories:
    - LOCAL_COMMAND
    - SYSTEM_CONTROL
    - MEMORY_QUERY
    - AUTOMATION
    - AI_QUERY

    Execution decision latency: < 100ms.
    """
    if not command or not isinstance(command, str):
        return ("LOCAL_COMMAND", _payload("talk", {}, ""))

    cmd_low = command.lower().strip()

    # 1. Memory Queries & Profile Preferences
    from JARVIS.core.memory.memory_preferences import detect_and_save_preference

    mem_response = detect_and_save_preference(command)
    if mem_response:
        return ("MEMORY_QUERY", _payload("talk", {}, mem_response))

    if any(p in cmd_low for p in ["my favorite", "my name is", "what is my name", "what is my favorite"]):
        return ("MEMORY_QUERY", _payload("talk", {}, ""))

    # 2. Local Intent Router
    local_action = route_local_intent(command)
    if local_action:
        act_name = local_action.get("action", "")
        # System control & destructive commands
        if act_name in {"shutdown", "restart", "delete_file", "format_drive", "kill_process", "system_settings", "registry"}:
            local_action["requires_confirmation"] = True
            return ("SYSTEM_CONTROL", local_action)
        return ("LOCAL_COMMAND", local_action)

    # 3. Automation workflows
    if any(k in cmd_low for k in ["workflow", "automation", "schedule", "routine", "soc report"]):
        return ("AUTOMATION", _payload("automation", {"command": command}))

    # 4. AI Query Classification
    coding_keywords = {
        "code",
        "program",
        "function",
        "compile",
        "debug",
        "script",
        "python",
        "javascript",
        "java",
        "c++",
        "c#",
        "html",
        "css",
        "rust",
        "golang",
        "typescript",
        "git",
        "database",
        "sql",
    }
    if any(k in cmd_low for k in coding_keywords):
        return ("AI_QUERY", "coding")

    reasoning_keywords = {"solve", "analyze", "math", "logic", "reason", "why", "compare", "proof", "evaluate"}
    if any(k in cmd_low for k in reasoning_keywords):
        return ("AI_QUERY", "reasoning")

    return ("AI_QUERY", "general")


__all__ = ["normalize_command", "route_local_intent", "classify_intent"]
