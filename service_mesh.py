"""Distributed AI Service Mesh for cost-routing, failovers, and analytics."""

from __future__ import annotations
import logging
import time
from typing import Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("distributed.service_mesh")


class ModelProvider:
    """Represents a single registered AI service endpoint and its live telemetry."""

    def __init__(self, name: str, cost_per_1k: float = 0.01, latency_ms: float = 500.0) -> None:
        self.name = name
        self.cost_per_1k = cost_per_1k
        self.last_latency = latency_ms
        self.online = True
        
        # Telemetry counts
        self.calls_count = 0
        self.failures_count = 0
        self.total_tokens_consumed = 0
        self.total_cost_accrued = 0.0

    def check_health(self) -> bool:
        """Pings provider availability."""
        # In a real environment, we'd query socket pings or API health routes
        # Defaults to online for simulated runs
        return self.online

    def get_score(self, strategy: str) -> float:
        """Higher scores imply preferred model routing decisions."""
        if not self.online:
            return -99999.0
            
        if strategy == "cost-priority":
            # Prefer cheaper options: return negative cost so max() yields lowest cost
            return -self.cost_per_1k
        elif strategy == "least-latency":
            # Prefer faster options: return negative latency
            return -self.last_latency
        
        # Default balanced scoring
        return -(self.cost_per_1k * 100 + self.last_latency / 100)


class AIServiceMesh:
    """Load balancer and orchestrator coordinating multiple LLM backends."""

    _instance: AIServiceMesh | None = None

    def __new__(cls, *args, **kwargs) -> AIServiceMesh:
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        
        # Providers directory
        self.providers: dict[str, ModelProvider] = {}
        self.round_robin_index = 0
        
        # Initialize default mesh catalog
        self._seed_default_mesh()

    def _seed_default_mesh(self) -> None:
        """Pre-seeds the mesh with standard enterprise providers."""
        self.register_provider("chatgpt", cost_per_1k=0.002, latency_ms=600.0)
        self.register_provider("gemini", cost_per_1k=0.0015, latency_ms=500.0)
        self.register_provider("claude", cost_per_1k=0.008, latency_ms=800.0)
        self.register_provider("grok", cost_per_1k=0.005, latency_ms=700.0)
        self.register_provider("deepseek", cost_per_1k=0.0002, latency_ms=900.0)
        self.register_provider("ollama", cost_per_1k=0.0, latency_ms=200.0)
        self.register_provider("lm_studio", cost_per_1k=0.0, latency_ms=300.0)

    def register_provider(self, name: str, cost_per_1k: float, latency_ms: float = 500.0) -> None:
        """Injects a new AI endpoint into the mesh routing list."""
        self.providers[name.lower()] = ModelProvider(name.lower(), cost_per_1k, latency_ms)
        logger.info(f"Mesh Provider registered: {name} (cost: ${cost_per_1k}/1k tokens)")

    def update_provider_status(self, name: str, online: bool) -> None:
        """Sets live online status for a model provider."""
        prov = self.providers.get(name.lower())
        if prov:
            prov.online = online
            logger.info(f"Mesh Provider '{name}' online status updated: {online}")

    def route_request(self, prompt: str, strategy: str = "least-latency") -> str:
        """Determines best active provider based on routing algorithm strategy."""
        active = [p for p in self.providers.values() if p.online]
        if not active:
            raise RuntimeError("All providers in AI Service Mesh are currently offline.")

        if strategy == "round-robin":
            selected = active[self.round_robin_index % len(active)]
            self.round_robin_index += 1
            return selected.name

        # Score based selection
        best_prov = max(active, key=lambda p: p.get_score(strategy))
        return best_prov.name

    def report_call_result(self, name: str, success: bool, latency: float, tokens: int) -> None:
        """Updates telemetry records for completed model calls."""
        prov = self.providers.get(name.lower())
        if not prov:
            return

        prov.calls_count += 1
        if not success:
            prov.failures_count += 1
            prov.online = False  # Mark offline temporarily if failed
            logger.warning(f"Mesh Provider '{name}' call failed. Telemetry marked unhealthy.")
        else:
            # Running average update for latency
            prov.last_latency = (prov.last_latency * 0.7) + (latency * 0.3)
            prov.total_tokens_consumed += tokens
            prov.total_cost_accrued += (tokens / 1000.0) * prov.cost_per_1k
            prov.online = True
            logger.info(f"Mesh call logged: {name} (latency: {latency:.1f}ms, tokens: {tokens})")

    def trigger_health_check(self) -> dict[str, Any]:
        """Runs diagnostics ping sweep on all endpoints."""
        logger.info("Executing AI Service Mesh Diagnostics check...")
        results = {}
        for name, prov in self.providers.items():
            is_ok = prov.check_health()
            results[name] = "ONLINE" if is_ok else "OFFLINE"
        return results

    def failover_execute(self, prompt: str, strategy: str = "least-latency") -> dict[str, Any]:
        """Attempts prompt run on best provider, falling back on fail list if outages hit."""
        # Get sorted list of providers based on strategy score
        active = [p for p in self.providers.values() if p.online]
        sorted_providers = sorted(active, key=lambda p: p.get_score(strategy), reverse=True)

        if not sorted_providers:
            # Fallback to local Ollama even if flagged offline
            sorted_providers = [self.providers["ollama"]]

        last_error = ""
        for prov in sorted_providers:
            logger.info(f"Failover loop: Attempting execution via provider '{prov.name}'...")
            t0 = time.time()
            
            try:
                # Simulate execution
                # If provider is configured to simulate failure (e.g. testing), raise error
                if not prov.online:
                    raise ConnectionError("Endpoint unreachable.")
                
                # Successful run simulation
                latency = prov.last_latency / 1000.0
                time.sleep(min(latency, 0.2))  # simulated delay capping at 200ms for test speed
                
                response = f"Response from {prov.name} mesh node."
                tokens = len(prompt.split()) + len(response.split())
                
                self.report_call_result(prov.name, success=True, latency=prov.last_latency, tokens=tokens)
                
                return {
                    "success": True,
                    "provider": prov.name,
                    "response": response,
                    "cost": (tokens / 1000.0) * prov.cost_per_1k,
                    "latency_sec": time.time() - t0
                }
            except Exception as e:
                last_error = str(e)
                self.report_call_result(prov.name, success=False, latency=9999.0, tokens=0)
                logger.warning(f"Provider '{prov.name}' execution failed: {e}. Trying next fallback...")

        return {
            "success": False,
            "error": f"All mesh nodes failed. Last error: {last_error}",
            "provider": None
        }

    def get_mesh_analytics(self) -> dict[str, Any]:
        """Collates accumulated cost/token metrics across the AI mesh."""
        analytics = {}
        total_cost = 0.0
        total_tokens = 0
        
        for name, prov in self.providers.items():
            analytics[name] = {
                "online": prov.online,
                "calls": prov.calls_count,
                "failures": prov.failures_count,
                "tokens": prov.total_tokens_consumed,
                "cost": prov.total_cost_accrued,
                "latency_ms": prov.last_latency
            }
            total_cost += prov.total_cost_accrued
            total_tokens += prov.total_tokens_consumed
            
        return {
            "providers": analytics,
            "total_cost": total_cost,
            "total_tokens": total_tokens
        }

    def clear(self) -> None:
        """Reset state."""
        for name in self.providers:
            self.providers[name].online = True
            self.providers[name].calls_count = 0
            self.providers[name].failures_count = 0
            self.providers[name].total_tokens_consumed = 0
            self.providers[name].total_cost_accrued = 0.0
        self.round_robin_index = 0
