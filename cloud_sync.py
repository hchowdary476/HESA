"""Offline-first Cloud Synchronization broker for the JARVIS platform."""

from __future__ import annotations
import time
import logging
from typing import Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("distributed.cloud_sync")


class CloudSyncManager:
    """Manages offline-first data synchronization and version conflict resolution."""

    _instance: CloudSyncManager | None = None

    def __new__(cls, *args, **kwargs) -> CloudSyncManager:
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.online = False
        
        # Local configuration cache database
        self.local_store: dict[str, dict[str, Any]] = {}  # key -> {"value": val, "version": ver, "timestamp": ts}
        
        # Simulated Cloud state database
        self.cloud_store: dict[str, dict[str, Any]] = {}
        
        # Queue of transactions generated while offline
        self.offline_queue: list[dict[str, Any]] = []  # list of {"action": "set", "key": key, "value": val, "version": ver}

    def set_online_status(self, is_online: bool) -> None:
        """Sets simulated network connectivity status."""
        self.online = is_online
        logger.info(f"CloudSync network status updated: {'ONLINE' if is_online else 'OFFLINE'}")
        if is_online:
            self.sync_online()

    def is_online(self) -> bool:
        """Check if sync agent is online."""
        return self.online

    def get_value(self, key: str) -> Any:
        """Retrieve local value from cache."""
        entry = self.local_store.get(key)
        return entry["value"] if entry else None

    def get_version(self, key: str) -> int:
        """Returns the version index for a key."""
        entry = self.local_store.get(key)
        return entry["version"] if entry else 0

    def push_local_change(self, key: str, value: Any) -> int:
        """Applies configuration updates locally and queues sync tasks."""
        current_ver = self.get_version(key)
        new_ver = current_ver + 1
        
        entry = {
            "value": value,
            "version": new_ver,
            "timestamp": time.time()
        }
        self.local_store[key] = entry

        # Queue change
        transaction = {
            "action": "set",
            "key": key,
            "value": value,
            "version": new_ver,
            "timestamp": entry["timestamp"]
        }
        
        if not self.online:
            self.offline_queue.append(transaction)
            logger.info(f"Offline: queued update for '{key}' (version: {new_ver})")
        else:
            # Sync immediately
            self._sync_transaction_to_cloud(transaction)

        return new_ver

    def sync_online(self) -> dict[str, Any]:
        """Uploads offline transactions and resolves cloud conflicts (LWW logic)."""
        if not self.online:
            logger.warning("Failed syncing: device is currently OFFLINE.")
            return {"status": "FAILED", "reason": "offline", "processed_jobs": 0}

        logger.info(f"Starting cloud synchronization. Processing {len(self.offline_queue)} offline actions...")
        
        processed_count = 0
        resolved_conflicts = 0

        # 1. Process offline transaction queue
        while self.offline_queue:
            tx = self.offline_queue.pop(0)
            conflict = self._sync_transaction_to_cloud(tx)
            if conflict:
                resolved_conflicts += 1
            processed_count += 1

        # 2. Pull remote cloud changes that are newer
        for key, cloud_entry in self.cloud_store.items():
            local_entry = self.local_store.get(key)
            if not local_entry or cloud_entry["version"] > local_entry["version"]:
                self.local_store[key] = {
                    "value": cloud_entry["value"],
                    "version": cloud_entry["version"],
                    "timestamp": cloud_entry["timestamp"]
                }
                logger.info(f"Synced newer cloud value down to local: '{key}' (version: {cloud_entry['version']})")

        sync_result = {
            "status": "SUCCESS",
            "processed_jobs": processed_count,
            "resolved_conflicts": resolved_conflicts,
            "local_keys": list(self.local_store.keys())
        }
        logger.info(f"Sync complete. Results: {sync_result}")
        return sync_result

    def _sync_transaction_to_cloud(self, tx: dict[str, Any]) -> bool:
        """Syncs single transaction to cloud using Last-Write-Wins (LWW) conflict checks."""
        key = tx["key"]
        val = tx["value"]
        local_ver = tx["version"]
        local_ts = tx["timestamp"]

        cloud_entry = self.cloud_store.get(key)
        
        conflict = False
        if cloud_entry:
            # Conflict detected: remote value exists
            cloud_ver = cloud_entry["version"]
            cloud_ts = cloud_entry["timestamp"]
            
            if local_ver > cloud_ver:
                # Local is newer by version index
                self.cloud_store[key] = {"value": val, "version": local_ver, "timestamp": local_ts}
                logger.info(f"Updated cloud with newer local data: '{key}' ({local_ver} > {cloud_ver})")
            elif local_ver == cloud_ver and local_ts > cloud_ts:
                # Same version but newer timestamp
                self.cloud_store[key] = {"value": val, "version": local_ver, "timestamp": local_ts}
                logger.info(f"Updated cloud with newer timestamp: '{key}'")
            else:
                # Cloud version is newer, local change rejected/conflicted
                conflict = True
                logger.warning(f"Sync Conflict: Cloud has newer data for '{key}' ({cloud_ver} >= {local_ver}). Keeping cloud.")
                # We do not overwrite cloud. In sync_online() we pull down the newer cloud version.
        else:
            # Fresh key in cloud
            self.cloud_store[key] = {"value": val, "version": local_ver, "timestamp": local_ts}
            logger.info(f"Created new cloud entry: '{key}' (version: {local_ver})")
            
        return conflict

    def get_local_store(self) -> dict[str, Any]:
        """Returns local configurations map."""
        return {k: v["value"] for k, v in self.local_store.items()}

    def clear(self) -> None:
        """Resets cached stores for clean test runs."""
        self.local_store.clear()
        self.cloud_store.clear()
        self.offline_queue.clear()
        self.online = False
