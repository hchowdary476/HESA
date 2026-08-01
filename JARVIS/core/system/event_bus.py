"""Lightweight newline-delimited JSON TCP Event Bus for cross-process IPC."""

import json
import socket
import threading
import time

from JARVIS.core.system.utils.jarvis_logging import get_logger

logger = get_logger("event_bus")


class EventBusServer:
    """Central Event Bus Server running on a background thread within supervisor."""

    def __init__(self, host: str = "127.0.0.1", port: int = 19110) -> None:
        self.host = host
        self.port = port
        self.clients: dict[socket.socket, list[str]] = {}  # socket -> registered event types
        self.lock = threading.Lock()
        self.running = False
        self.server_socket: socket.socket | None = None

    def start(self) -> None:
        self.running = True
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(25)
            logger.info("Event Bus Server started on %s:%d", self.host, self.port)
            threading.Thread(target=self._accept_loop, daemon=True).start()
        except Exception as e:
            logger.error("Failed to start Event Bus Server: %s", e)

    def _accept_loop(self) -> None:
        while self.running and self.server_socket:
            try:
                conn, addr = self.server_socket.accept()
                with self.lock:
                    self.clients[conn] = []
                threading.Thread(target=self._client_handler, args=(conn,), daemon=True).start()
            except Exception:
                break

    def _client_handler(self, conn: socket.socket) -> None:
        buffer = ""
        while self.running:
            try:
                data = conn.recv(8192).decode("utf-8")
                if not data:
                    break
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                    except Exception:
                        continue
                    action = msg.get("action")
                    event_type = msg.get("event_type")
                    if action == "subscribe" and event_type:
                        with self.lock:
                            if event_type not in self.clients[conn]:
                                self.clients[conn].append(event_type)
                                logger.info("Client subscribed to event: %s", event_type)
                    elif action == "publish" and event_type:
                        payload = msg.get("payload")
                        self.broadcast(event_type, payload, conn)
            except Exception:
                break
        with self.lock:
            if conn in self.clients:
                del self.clients[conn]
        try:
            conn.close()
        except Exception:
            pass

    def broadcast(self, event_type: str, payload: dict, sender_conn: socket.socket) -> None:
        broadcast_msg = json.dumps({"event_type": event_type, "payload": payload}) + "\n"
        encoded = broadcast_msg.encode("utf-8")
        with self.lock:
            for conn, subs in list(self.clients.items()):
                if event_type in subs:
                    try:
                        conn.sendall(encoded)
                    except Exception:
                        pass

    def stop(self) -> None:
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
            self.server_socket = None


class EventBusClient:
    """Client wrapper used by services and QML Bridge to publish/subscribe."""

    def __init__(self, host: str = "127.0.0.1", port: int = 19110) -> None:
        self.host = host
        self.port = port
        self.conn: socket.socket | None = None
        self.subscriptions: dict[str, list[callable]] = {}  # event_type -> callbacks
        self.lock = threading.Lock()
        self.running = False

    def connect(self, retries: int = 5) -> bool:
        for i in range(retries):
            try:
                self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.conn.connect((self.host, self.port))
                self.running = True
                threading.Thread(target=self._receive_loop, daemon=True).start()
                # Re-register existing subscriptions
                with self.lock:
                    for event_type in self.subscriptions:
                        sub_msg = json.dumps({"action": "subscribe", "event_type": event_type}) + "\n"
                        self.conn.sendall(sub_msg.encode("utf-8"))
                logger.info("Connected to Event Bus on port %d", self.port)
                return True
            except Exception:
                time.sleep(0.5)
        return False

    def subscribe(self, event_type: str, callback: callable) -> None:
        with self.lock:
            if event_type not in self.subscriptions:
                self.subscriptions[event_type] = []
                if self.conn and self.running:
                    try:
                        sub_msg = json.dumps({"action": "subscribe", "event_type": event_type}) + "\n"
                        self.conn.sendall(sub_msg.encode("utf-8"))
                    except Exception:
                        pass
            self.subscriptions[event_type].append(callback)

    def publish(self, event_type: str, payload: dict) -> bool:
        if not self.conn or not self.running:
            return False
        try:
            pub_msg = json.dumps({"action": "publish", "event_type": event_type, "payload": payload}) + "\n"
            self.conn.sendall(pub_msg.encode("utf-8"))
            return True
        except Exception:
            return False

    def _receive_loop(self) -> None:
        buffer = ""
        while self.running and self.conn:
            try:
                data = self.conn.recv(8192).decode("utf-8")
                if not data:
                    break
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                    except Exception:
                        continue
                    event_type = msg.get("event_type")
                    payload = msg.get("payload")
                    callbacks = []
                    with self.lock:
                        if event_type in self.subscriptions:
                            callbacks = self.subscriptions[event_type].copy()
                    for cb in callbacks:
                        try:
                            cb(payload)
                        except Exception as e:
                            logger.error("Error in event callback: %s", e)
            except Exception:
                break
        self.running = False
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None
