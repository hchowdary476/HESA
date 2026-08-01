"""Compatibility wrappers for Groq-backed command analysis and summarization with lazy loading."""

from __future__ import annotations

import os

from dotenv import load_dotenv

from JARVIS.core.system.observability import record_runtime_event
from JARVIS.providers import GroqProvider, ProviderRequest, ProviderRouter
from JARVIS.providers.groq import (
    DEFAULT_GROQ_MODEL,
    GROQ_COOLDOWN_SECONDS,
    activate_groq_cooldown,
    extract_action_json,
    is_groq_cooling_down,
)
from JARVIS.core.security.jarvis_admin import format_actionable_message
from JARVIS.core.system.utils.jarvis_logging import get_logger

# Lazy import Groq to avoid 661ms + 991ms startup penalty
try:
    from groq import GroqError
except ImportError:
    GroqError = RuntimeError

from JARVIS.core.system.utils.env_helper import find_env_file

load_dotenv(find_env_file())

logger = get_logger("commands")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = None
_groq_initialized = False

def get_groq_client():
    """Lazy load Groq client on first use (saves 1.6s at startup)."""
    global client, _groq_initialized
    
    if _groq_initialized:
        return client
    
    _groq_initialized = True
    
    if not GROQ_API_KEY:
        logger.warning("Groq API key not found. Running local backup routing, sir.")
        return None
    
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        logger.info("Groq API client initialized (lazy loaded).")
        return client
    except ImportError:
        logger.warning("Groq library not installed. Running local backup routing, sir.")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Groq client: {e}")
        return None

SYSTEM_PROMPT = """
You are HESA, Tony Stark's personal AI assistant from Iron Man.
You are highly intelligent, witty, and always professional.
You speak in a formal British manner and address the user as "sir".
You remember the user's preferences and adapt to their habits.
You are proactive — if you notice patterns, mention them.
You occasionally make subtle, dry humor remarks.
Always be concise but complete in your responses.
You are HESA, an AI assistant like in Iron Man.
Think carefully before responding. Always return valid JSON.
Analyze the user's command and return ONLY valid JSON.

IMPORTANT: If the command contains multiple tasks (e.g. "open chrome and go to youtube"),
return a list of actions. Otherwise return a single action object.

Single action format:
{"action": "ACTION_NAME", "params": {}, "response": "What HESA says"}

Multiple actions format:
{"actions": [{"action": "ACTION_NAME", "params": {}}, {"action": "ACTION_NAME", "params": {}}], "response": "What HESA says"}

Available actions:
- "open_app": {"app": "chrome|steam|epic|spotify|vscode|notepad|calculator|explorer|taskmgr|discord|whatsapp|word|excel|powerpoint|paint|cmd"}
- "open_web": {"url": "full URL"}
- "search_google": {"query": "search term"}
- "get_time": {}
- "get_date": {}
- "get_battery": {}
- "get_ram": {}
- "get_cpu": {}
- "screenshot": {}
- "read_clipboard": {}
- "summarize_clipboard": {}
- "type_text": {"text": "text to type"}
- "press_key": {"key": "enter|esc|space|tab|ctrl+c|ctrl+v|ctrl+z|ctrl+s|alt+f4|win|f5|delete|volumeup|volumedown|volumemute"}
- "mouse_click": {"x": 0, "y": 0, "button": "left|right|double"}
- "scroll": {"direction": "up|down", "amount": 3}
- "minimize_all": {}
- "maximize_window": {}
- "close_window": {}
- "lock_screen": {}
- "shutdown": {}
- "restart": {}
- "sleep": {}
- "spotify_play": {}
- "spotify_pause": {}
- "spotify_next": {}
- "spotify_prev": {}
- "spotify_volume": {"level": 50}
- "spotify_search": {"query": "song or artist name"}
- "spotify_current": {}
- "memory_stats": {}
- "memory_habits": {}
- "memory_health": {}
- "memory_summary": {}
- "prune_memory": {}
- "add_note": {"text": "note text"}
- "read_notes": {}
- "talk": {}
"""

import socket
import threading
import time
import json
import datetime
import urllib.request
import urllib.parse
from JARVIS.core.memory import build_context_prompt

# Background internet check caching
_cached_internet_status = True
_cached_latency_ms = 0.0
_internet_check_thread_started = False
_internet_check_lock = threading.Lock()

def _internet_check_loop():
    global _cached_internet_status, _cached_latency_ms
    while True:
        try:
            start = time.perf_counter()
            socket.create_connection(("1.1.1.1", 53), timeout=0.2).close()
            latency = (time.perf_counter() - start) * 1000.0
            with _internet_check_lock:
                _cached_internet_status = True
                _cached_latency_ms = round(latency, 1)
        except OSError:
            with _internet_check_lock:
                _cached_internet_status = False
                _cached_latency_ms = 0.0
        time.sleep(5.0)

def is_internet_available() -> bool:
    global _internet_check_thread_started
    if not _internet_check_thread_started:
        _internet_check_thread_started = True
        t = threading.Thread(target=_internet_check_loop, name="jarvis_internet_check", daemon=True)
        t.start()
    with _internet_check_lock:
        return _cached_internet_status

def get_cached_latency() -> float:
    with _internet_check_lock:
        return _cached_latency_ms

def update_provider_stats(status: dict, provider: str, success: bool, elapsed_ms: float):
    if "stats" not in status:
        status["stats"] = {}
    for p in ["GROQ", "GEMINI", "OLLAMA"]:
        if p not in status["stats"]:
            status["stats"][p] = {
                "response_time": "0ms",
                "last_success": "Never",
                "last_failure": "Never"
            }
    p_stats = status["stats"][provider.upper()]
    p_stats["response_time"] = f"{elapsed_ms:.1f}ms"
    now_str = datetime.datetime.now().isoformat()
    if success:
        p_stats["last_success"] = now_str
    else:
        p_stats["last_failure"] = now_str

def get_hybrid_ai_status() -> dict:
    path = os.path.join("logs", "hybrid_ai_status.json")
    status_data = None
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                status_data = json.load(f)
        except Exception:
            pass
            
    # Default initial stats
    online = is_internet_available()
    has_groq = bool(os.getenv("GROQ_API_KEY"))
    has_gemini = bool(os.getenv("GEMINI_API_KEY"))
    has_ollama = bool(os.getenv("JARVIS_LOCAL_LLM_URL"))
    
    current = "GROQ" if has_groq else "GEMINI" if has_gemini else "OLLAMA"
    
    if not status_data or not isinstance(status_data, dict):
        status_data = {
            "network_status": "ONLINE" if online else "OFFLINE",
            "current_provider": current,
            "current_ai_provider": f"AI Provider: {current}",
            "groq_status": "ACTIVE" if has_groq else "UNCONFIGURED",
            "gemini_status": "ACTIVE" if has_gemini else "UNCONFIGURED",
            "ollama_status": "ACTIVE" if has_ollama else "UNCONFIGURED",
            "response_time": "0ms",
            "last_success": "Never",
            "last_failure": "Never",
            "stats": {
                "GROQ": {"response_time": "0ms", "last_success": "Never", "last_failure": "Never"},
                "GEMINI": {"response_time": "0ms", "last_success": "Never", "last_failure": "Never"},
                "OLLAMA": {"response_time": "0ms", "last_success": "Never", "last_failure": "Never"}
            }
        }
    else:
        # Merge/ensure stats dictionary exists
        if "stats" not in status_data:
            status_data["stats"] = {
                "GROQ": {"response_time": "0ms", "last_success": "Never", "last_failure": "Never"},
                "GEMINI": {"response_time": "0ms", "last_success": "Never", "last_failure": "Never"},
                "OLLAMA": {"response_time": "0ms", "last_success": "Never", "last_failure": "Never"}
            }
    return status_data


def save_hybrid_ai_status(status: dict):
    os.makedirs("logs", exist_ok=True)
    path = os.path.join("logs", "hybrid_ai_status.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(status, f, indent=2)
    except Exception:
        pass


def _env_flag_enabled(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def groq_enabled() -> bool:
    """Return whether optional Groq routing is enabled by configuration."""
    return _env_flag_enabled("JARVIS_ENABLE_GROQ", default=False)


def _resolve_client(provided_client):
    return provided_client if provided_client is not None else client


def get_groq_model() -> str:
    """Return the configured free-first Groq routing model."""
    return os.getenv("JARVIS_GROQ_MODEL", DEFAULT_GROQ_MODEL).strip() or DEFAULT_GROQ_MODEL


def _missing_groq_action() -> dict:
    return {
        "action": "talk",
        "params": {},
        "response": format_actionable_message(
            "Groq API key not found. Running local backup routing, sir.",
            "AI command routing is active using local fallback systems.",
            "Add GROQ_API_KEY to your .env file or enable Gemini/Ollama for alternative options.",
        ),
    }


def _local_fallback_action() -> dict:
    return {
        "action": "talk",
        "params": {},
        "response": format_actionable_message(
            "I am running on local fallback routines, sir.",
            "The command could not be processed by cloud AI engines and local fallback is active.",
            "Please check settings if you want to configure Groq or Gemini cloud options.",
        ),
    }


def get_ollama_model(base_url: str) -> str:
    from urllib.parse import urlparse
    parsed = urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    tags_url = f"{origin}/api/tags"
    
    try:
        req = urllib.request.Request(tags_url, method="GET")
        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                models = data.get("models", [])
                if models:
                    model_name = models[0].get("name")
                    if model_name:
                        return model_name
    except Exception as e:
        logger.warning(f"Ollama tags model detection failed: {e}")
        
    return "llama3"


def query_gemini(command: str, context: str = "", system_prompt: str = SYSTEM_PROMPT) -> dict | None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    system = f"{context}\n\n{system_prompt}" if context else system_prompt
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": command}
                ]
            }
        ],
        "systemInstruction": {
            "parts": [
                {"text": system}
            ]
        }
    }
    
    try:
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, 
            data=req_data, 
            headers={"Content-Type": "application/json"}, 
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                body = response.read().decode("utf-8")
                res_json = json.loads(body)
                content = res_json["candidates"][0]["content"]["parts"][0]["text"]
                try:
                    return extract_action_json(content)
                except Exception:
                    return {
                        "action": "talk",
                        "params": {},
                        "response": content
                    }
    except Exception as e:
        logger.warning(f"Gemini API query failed: {e}")
        raise e


def query_ollama(command: str, context: str = "", system_prompt: str = SYSTEM_PROMPT) -> dict | None:
    local_url = os.getenv("JARVIS_LOCAL_LLM_URL", "").strip()
    if not local_url:
        return None
        
    base_url = local_url.rstrip("/")
    if not base_url.endswith("/v1/chat/completions") and not base_url.endswith("/chat/completions"):
        if "/v1" in base_url:
            url = f"{base_url}/chat/completions"
        else:
            url = f"{base_url}/v1/chat/completions"
    else:
        url = base_url
        
    model = get_ollama_model(base_url)
    system = f"{context}\n\n{system_prompt}" if context else system_prompt
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": command}
        ],
        "temperature": 0.1,
        "max_tokens": 300
    }
    
    try:
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, 
            data=req_data, 
            headers={"Content-Type": "application/json"}, 
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                body = response.read().decode("utf-8")
                res_json = json.loads(body)
                content = res_json["choices"][0]["message"]["content"]
                try:
                    return extract_action_json(content)
                except Exception:
                    return {
                        "action": "talk",
                        "params": {},
                        "response": content
                    }
    except Exception as e:
        logger.warning(f"Ollama local LLM query failed: {e}")
        raise e


def query_local_rules(command: str) -> dict:
    lowered = command.lower()
    from JARVIS.core.memory.memory_preferences import get_preference
    from JARVIS.core.system.utils.telugu_formatter import detect_language
    
    pref_lang = get_preference("preferred_language")
    cmd_lang = detect_language(command)
    is_telugu = (cmd_lang == "telugu") or (pref_lang == "telugu" and cmd_lang == "telugu")

    if "what is ai" in lowered:
        resp = "Artificial Intelligence (AI), sir, is the simulation of human intelligence processes by machines, especially computer systems. It allows systems to learn, reason, and self-correct."
    elif "ai ante enti" in lowered or "ai ante yenti" in lowered:
        resp = "Artificial Intelligence ante machines manushula la nerchukoni decisions teesukune technology sir."
    elif "hello" in lowered or "hi" in lowered or "hey" in lowered:
        if is_telugu:
            resp = "Namaskaram sir. HESA siddhanga undi. Mee commands kosam ready ga unnanu sir."
        else:
            resp = "Hello, sir. Local neural links are online and standby. How may I assist you?"
    elif "who are you" in lowered or "evaru nuvvu" in lowered:
        if is_telugu:
            resp = "Nenu HESA ni sir, mee personal cybernetic assistant. Naa cloud connection online ledu, nenu local ga run avtunnanu sir."
        else:
            resp = "I am HESA, your personal cybernetic assistant. My cloud connection is currently offline, so I am running on local fallback routines, sir."
    elif "joke" in lowered:
        if is_telugu:
            resp = "Enduku computer doctor daggara vellindi sir? Endukante daaniki virus vachindi!"
        else:
            resp = "Why did the computer go to the doctor, sir? Because it had a virus!"
    else:
        if is_telugu:
            resp = f"Mee command naku vachindi sir: '{command}'. Naa cloud connection offline undadam valla nenu deenni local ga process chestunnanu."
        else:
            resp = f"I have received your command: '{command}', sir. Since my cloud connection is offline, I am processing this request locally."
        
    return {
        "action": "talk",
        "params": {},
        "response": resp
    }


def query_local_llm(command: str) -> dict | None:
    """Connect to a local LLM server (like Ollama or LM Studio) and query the command."""
    try:
        return query_ollama(command)
    except Exception:
        return query_local_rules(command)


def analyze_with_groq(command, *, client=None, logger=logger):
    """Analyze a command through the Hybrid AI Routing system."""
    try:
        global GROQ_API_KEY
        GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        
        primary_provider = os.getenv("JARVIS_PRIMARY_AI", "GROQ").upper()
        secondary_provider = os.getenv("JARVIS_SECONDARY_AI", "GEMINI").upper()
        offline_provider = os.getenv("JARVIS_OFFLINE_AI", "OLLAMA").upper()
        
        online = is_internet_available()
        
        # Read/Initialize status
        status = get_hybrid_ai_status()
        status["network_status"] = "ONLINE" if online else "OFFLINE"
        
        has_groq = bool(GROQ_API_KEY)
        has_gemini = bool(os.getenv("GEMINI_API_KEY"))
        has_ollama = bool(os.getenv("JARVIS_LOCAL_LLM_URL"))
        
        status["groq_status"] = "ACTIVE" if has_groq else "UNCONFIGURED"
        status["gemini_status"] = "ACTIVE" if has_gemini else "UNCONFIGURED"
        status["ollama_status"] = "ACTIVE" if has_ollama else "UNCONFIGURED"
        
        if is_groq_cooling_down():
            status["groq_status"] = "COOLDOWN"
            
        try:
            context = build_context_prompt()
        except Exception:
            context = ""
            
        from JARVIS.core.memory.memory_preferences import get_preference
        active_system_prompt = SYSTEM_PROMPT
        if get_preference("preferred_language") == "telugu":
            active_system_prompt += """
            
            CRITICAL: The user has chosen to communicate in Telugu (or mixed Telugu-English).
            You MUST respond in natural, conversational Telugu (using Latin script, i.e., transliterated Telugu, unless they write in Telugu script, in which case use Telugu script).
            Follow these guidelines:
            - Speak like an educated native Telugu speaker from Andhra Pradesh/Telangana.
            - Use respectful, intelligent, helpful, calm, professional but friendly tone.
            - Avoid robotic translations and overly formal/literal language.
            - Use preferred conversational phrases like: "Sare sir", "Avunu sir", "Mee kosam", "Ippude", "Konchem wait cheyyandi", "Complete ayyindi", "Ready ga undi".
            """
            
        result = None
        provider_used = None
        start_time = time.perf_counter()
        
        if online:
            if not has_groq and not has_gemini:
                return _missing_groq_action()
            
            # Construct online order from priorities
            attempts = [primary_provider, secondary_provider, offline_provider]
            seen = set()
            online_order = []
            for p in attempts:
                if p not in seen:
                    seen.add(p)
                    online_order.append(p)
                    
            for prov in online_order:
                if prov == "GROQ":
                    if has_groq and not is_groq_cooling_down():
                        try:
                            g_start = time.perf_counter()
                            active_client = client if client is not None else get_groq_client()  # Lazy load client
                            provider = GroqProvider(
                                api_key=GROQ_API_KEY or "injected-client",
                                enabled=True,
                                model=get_groq_model(),
                                client=active_client,
                                activate_cooldown=activate_groq_cooldown,
                                system_prompt=active_system_prompt,
                            )
                            response = provider.analyze(
                                ProviderRequest(
                                    command=command,
                                    context=context,
                                    allow_cloud=True,
                                    allow_memory_context=True
                                )
                            )
                            g_elapsed = (time.perf_counter() - g_start) * 1000
                            if response.action:
                                result = response.action
                                provider_used = "GROQ"
                                status["groq_status"] = "ACTIVE"
                                update_provider_stats(status, "GROQ", success=True, elapsed_ms=g_elapsed)
                                break
                            elif response.error == "rate_limited":
                                status["groq_status"] = "COOLDOWN"
                                activate_groq_cooldown()
                                update_provider_stats(status, "GROQ", success=False, elapsed_ms=g_elapsed)
                            else:
                                status["groq_status"] = "OFFLINE"
                                update_provider_stats(status, "GROQ", success=False, elapsed_ms=g_elapsed)
                        except Exception as e:
                            g_elapsed = (time.perf_counter() - g_start) * 1000
                            logger.warning(f"Groq query exception: {e}")
                            status["groq_status"] = "OFFLINE"
                            activate_groq_cooldown()
                            update_provider_stats(status, "GROQ", success=False, elapsed_ms=g_elapsed)
                elif prov == "GEMINI":
                    if has_gemini:
                        try:
                            gem_start = time.perf_counter()
                            result = query_gemini(command, context=context, system_prompt=active_system_prompt)
                            gem_elapsed = (time.perf_counter() - gem_start) * 1000
                            if result:
                                provider_used = "GEMINI"
                                status["gemini_status"] = "ACTIVE"
                                update_provider_stats(status, "GEMINI", success=True, elapsed_ms=gem_elapsed)
                                break
                        except Exception as e:
                            gem_elapsed = (time.perf_counter() - gem_start) * 1000
                            logger.warning(f"Gemini fallback failed: {e}")
                            status["gemini_status"] = "OFFLINE"
                            update_provider_stats(status, "GEMINI", success=False, elapsed_ms=gem_elapsed)
                elif prov == "OLLAMA":
                    if has_ollama:
                        try:
                            oll_start = time.perf_counter()
                            result = query_ollama(command, context=context, system_prompt=active_system_prompt)
                            oll_elapsed = (time.perf_counter() - oll_start) * 1000
                            if result:
                                provider_used = "OLLAMA"
                                status["ollama_status"] = "ACTIVE"
                                update_provider_stats(status, "OLLAMA", success=True, elapsed_ms=oll_elapsed)
                                break
                        except Exception as e:
                            oll_elapsed = (time.perf_counter() - oll_start) * 1000
                            logger.warning(f"Ollama fallback failed: {e}")
                            status["ollama_status"] = "OFFLINE"
                            update_provider_stats(status, "OLLAMA", success=False, elapsed_ms=oll_elapsed)
            
            # If all prioritized providers failed
            if not result:
                result = query_local_rules(command)
                provider_used = "OLLAMA"
        else:
            # Offline path: try Offline settings (Ollama) -> Local Rules
            if offline_provider == "OLLAMA" and has_ollama:
                try:
                    oll_start = time.perf_counter()
                    result = query_ollama(command, context=context, system_prompt=active_system_prompt)
                    oll_elapsed = (time.perf_counter() - oll_start) * 1000
                    if result:
                        provider_used = "OLLAMA"
                        status["ollama_status"] = "ACTIVE"
                        update_provider_stats(status, "OLLAMA", success=True, elapsed_ms=oll_elapsed)
                except Exception as e:
                    oll_elapsed = (time.perf_counter() - oll_start) * 1000
                    logger.warning(f"Ollama offline fallback failed: {e}")
                    status["ollama_status"] = "OFFLINE"
                    update_provider_stats(status, "OLLAMA", success=False, elapsed_ms=oll_elapsed)
            
            if not result:
                result = query_local_rules(command)
                provider_used = "OLLAMA"
                
        # Calculate overall response metrics
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        if result:
            status["current_provider"] = provider_used
            status["current_ai_provider"] = f"AI Provider: {provider_used}"
            status["response_time"] = f"{elapsed_ms:.1f}ms"
            status["last_success"] = datetime.datetime.now().isoformat()
        else:
            result = query_local_rules(command)
            status["current_provider"] = "OLLAMA"
            status["current_ai_provider"] = "AI Provider: OLLAMA"
            status["response_time"] = f"{elapsed_ms:.1f}ms"
            status["last_failure"] = datetime.datetime.now().isoformat()
            
        save_hybrid_ai_status(status)
        return result
        
    except Exception as exc:
        logger.error(f"Top-level routing exception caught: {exc}")
        return query_local_rules(command)


def analyze_with_groq_direct(command: str, *, client=None) -> dict:
    """Send a command directly to Groq with no diagnostics side-effects (lazy loaded)."""
    global GROQ_API_KEY
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    
    active_client = get_groq_client() if client is None else client  # Lazy load
    provider = GroqProvider(
        api_key=GROQ_API_KEY or "injected-client",
        enabled=True,
        model=get_groq_model(),
        client=active_client,
        activate_cooldown=activate_groq_cooldown,
        system_prompt=SYSTEM_PROMPT,
    )
    try:
        response = provider.analyze(ProviderRequest(command=command, allow_cloud=True, allow_memory_context=False))
        if response.action:
            return response.action
    except Exception as e:
        logger.warning(f"Direct Groq analysis failed: {e}")
        
    return _local_fallback_action()


def summarize_text(text, *, client=None, logger=logger):
    """Summarize text using Groq when explicitly available."""
    global GROQ_API_KEY
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

    active_client = client if client is not None else get_groq_client()  # Lazy load
    if active_client is None and not GROQ_API_KEY:
        logger.warning("Summarization skipped because GROQ_API_KEY is missing.")
        return None

    provider = GroqProvider(
        api_key=GROQ_API_KEY or ("injected-client" if active_client is not None else ""),
        enabled=groq_enabled() or active_client is not None,
        model=get_groq_model(),
        client=active_client,
    )
    try:
        response = provider.summarize(text)
        if response.ok:
            return response.text
        logger.warning("Groq summarization failed: %s", response.error)
        record_runtime_event("summarization_error", "Groq summarization failed", "warning", {"error": response.error})
    except Exception as e:
        logger.warning(f"Summarization exception: {e}")
    return None


__all__ = [
    "DEFAULT_GROQ_MODEL",
    "GROQ_COOLDOWN_SECONDS",
    "GroqError",
    "SYSTEM_PROMPT",
    "activate_groq_cooldown",
    "analyze_with_groq",
    "analyze_with_groq_direct",
    "client",
    "extract_action_json",
    "get_groq_model",
    "groq_enabled",
    "is_groq_cooling_down",
    "summarize_text",
    "get_hybrid_ai_status",
    "save_hybrid_ai_status",
    "is_internet_available",
    "get_cached_latency",
]

