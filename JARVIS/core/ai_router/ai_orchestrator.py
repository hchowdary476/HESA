"""AI Orchestrator for multi-LLM routing, failover, caching, encryption, and debate modes.

Expected architecture:
  Primary AI   : Claude (claude-3-5-sonnet-20241022)
  Secondary AI : OpenAI (gpt-4o-mini)
  Third AI     : Gemini (gemini-2.5-flash)
  Offline AI   : Ollama (phi3:latest)
"""

from __future__ import annotations

import base64
import concurrent.futures
import hashlib
import os
import time
from typing import Any

import requests
from cryptography.fernet import Fernet

from JARVIS.core.system.utils.jarvis_logging import get_file_logger

logger = get_file_logger("ai_orchestrator")


def _query_offline_rules(prompt: str) -> str:
    """Fallback handler for offline mode when no AI providers are available."""
    lowered = prompt.lower()
    if "python" in lowered:
        return "Python is a high-level, general-purpose programming language known for its clean syntax and readability, sir."
    if "hello" in lowered or "hi" in lowered or "hey" in lowered:
        return "Hello, sir. Local systems are online. How may I assist you?"
    if "who are you" in lowered:
        return "I am HESA, your personal cybernetic assistant, running in local offline fallback mode."
    if "what is ai" in lowered or "artificial intelligence" in lowered:
        return "Artificial Intelligence, sir, refers to the simulation of human intelligence by computer systems."
    return "I am currently running in offline fallback mode, sir. Cloud services are unavailable, but local subsystems remain at your disposal."


class AIOrchestrator:
    """Manages secure key storage, multi-model wrappers, smart routing, cache, failover, and debate."""

    _instance: AIOrchestrator | None = None

    def __new__(cls, *args, **kwargs) -> AIOrchestrator:
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        # Load environment variables
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except Exception:
            pass

        self.cache: dict[str, dict[str, Any]] = {}  # sha256 -> {response, expires}
        self.cache_ttl = 300  # Cache for 5 minutes

        # API status states for dashboard tracking
        self.active_ai = "Offline"
        self.active_model = "none"
        self.latency_ms = 0.0
        self.token_usage = 0
        self.api_status = "Offline"
        self.estimated_cost = 0.0

        # Fernet encryption setup
        self._init_encryption()

        # ── Startup Provider Diagnostics ──────────────────────────────────────
        self._run_startup_diagnostics()

    def _init_encryption(self) -> None:
        """Derive a cryptographic key from machine attributes or env variables."""
        env_key = os.environ.get("JARVIS_SECURE_SALT")
        if env_key:
            key_hash = hashlib.sha256(env_key.encode()).digest()
            self.cipher = Fernet(base64.urlsafe_b64encode(key_hash))
        else:
            fallback = "JarvisSecuredMachineLockSalt"
            key_hash = hashlib.sha256(fallback.encode()).digest()
            self.cipher = Fernet(base64.urlsafe_b64encode(key_hash))

    def encrypt_key(self, raw_key: str) -> str:
        """Encrypt an API key using AES-128 Fernet."""
        return self.cipher.encrypt(raw_key.encode()).decode()

    def decrypt_key(self, encrypted_key: str) -> str:
        """Decrypt an API key using AES-128 Fernet."""
        return self.cipher.decrypt(encrypted_key.encode()).decode()

    def _get_api_key(self, name: str) -> str:
        """Fetch raw API key from env or check if encrypted key is stored."""
        raw = os.environ.get(name)
        if raw:
            return raw
        enc = os.environ.get(f"{name}_ENC")
        if enc:
            try:
                return self.decrypt_key(enc)
            except Exception as e:
                logger.error("Failed to decrypt API key %s_ENC: %s", name, e)
        return ""

    def _run_startup_diagnostics(self) -> None:
        """Probe configured providers on startup to establish initial status."""
        # 1. Ollama (local) probe
        _ollama_url = os.getenv("JARVIS_LOCAL_LLM_URL", "http://127.0.0.1:11434").rstrip("/")
        _ollama_model = os.getenv("JARVIS_LOCAL_LLM_MODEL", "phi3:latest")
        print("[AI] PROBING OLLAMA SERVER ...", flush=True)
        logger.info("[AI] PROBING OLLAMA at %s model=%s", _ollama_url, _ollama_model)
        try:
            # Use /api/tags (fast 10ms GET) to verify server + model existence
            _res = requests.get(f"{_ollama_url}/api/tags", timeout=(3.05, 5.0))
            if _res.status_code == 200:
                models = [m.get("name", "") for m in _res.json().get("models", [])]
                print("[AI] OLLAMA DETECTED", flush=True)
                print(f"[AI] OLLAMA MODEL = {_ollama_model}", flush=True)
                print("[AI] OLLAMA READY", flush=True)
                logger.info("[AI] OLLAMA DETECTED models=%s", models)
                logger.info("[AI] OLLAMA MODEL = %s", _ollama_model)
            else:
                logger.warning("[AI] Ollama responded HTTP %d: %s", _res.status_code, _res.text[:100])
                print(f"[AI] OLLAMA UNAVAILABLE (HTTP {_res.status_code})", flush=True)
        except Exception as _e:
            logger.warning("[AI] Ollama unreachable at %s: %s", _ollama_url, _e)
            print(f"[AI] OLLAMA UNREACHABLE ({_e})", flush=True)

        # 2. Claude (Primary AI)
        claude_key = self._get_api_key("ANTHROPIC_API_KEY")
        if claude_key:
            print("[AI] CLAUDE API KEY DETECTED", flush=True)
            logger.info("[AI] CLAUDE API KEY DETECTED")

        # 3. OpenAI (Secondary AI)
        openai_key = self._get_api_key("OPENAI_API_KEY")
        if openai_key:
            print("[AI] OPENAI API KEY DETECTED", flush=True)
            logger.info("[AI] OPENAI API KEY DETECTED")

        # 4. Gemini (Third AI)
        gemini_key = self._get_api_key("GEMINI_API_KEY")
        if gemini_key:
            print("[AI] GEMINI API KEY DETECTED", flush=True)
            logger.info("[AI] GEMINI API KEY DETECTED")

    def query_provider(self, provider: str, prompt: str, timeout: float | tuple[float, float] = 15.0) -> str:
        """Invoke a specific provider's API endpoint synchronously with structured logging."""
        p_name = provider.lower().strip()
        start = time.perf_counter()

        try:
            if p_name == "claude":
                key = self._get_api_key("ANTHROPIC_API_KEY")
                if not key:
                    raise ValueError("Anthropic Claude API key missing.")

                model = "claude-3-5-sonnet-20241022"
                url = "https://api.anthropic.com/v1/messages"
                headers = {
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": model,
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": prompt}],
                }

                logger.info(
                    "[AI] CLAUDE REQUEST url=%s model=%s max_tokens=1024 timeout=%s",
                    url,
                    model,
                    timeout,
                )
                print(f"[AI] SENDING CLAUDE REQUEST (model={model}) ...", flush=True)

                res = requests.post(url, headers=headers, json=payload, timeout=timeout)
                res.raise_for_status()

                data = res.json()
                content = str(data["content"][0]["text"])
                latency = (time.perf_counter() - start) * 1000
                logger.info("[AI] CLAUDE RESPONSE status=200 latency=%.0fms", latency)
                print(f"[AI] CLAUDE SUCCESS (latency={latency:.0f}ms)", flush=True)
                return content

            elif p_name == "chatgpt":
                key = self._get_api_key("OPENAI_API_KEY")
                if not key:
                    raise ValueError("OpenAI API key missing.")

                model = "gpt-4o-mini"
                url = "https://api.openai.com/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                }

                logger.info("[AI] OPENAI REQUEST url=%s model=%s timeout=%s", url, model, timeout)
                print(f"[AI] SENDING OPENAI REQUEST (model={model}) ...", flush=True)

                res = requests.post(url, headers=headers, json=payload, timeout=timeout)
                res.raise_for_status()

                data = res.json()
                self.token_usage += data.get("usage", {}).get("total_tokens", 0)
                self.estimated_cost += 0.0001
                content = str(data["choices"][0]["message"]["content"])
                latency = (time.perf_counter() - start) * 1000
                logger.info("[AI] OPENAI RESPONSE status=200 latency=%.0fms", latency)
                print(f"[AI] OPENAI SUCCESS (latency={latency:.0f}ms)", flush=True)
                return content

            elif p_name == "gemini":
                key = self._get_api_key("GEMINI_API_KEY")
                if not key:
                    raise ValueError("Gemini API key missing.")

                model = "gemini-2.5-flash"
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                headers = {"Content-Type": "application/json"}
                payload = {"contents": [{"parts": [{"text": prompt}]}]}

                logger.info("[AI] GEMINI REQUEST model=%s timeout=%s", model, timeout)
                print(f"[AI] SENDING GEMINI REQUEST (model={model}) ...", flush=True)

                res = requests.post(url, headers=headers, json=payload, timeout=timeout)
                res.raise_for_status()

                data = res.json()
                content = str(data["candidates"][0]["content"]["parts"][0]["text"])
                latency = (time.perf_counter() - start) * 1000
                logger.info("[AI] GEMINI RESPONSE status=200 latency=%.0fms", latency)
                print(f"[AI] GEMINI SUCCESS (latency={latency:.0f}ms)", flush=True)
                return content

            elif p_name == "ollama":
                base_url = os.getenv("JARVIS_LOCAL_LLM_URL", "http://127.0.0.1:11434").rstrip("/")
                model = os.getenv("JARVIS_LOCAL_LLM_MODEL", "phi3:latest")
                url = f"{base_url}/api/chat"

                # Use custom connect/read timeout for local inference if default float passed
                ollama_timeout = (3.05, 60.0) if isinstance(timeout, (int, float)) else timeout

                headers = {"Content-Type": "application/json"}
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                }

                logger.info(
                    "[AI] OLLAMA REQUEST url=%s model=%s timeout=%s",
                    url,
                    model,
                    ollama_timeout,
                )
                print(
                    f"[AI] SENDING OLLAMA REQUEST url={url} model={model} timeout={ollama_timeout} ...",
                    flush=True,
                )

                res = requests.post(url, headers=headers, json=payload, timeout=ollama_timeout)
                res.raise_for_status()

                content = str(res.json()["message"]["content"])
                latency = (time.perf_counter() - start) * 1000
                logger.info(
                    '[AI] OLLAMA RESPONSE status=200 latency=%.0fms result="%s"',
                    latency,
                    content[:80].replace("\n", " "),
                )
                print(f"[AI] OLLAMA SUCCESS (latency={latency:.0f}ms)", flush=True)
                return content

            elif p_name == "grok":
                key = self._get_api_key("GROK_API_KEY")
                if not key:
                    raise ValueError("xAI Grok API key missing.")
                res = requests.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={"model": "grok-beta", "messages": [{"role": "user", "content": prompt}]},
                    timeout=timeout,
                )
                res.raise_for_status()
                return str(res.json()["choices"][0]["message"]["content"])

            elif p_name == "deepseek":
                key = self._get_api_key("DEEPSEEK_API_KEY")
                if not key:
                    raise ValueError("DeepSeek API key missing.")
                res = requests.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}]},
                    timeout=timeout,
                )
                res.raise_for_status()
                return str(res.json()["choices"][0]["message"]["content"])

            else:
                raise ValueError(f"Unknown provider: {provider}")

        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            res_obj = getattr(e, "response", None)
            _status = getattr(res_obj, "status_code", None)
            res_text = getattr(res_obj, "text", "") or str(e)

            if _status == 401:
                logger.error("[AI] KEY_INVALID for %s (HTTP 401, latency=%.0fms): %s", provider, latency, res_text[:120])
                print(f"[AI] KEY_INVALID — {provider} (HTTP 401)", flush=True)
            elif _status == 429:
                logger.error("[AI] QUOTA_EXHAUSTED for %s (HTTP 429, latency=%.0fms): %s", provider, latency, res_text[:120])
                print(f"[AI] QUOTA_EXHAUSTED — {provider} (HTTP 429)", flush=True)
            elif _status == 400 and ("credit balance" in res_text.lower() or "quota" in res_text.lower()):
                logger.error("[AI] CREDIT_EXHAUSTED for %s (HTTP 400, latency=%.0fms): %s", provider, latency, res_text[:120])
                print(f"[AI] CREDIT_EXHAUSTED — {provider} (HTTP 400: low balance)", flush=True)
            elif _status in (400, 422):
                logger.error("[AI] MALFORMED_PAYLOAD for %s (HTTP %s, latency=%.0fms): %s", provider, _status, latency, res_text[:120])
                print(f"[AI] MALFORMED_PAYLOAD — {provider} (HTTP {_status})", flush=True)
            elif _status:
                logger.error("[AI] HTTP_ERROR_%s for %s (latency=%.0fms): %s", _status, provider, latency, res_text[:120])
                print(f"[AI] HTTP_ERROR_{_status} — {provider}", flush=True)
            else:
                logger.warning("[AI] %s query failed (latency=%.0fms): %s", provider, latency, e)
                print(f"[AI] QUERY_FAILED — {provider} ({e})", flush=True)
            raise e
        finally:
            self.latency_ms = (time.perf_counter() - start) * 1000

    def query_with_failover(self, prompt: str, task_type: str = "general") -> str:
        """Route prompt with task-type priority routing and seamless failover.

        Routing Rules (Requirement #4):
          - Coding tasks    : Claude (claude-3-5-sonnet-20241022)
          - Reasoning tasks : OpenAI (gpt-4o-mini)
          - General knowledge: Gemini (gemini-2.5-flash)
          - Offline fallback: Ollama (phi3:latest)
        """
        router_logger = get_file_logger("jarvis.router")
        t0 = time.perf_counter()

        # 1. Try Cache
        cache_key = hashlib.sha256(prompt.encode()).hexdigest()
        cached = self.cache.get(cache_key)
        if cached and cached["expires"] > time.time():
            logger.info("Serving query response from cache.")
            return str(cached["response"])

        # Select failover order based on task classification
        task_norm = (task_type or "general").lower().strip()
        if task_norm == "coding":
            failover_order = ["claude", "chatgpt", "gemini", "ollama"]
        elif task_norm == "reasoning":
            failover_order = ["chatgpt", "claude", "gemini", "ollama"]
        elif task_norm == "general":
            failover_order = ["gemini", "claude", "chatgpt", "ollama"]
        elif task_norm == "offline":
            failover_order = ["ollama"]
        else:
            failover_order = ["claude", "chatgpt", "gemini", "ollama"]

        routing_decision_ms = (time.perf_counter() - t0) * 1000
        msg = f"[ROUTER] TASK_TYPE={task_norm.upper()} DECISION_LATENCY={routing_decision_ms:.2f}ms ORDER={failover_order}"
        print(msg, flush=True)
        router_logger.info(msg)

        for provider in failover_order:
            try:
                if provider != "ollama" and provider != "lmstudio" and os.environ.get("JARVIS_OFFLINE") == "1":
                    logger.info("Enforced Offline Mode, skipping %s", provider)
                    continue

                logger.info("[AI] ROUTING QUERY TO PROVIDER: %s", provider)
                response = self.query_provider(provider, prompt)

                # Log active provider selection
                if provider == "claude":
                    print("[AI] ACTIVE PROVIDER = CLAUDE", flush=True)
                    logger.info("[AI] ACTIVE PROVIDER = CLAUDE")
                elif provider == "chatgpt":
                    print("[AI] ACTIVE PROVIDER = OPENAI", flush=True)
                    logger.info("[AI] ACTIVE PROVIDER = OPENAI")
                elif provider == "gemini":
                    print("[AI] ACTIVE PROVIDER = GEMINI", flush=True)
                    logger.info("[AI] ACTIVE PROVIDER = GEMINI")
                elif provider == "ollama":
                    _m = os.getenv("JARVIS_LOCAL_LLM_MODEL", "phi3:latest")
                    print(f"[AI] ACTIVE PROVIDER = OLLAMA (model={_m})", flush=True)
                    logger.info("[AI] ACTIVE PROVIDER = OLLAMA (model=%s)", _m)

                # Update status variables
                self.active_ai = (
                    "Claude"
                    if provider == "claude"
                    else "ChatGPT"
                    if provider == "chatgpt"
                    else "Gemini"
                    if provider == "gemini"
                    else "Ollama"
                    if provider == "ollama"
                    else provider.title()
                )
                self.active_model = (
                    "claude-3-5-sonnet-20241022"
                    if provider == "claude"
                    else "gpt-4o-mini"
                    if provider == "chatgpt"
                    else "gemini-2.5-flash"
                    if provider == "gemini"
                    else "phi3:latest"
                    if provider == "ollama"
                    else "unknown"
                )
                self.api_status = "Online"

                # Save Cache
                self.cache[cache_key] = {
                    "response": response,
                    "expires": time.time() + self.cache_ttl,
                }
                return response
            except Exception:
                logger.warning("[AI] Provider %s failed, cascading to next in failover chain...", provider)
                continue

        # Ultimate fallback (if Ollama is down, return offline rules response)
        logger.error("All AI services failed or timed out.")
        self.api_status = "Offline"
        self.active_ai = "Offline Fallback"
        return _query_offline_rules(prompt)

    def run_debate_mode(self, prompt: str) -> dict[str, str]:
        """Dispatch query in parallel to ChatGPT, Gemini, and Claude, scoring and merging them."""
        responses: dict[str, str] = {}
        providers = ["claude", "chatgpt", "gemini"]

        def _fetch(p: str) -> tuple[str, str]:
            try:
                return p, self.query_provider(p, prompt)
            except Exception as e:
                return p, f"Error: {e}"

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(_fetch, p) for p in providers]
            for future in concurrent.futures.as_completed(futures):
                p, resp = future.result()
                responses[p] = resp

        return responses
