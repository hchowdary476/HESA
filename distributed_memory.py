"""Distributed Federated Memory for the JARVIS platform."""

from __future__ import annotations
import logging
from typing import Any
from cloud_sync import CloudSyncManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("distributed.memory")


class DistributedMemory:
    """Manages memory scopes across nodes, using cloud sync for federation."""

    _instance: DistributedMemory | None = None

    def __new__(cls, *args, **kwargs) -> DistributedMemory:
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.sync_manager = CloudSyncManager()
        
        # Memory Layers definition
        self.layers = {
            "session": {},       # RAM - temporary session metrics
            "working": {},       # RAM - immediate context caches
            "long_term": {},     # DB - personal knowledge notes
            "project": {},       # DB - workspace source configurations
            "cloud": {},         # Federated remote state
            "graph": {},         # Entity-relationship bindings
            "vector": {}         # TF-IDF search corpus
        }

    def write_memory(self, layer: str, key: str, value: Any) -> bool:
        """Saves a memory object to a specified layer and flags cloud sync if federated."""
        if layer not in self.layers:
            logger.error(f"Failed writing memory: Layer '{layer}' not found.")
            return False

        self.layers[layer][key] = value
        logger.info(f"Memory update on layer '{layer}': '{key}' = {value}")

        # Synchronize federated layers (long-term, project, preferences, graphs) to Cloud Sync
        if layer in ["long_term", "project", "graph"]:
            sync_key = f"mem:{layer}:{key}"
            self.sync_manager.push_local_change(sync_key, value)
            
        return True

    def read_memory(self, layer: str, key: str) -> Any:
        """Retrieves a memory object from a layer, falling back to synced local store."""
        if layer not in self.layers:
            return None

        # Return local memory cache if present
        if key in self.layers[layer]:
            return self.layers[layer][key]

        # Check cloud sync store fallback for federated layers
        if layer in ["long_term", "project", "graph"]:
            sync_key = f"mem:{layer}:{key}"
            synced_val = self.sync_manager.get_value(sync_key)
            if synced_val is not None:
                # Update local layer memory cache
                self.layers[layer][key] = synced_val
                return synced_val

        return None

    def sync_all_layers(self) -> dict[str, Any]:
        """Pushes local memory updates and pulls newer cloud memory states."""
        sync_result = self.sync_manager.sync_online()
        
        # Pull updated federated memory states down to local layers
        local_cache = self.sync_manager.get_local_store()
        for sync_key, val in local_cache.items():
            if sync_key.startswith("mem:"):
                # Extract layer and key from sync key: "mem:{layer}:{key}"
                parts = sync_key.split(":", 2)
                if len(parts) == 3:
                    layer = parts[1]
                    key = parts[2]
                    if layer in self.layers:
                        self.layers[layer][key] = val

        return sync_result

    def get_memory_status(self) -> dict[str, int]:
        """Returns statistics for memory density in each scope."""
        return {layer: len(entries) for layer, entries in self.layers.items()}

    def clear(self) -> None:
        """Resets federated memory scopes."""
        for layer in self.layers:
            self.layers[layer].clear()
        self.sync_manager.clear()
