"""Central Event Bus for the JARVIS AI Operating System."""

from __future__ import annotations
import threading
import time
import logging
from typing import Callable, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_os.event_bus")


class EventBus:
    """Manages system events, supporting thread-safe subscribe/publish operations."""

    _instance: EventBus | None = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs) -> EventBus:
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.subscribers: dict[str, list[Callable[[dict[str, Any]], None]]] = {}
        self.history: list[dict[str, Any]] = []
        self.history_lock = threading.Lock()
        self.subs_lock = threading.Lock()
        self.client_bridge = None
        self.server_bridge = None
        logger.info("Enterprise Event Bus initialized.")

    def start_tcp_bridge(self, host: str = "127.0.0.1", port: int = 19110, as_server: bool = True) -> None:
        """Dynamic TCP bridging to support legacy cross-process EventBus communications."""
        try:
            if as_server:
                from JARVIS.core.system.event_bus import EventBusServer
                self.server_bridge = EventBusServer(host=host, port=port)
                self.server_bridge.start()
                logger.info(f"Event Bus TCP server bridge running on {host}:{port}")
            else:
                from JARVIS.core.system.event_bus import EventBusClient
                self.client_bridge = EventBusClient(host=host, port=port)
                if self.client_bridge.connect():
                    logger.info(f"Event Bus TCP client bridge connected to {host}:{port}")
                else:
                    logger.warning("Event Bus TCP client bridge failed to connect, using local-only mode.")
        except Exception as e:
            logger.error(f"Failed to initialize event bus TCP bridge: {e}")

    def subscribe(self, event_type: str, callback: Callable[[dict[str, Any]], None]) -> None:
        """Register a callback for a specific event type."""
        with self.subs_lock:
            if event_type not in self.subscribers:
                self.subscribers[event_type] = []
            if callback not in self.subscribers[event_type]:
                self.subscribers[event_type].append(callback)
            
            # Bridge to TCP client if active
            if self.client_bridge:
                try:
                    self.client_bridge.subscribe(event_type, lambda payload: self.publish(event_type, payload, bridge=False))
                except Exception as e:
                    logger.error(f"Failed to register subscription bridge: {e}")
                    
        logger.debug(f"Subscribed callback to event type: {event_type}")

    def unsubscribe(self, event_type: str, callback: Callable[[dict[str, Any]], None]) -> None:
        """Remove a callback registration."""
        with self.subs_lock:
            if event_type in self.subscribers and callback in self.subscribers[event_type]:
                self.subscribers[event_type].remove(callback)
                logger.debug(f"Unsubscribed callback from event type: {event_type}")

    def publish(self, event_type: str, payload: dict[str, Any], bridge: bool = True) -> None:
        """Broadcasts an event with the given payload to all subscribers."""
        event = {
            "event_type": event_type,
            "payload": payload,
            "timestamp": time.time()
        }
        
        # Log in history
        with self.history_lock:
            self.history.append(event)
            if len(self.history) > 1000:
                self.history.pop(0)

        # Notify local subscribers
        callbacks = []
        with self.subs_lock:
            if event_type in self.subscribers:
                callbacks = list(self.subscribers[event_type])
            # Handle wildcards if needed, or default broad category listeners
            if "*" in self.subscribers:
                callbacks.extend(self.subscribers["*"])

        for cb in callbacks:
            try:
                # Run callback asynchronously in a daemon thread to keep scheduler non-blocking
                threading.Thread(target=self._safe_execute, args=(cb, payload), daemon=True).start()
            except Exception as e:
                logger.error(f"Error starting callback thread: {e}")

        # Bridge publishing
        if bridge:
            if self.client_bridge:
                try:
                    self.client_bridge.publish(event_type, payload)
                except Exception as e:
                    logger.debug(f"Failed bridging publish to client: {e}")
            if self.server_bridge and hasattr(self.server_bridge, "broadcast"):
                try:
                    self.server_bridge.broadcast(event_type, payload, None)
                except Exception as e:
                    logger.debug(f"Failed bridging broadcast to server clients: {e}")

        logger.debug(f"Published event: {event_type} (payload: {payload})")

    def _safe_execute(self, callback: Callable[[dict[str, Any]], None], payload: dict[str, Any]) -> None:
        try:
            callback(payload)
        except Exception as e:
            logger.error(f"Error in EventBus callback invocation: {e}")

    def get_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Retrieve recent event history."""
        with self.history_lock:
            return list(self.history[-limit:])

    def clear(self) -> None:
        """Reset state for clean testing."""
        with self.subs_lock:
            self.subscribers.clear()
        with self.history_lock:
            self.history.clear()
        self.client_bridge = None
        self.server_bridge = None
