"""Distributed Intelligence Remote API Gateway & Dashboard for JARVIS."""

from __future__ import annotations
import http.server
import socketserver
import socket
import threading
import time
import json
import urllib.parse
import logging
import secrets
from typing import Any

from ai_fabric import AIFabric
from cloud_sync import CloudSyncManager
from distributed_memory import DistributedMemory
from service_mesh import AIServiceMesh

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("distributed.remote_api")


class OAuthManager:
    """Manages secure Bearer token issuance and validation for OAuth compliance."""

    def __init__(self) -> None:
        self.tokens: dict[str, float] = {}  # token -> expiry_timestamp
        self.valid_client_id = "jarvis_client"
        self.valid_client_secret = "jarvis_secret"
        self.lock = threading.Lock()

    def issue_token(self, client_id: str, client_secret: str, expires_in: int = 3600) -> str | None:
        """Issues a new token if credentials are valid."""
        with self.lock:
            if client_id == self.valid_client_id and client_secret == self.valid_client_secret:
                token = secrets.token_hex(24)
                self.tokens[token] = time.time() + expires_in
                return token
            return None

    def validate_token(self, token: str) -> bool:
        """Validates a given bearer token against active cache and expiry."""
        with self.lock:
            if token in self.tokens:
                if time.time() < self.tokens[token]:
                    return True
                else:
                    del self.tokens[token]
            return False


class RateLimiter:
    """Tracks sliding window request limits per client IP."""

    def __init__(self, limit_per_minute: int = 60) -> None:
        self.limit = limit_per_minute
        self.requests: dict[str, list[float]] = {}  # ip -> timestamps
        self.lock = threading.Lock()

    def check_limit(self, ip: str) -> bool:
        """Checks if the client IP is within request bounds."""
        now = time.time()
        with self.lock:
            if ip not in self.requests:
                self.requests[ip] = []
            # Prune timestamps older than 60 seconds
            self.requests[ip] = [t for t in self.requests[ip] if now - t < 60.0]
            if len(self.requests[ip]) >= self.limit:
                return False
            self.requests[ip].append(now)
            return True


class ThreadedRemoteApiServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """Multi-threaded HTTP Server for non-blocking concurrent request routing."""
    daemon_threads = True


class RemoteApiHandler(http.server.BaseHTTPRequestHandler):
    """Routes distributed intelligence API endpoints and serves the Web Dashboard."""

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress server output logs to keep console clean
        logger.debug(format % args)

    def _send_json(self, status: int, data: dict[str, Any]) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _authenticate(self) -> bool:
        """Authenticates requests utilizing Bearer tokens or query param access."""
        auth_header = self.headers.get("Authorization")
        token = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
        else:
            # Query param fallback
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            token = params.get("token", [None])[0]

        if token and self.server.oauth_manager.validate_token(token):
            return True

        self._send_json(401, {"error": "Unauthorized", "message": "Valid OAuth access token required."})
        return False

    def _check_rate_limit(self) -> bool:
        """Ensures incoming requests from client IP remain under rate bounds."""
        client_ip = self.client_address[0]
        if not self.server.rate_limiter.check_limit(client_ip):
            self._send_json(429, {"error": "Too Many Requests", "message": "Rate limit exceeded (60 req/min)."})
            return False
        return True

    def do_OPTIONS(self) -> None:
        """CORS preflight configuration."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self) -> None:
        """Routes GET calls."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        # Serving dashboard resources and health routes (no authentication needed)
        if path in ["/", "/dashboard"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_DASHBOARD.encode("utf-8"))
            return

        if path == "/api/v1/health":
            self._send_json(200, {
                "status": "HEALTHY",
                "service": "JARVIS Distributed Intelligence Hub",
                "uptime": time.time() - self.server.start_time,
                "timestamp": time.time()
            })
            return

        # Authenticate and limit other API routes
        if not self._authenticate() or not self._check_rate_limit():
            return

        if path == "/api/v1/nodes":
            nodes = self.server.fabric.get_nodes()
            self._send_json(200, {"nodes": nodes})

        elif path == "/api/v1/sync":
            self._send_json(200, {
                "online": self.server.sync_manager.is_online(),
                "local_store": self.server.sync_manager.get_local_store(),
                "offline_queue_size": len(self.server.sync_manager.offline_queue),
                "offline_queue": self.server.sync_manager.offline_queue
            })

        elif path == "/api/v1/mesh":
            analytics = self.server.service_mesh.get_mesh_analytics()
            self._send_json(200, analytics)

        elif path == "/api/v1/memory":
            scopes = self.server.memory.get_memory_status()
            # Compile memory layer contents
            layer_contents = {}
            for layer_name, entries in self.server.memory.layers.items():
                layer_contents[layer_name] = entries
            self._send_json(200, {
                "status": scopes,
                "data": layer_contents
            })

        elif path == "/api/v1/stream":
            # Server-Sent Events stream for real-time web telemetry
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            client_id = f"web_{self.client_address[0]}_{self.client_address[1]}"
            q = self.server.gateway.register_sse_client(client_id)
            logger.info(f"SSE client subscription active: {client_id}")

            try:
                while self.server.gateway.running:
                    # Retrieve pending notifications
                    try:
                        event_data = q.pop(0)
                        self.wfile.write(f"data: {json.dumps(event_data)}\n\n".encode("utf-8"))
                        self.wfile.flush()
                    except IndexError:
                        # Send heartbeat ping to keep connection alive
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
                        time.sleep(1.0)
            except Exception as e:
                logger.debug(f"SSE client connection dropped: {client_id} ({e})")
            finally:
                self.server.gateway.unregister_sse_client(client_id)

        else:
            self._send_json(404, {"error": "Not Found", "message": f"Endpoint {path} not found."})

    def do_POST(self) -> None:
        """Routes POST calls."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body) if body else {}
        except Exception as e:
            self._send_json(400, {"error": "Bad Request", "message": f"Malformed JSON payload: {e}"})
            return

        # OAuth token generation bypasses standard authentication check
        if path == "/oauth/token":
            # Handle forms or json input
            client_id = data.get("client_id")
            client_secret = data.get("client_secret")
            if not client_id or not client_secret:
                # Attempt to read from form urlencoded instead
                params = urllib.parse.parse_qs(body)
                client_id = params.get("client_id", [None])[0]
                client_secret = params.get("client_secret", [None])[0]

            token = self.server.oauth_manager.issue_token(client_id, client_secret)
            if token:
                self._send_json(200, {
                    "access_token": token,
                    "token_type": "Bearer",
                    "expires_in": 3600
                })
            else:
                self._send_json(400, {"error": "invalid_grant", "message": "Invalid client credentials."})
            return

        # Authenticate and rate limit check
        if not self._authenticate() or not self._check_rate_limit():
            return

        if path == "/api/v1/nodes/register":
            node_id = data.get("node_id")
            device_type = data.get("device_type", "DESKTOP")
            status = data.get("status", "ONLINE")

            if not node_id:
                self._send_json(400, {"error": "Bad Request", "message": "Missing required field: node_id"})
                return

            self.server.fabric.register_node(node_id, device_type, status)
            self.server.gateway.broadcast_event("NODE_REGISTERED", {
                "node_id": node_id, "device_type": device_type, "status": status
            })
            self._send_json(200, {"status": "SUCCESS", "message": f"Node '{node_id}' registered successfully."})

        elif path == "/api/v1/sync/push":
            key = data.get("key")
            value = data.get("value")

            if not key:
                self._send_json(400, {"error": "Bad Request", "message": "Missing required field: key"})
                return

            version = self.server.sync_manager.push_local_change(key, value)
            self.server.gateway.broadcast_event("SYNC_PUSHED", {
                "key": key, "value": value, "version": version
            })
            self._send_json(200, {"status": "SUCCESS", "version": version})

        elif path == "/api/v1/sync/status":
            online = data.get("online", False)
            self.server.sync_manager.set_online_status(online)
            self.server.gateway.broadcast_event("SYNC_STATUS_CHANGED", {"online": online})
            self._send_json(200, {"status": "SUCCESS", "online": online})

        elif path == "/api/v1/route":
            prompt = data.get("prompt")
            strategy = data.get("strategy", "least-latency")

            if not prompt:
                self._send_json(400, {"error": "Bad Request", "message": "Missing required field: prompt"})
                return

            result = self.server.service_mesh.failover_execute(prompt, strategy)
            self.server.gateway.broadcast_event("REQUEST_ROUTED", {
                "prompt": prompt, "strategy": strategy, "result": result
            })
            self._send_json(200, result)

        elif path == "/api/v1/memory/write":
            layer = data.get("layer")
            key = data.get("key")
            value = data.get("value")

            if not layer or not key:
                self._send_json(400, {"error": "Bad Request", "message": "Missing layer or key."})
                return

            success = self.server.memory.write_memory(layer, key, value)
            if success:
                self.server.gateway.broadcast_event("MEMORY_WRITTEN", {
                    "layer": layer, "key": key, "value": value
                })
                self._send_json(200, {"status": "SUCCESS"})
            else:
                self._send_json(400, {"error": "Write Failed", "message": f"Could not write to layer '{layer}'."})

        else:
            self._send_json(404, {"error": "Not Found", "message": f"Endpoint {path} not found."})


class RemoteGateway:
    """Manages HTTP web routing, dashboard, and TCP socket stream interfaces."""

    _instance: RemoteGateway | None = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs) -> RemoteGateway:
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self, host: str = "127.0.0.1", port: int = 18010) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.host = host
        self.port = port
        
        # Instantiate platform singletons
        self.fabric = AIFabric()
        self.sync_manager = CloudSyncManager()
        self.memory = DistributedMemory()
        self.service_mesh = AIServiceMesh()
        
        self.oauth_manager = OAuthManager()
        self.rate_limiter = RateLimiter(limit_per_minute=60)
        
        # Server loops controls
        self.http_server: ThreadedRemoteApiServer | None = None
        self.http_thread: threading.Thread | None = None
        self.tcp_server: socket.socket | None = None
        self.tcp_thread: threading.Thread | None = None
        self.tcp_clients: list[socket.socket] = []
        self.tcp_lock = threading.Lock()
        
        self.sse_clients: dict[str, list[dict[str, Any]]] = {}
        self.sse_lock = threading.Lock()
        self.running = False

    def start(self) -> None:
        """Starts gateway components and schedules listener threads."""
        self.running = True
        
        # Instantiate and bind HTTP Server
        self.http_server = ThreadedRemoteApiServer((self.host, self.port), RemoteApiHandler)
        self.http_server.oauth_manager = self.oauth_manager
        self.http_server.rate_limiter = self.rate_limiter
        self.http_server.fabric = self.fabric
        self.http_server.sync_manager = self.sync_manager
        self.http_server.memory = self.memory
        self.http_server.service_mesh = self.service_mesh
        self.http_server.gateway = self
        self.http_server.start_time = time.time()

        # Update dynamic port details if ephemeral selected
        self.port = self.http_server.server_address[1]
        
        # Launch HTTP server daemon loop
        self.http_thread = threading.Thread(target=self.http_server.serve_forever, daemon=True)
        self.http_thread.start()
        logger.info(f"Remote API Gateway and Dashboard live on http://{self.host}:{self.port}")

        # Start TCP Socket event broadcast engine
        self.tcp_thread = threading.Thread(target=self._run_tcp_server, daemon=True)
        self.tcp_thread.start()

    def stop(self) -> None:
        """Shuts down connection loops and sweeps socket bindings."""
        self.running = False
        
        # Shut down HTTP engine
        if self.http_server:
            self.http_server.shutdown()
            self.http_server.server_close()
        
        # Shut down TCP socket listener
        if self.tcp_server:
            try:
                self.tcp_server.close()
            except Exception:
                pass

        # Disconnect TCP stream clients
        with self.tcp_lock:
            for conn in self.tcp_clients:
                try:
                    conn.close()
                except Exception:
                    pass
            self.tcp_clients.clear()

        # Clear SSE queues
        with self.sse_lock:
            self.sse_clients.clear()

        logger.info("Remote API Gateway stopped.")

    def register_sse_client(self, client_id: str) -> list[dict[str, Any]]:
        """Registers a SSE web subscriber queue."""
        with self.sse_lock:
            self.sse_clients[client_id] = []
            return self.sse_clients[client_id]

    def unregister_sse_client(self, client_id: str) -> None:
        """Cleans up a dropped SSE subscriber queue."""
        with self.sse_lock:
            if client_id in self.sse_clients:
                del self.sse_clients[client_id]

    def broadcast_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Broadcasts real-time events to active TCP sockets and SSE clients."""
        msg_payload = {
            "event_type": event_type,
            "payload": payload,
            "timestamp": time.time()
        }
        
        # 1. Dispatch to Web browser clients (SSE)
        with self.sse_lock:
            for client_queue in self.sse_clients.values():
                client_queue.append(msg_payload)

        # 2. Dispatch to CLI/Machine client connections (TCP socket stream)
        raw_msg = (json.dumps(msg_payload) + "\n").encode("utf-8")
        with self.tcp_lock:
            dead_clients = []
            for client in self.tcp_clients:
                try:
                    client.sendall(raw_msg)
                except Exception:
                    dead_clients.append(client)
            
            for client in dead_clients:
                self.tcp_clients.remove(client)
                try:
                    client.close()
                except Exception:
                    pass

    def _run_tcp_server(self) -> None:
        """Binds TCP socket to stream event logs to terminal nodes."""
        tcp_port = self.port + 1
        self.tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.tcp_server.bind((self.host, tcp_port))
            self.tcp_server.listen(10)
            logger.info(f"CLI / Socket Streaming mesh active on TCP port {tcp_port}")
        except Exception as e:
            logger.error(f"Failed starting TCP Streaming server on port {tcp_port}: {e}")
            return

        while self.running:
            try:
                conn, addr = self.tcp_server.accept()
                with self.tcp_lock:
                    self.tcp_clients.append(conn)
                logger.info(f"CLI/Node stream client linked: {addr}")
            except Exception:
                break


# Complete gorgeous dashboard single page HTML/CSS/JS code
HTML_DASHBOARD = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>JARVIS Enterprise Distributed AI Control Hub</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
        
        :root {
            --bg-dark: #09090b;
            --bg-card: #18181b;
            --border-color: rgba(255, 255, 255, 0.08);
            --text-primary: #f4f4f5;
            --text-secondary: #a1a1aa;
            --primary: #8b5cf6;
            --primary-hover: #7c3aed;
            --primary-glow: rgba(139, 92, 246, 0.15);
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --font-main: 'Outfit', sans-serif;
            --font-mono: 'JetBrains Mono', monospace;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg-dark);
            color: var(--text-primary);
            font-family: var(--font-main);
            overflow-x: hidden;
            line-height: 1.5;
        }

        /* Ambient background glow */
        .ambient-glow {
            position: absolute;
            top: -10%;
            left: 50%;
            transform: translateX(-50%);
            width: 80%;
            height: 400px;
            background: radial-gradient(circle, rgba(139, 92, 246, 0.12) 0%, rgba(0,0,0,0) 70%);
            pointer-events: none;
            z-index: -1;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1.5rem 3rem;
            border-bottom: 1px solid var(--border-color);
            background: rgba(24, 24, 27, 0.5);
            backdrop-filter: blur(12px);
            position: sticky;
            top: 0;
            z-index: 10;
        }

        header h1 {
            font-size: 1.5rem;
            font-weight: 700;
            background: linear-gradient(to right, #a78bfa, #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .header-status {
            display: flex;
            align-items: center;
            gap: 1.5rem;
        }

        .status-badge {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.875rem;
            background: rgba(16, 185, 129, 0.1);
            color: var(--success);
            padding: 0.25rem 0.75rem;
            border-radius: 100px;
            border: 1px solid rgba(16, 185, 129, 0.2);
            font-weight: 500;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: var(--success);
            box-shadow: 0 0 8px var(--success);
        }

        /* Container Layout */
        .main-container {
            display: grid;
            grid-template-columns: 250px 1fr;
            min-height: calc(100vh - 73px);
        }

        /* Sidebar styling */
        sidebar {
            border-right: 1px solid var(--border-color);
            padding: 2rem 1.5rem;
            background: rgba(15, 15, 17, 0.3);
        }

        .nav-list {
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .nav-item {
            display: flex;
            align-items: center;
            padding: 0.85rem 1.25rem;
            border-radius: 8px;
            cursor: pointer;
            color: var(--text-secondary);
            font-weight: 500;
            transition: all 0.2s ease;
        }

        .nav-item:hover, .nav-item.active {
            color: var(--text-primary);
            background: rgba(255, 255, 255, 0.04);
        }

        .nav-item.active {
            border-left: 3px solid var(--primary);
            background: rgba(139, 92, 246, 0.08);
        }

        /* Dashboard content layout */
        .content-area {
            padding: 3rem;
            max-width: 1400px;
            margin: 0 auto;
            width: 100%;
        }

        .panel {
            display: none;
            animation: fadeIn 0.3s ease;
        }

        .panel.active {
            display: block;
        }

        /* Grid cards layout */
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2.5rem;
        }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(139, 92, 246, 0.05);
            border-color: rgba(139, 92, 246, 0.2);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.25rem;
        }

        .card-title {
            font-size: 1.125rem;
            font-weight: 600;
            color: var(--text-primary);
        }

        .card-value {
            font-size: 2.25rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 0.5rem;
        }

        .card-desc {
            font-size: 0.875rem;
            color: var(--text-secondary);
        }

        /* Forms, inputs, tables */
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
            text-align: left;
        }

        th, td {
            padding: 1rem;
            border-bottom: 1px solid var(--border-color);
            font-size: 0.875rem;
        }

        th {
            color: var(--text-secondary);
            font-weight: 600;
        }

        td {
            color: var(--text-primary);
        }

        tr:hover td {
            background: rgba(255,255,255,0.02);
        }

        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
            margin-bottom: 1rem;
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            margin-bottom: 1.25rem;
        }

        label {
            font-size: 0.875rem;
            font-weight: 500;
            color: var(--text-secondary);
        }

        input, select, textarea {
            background: #0f0f11;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: var(--text-primary);
            padding: 0.75rem 1rem;
            font-family: var(--font-main);
            outline: none;
            transition: border-color 0.2s;
        }

        input:focus, select:focus, textarea:focus {
            border-color: var(--primary);
        }

        button {
            background: var(--primary);
            color: var(--text-primary);
            border: none;
            border-radius: 8px;
            padding: 0.75rem 1.5rem;
            font-weight: 600;
            cursor: pointer;
            transition: background-color 0.2s, transform 0.1s;
        }

        button:hover {
            background: var(--primary-hover);
        }

        button:active {
            transform: scale(0.98);
        }

        .btn-outline {
            background: transparent;
            border: 1px solid var(--primary);
            color: var(--primary);
        }

        .btn-outline:hover {
            background: rgba(139, 92, 246, 0.05);
        }

        /* Interactive log component */
        .terminal-log {
            background: #09090b;
            border: 1px solid var(--border-color);
            border-radius: 12px;
            font-family: var(--font-mono);
            padding: 1.25rem;
            font-size: 0.875rem;
            height: 300px;
            overflow-y: auto;
            color: #d1d5db;
        }

        .terminal-line {
            margin-bottom: 0.5rem;
            border-bottom: 1px dashed rgba(255, 255, 255, 0.02);
            padding-bottom: 0.25rem;
            display: flex;
            gap: 1rem;
        }

        .terminal-time {
            color: var(--primary);
            flex-shrink: 0;
        }

        .terminal-tag {
            color: var(--warning);
            font-weight: 600;
            flex-shrink: 0;
        }

        /* Keyframes */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Mesh details list */
        .provider-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 1.25rem;
        }

        .prov-card {
            background: #1c1917;
            border-radius: 10px;
            padding: 1.25rem;
            border: 1px solid var(--border-color);
            position: relative;
        }

        .prov-status {
            position: absolute;
            top: 1.25rem;
            right: 1.25rem;
        }

        /* Playground details */
        .playground-results {
            margin-top: 1.5rem;
            background: rgba(24, 24, 27, 0.8);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 1.5rem;
            display: none;
        }

        .metric-badges {
            display: flex;
            gap: 1rem;
            margin-top: 1rem;
        }

        .metric-badge {
            background: #27272a;
            border-radius: 6px;
            padding: 0.5rem 1rem;
            text-align: center;
        }

        .metric-label {
            font-size: 0.75rem;
            color: var(--text-secondary);
            text-transform: uppercase;
        }

        .metric-val {
            font-size: 1.125rem;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="ambient-glow"></div>
    <header>
        <h1><span>⚡</span> JARVIS Platform Control Panel</h1>
        <div class="header-status">
            <div class="status-badge">
                <span class="status-dot"></span>
                <span>Active Fabric Mesh Online</span>
            </div>
            <div style="font-size: 0.875rem; color: var(--text-secondary)">
                API Port: <span style="color: var(--text-primary); font-weight: bold;" id="display-port">...</span>
            </div>
        </div>
    </header>

    <div class="main-container">
        <sidebar>
            <ul class="nav-list">
                <li class="nav-item active" onclick="switchTab('dashboard')">Overview</li>
                <li class="nav-item" onclick="switchTab('fabric')">Fabric Nodes</li>
                <li class="nav-item" onclick="switchTab('mesh')">Service Mesh</li>
                <li class="nav-item" onclick="switchTab('sync')">Cloud Sync</li>
                <li class="nav-item" onclick="switchTab('memory')">Memory Space</li>
                <li class="nav-item" onclick="switchTab('router')">AI Router</li>
            </ul>
        </sidebar>

        <div class="content-area">
            
            <!-- OVERVIEW PANEL -->
            <div id="panel-dashboard" class="panel active">
                <div class="dashboard-grid">
                    <div class="card">
                        <div class="card-header">
                            <span class="card-title">Nodes Cluster Density</span>
                            <span style="font-size: 1.25rem;">🖥️</span>
                        </div>
                        <div class="card-value" id="count-nodes">0</div>
                        <div class="card-desc">Active instances in fabric routing mesh</div>
                    </div>
                    <div class="card">
                        <div class="card-header">
                            <span class="card-title">Cloud Sync Status</span>
                            <span style="font-size: 1.25rem;">☁️</span>
                        </div>
                        <div class="card-value" id="sync-status">OFFLINE</div>
                        <div class="card-desc" id="sync-desc">0 updates pending in queue</div>
                    </div>
                    <div class="card">
                        <div class="card-header">
                            <span class="card-title">Model Load balancer</span>
                            <span style="font-size: 1.25rem;">⚖️</span>
                        </div>
                        <div class="card-value" id="mesh-active-count">0/7</div>
                        <div class="card-desc">Online endpoints in proxy pool</div>
                    </div>
                </div>

                <div class="card" style="margin-bottom: 2rem;">
                    <div class="card-header">
                        <span class="card-title">Live Node Telemetry Event Pipeline</span>
                        <span>📊</span>
                    </div>
                    <div class="terminal-log" id="system-terminal">
                        <div class="terminal-line">
                            <span class="terminal-time">[System]</span>
                            <span class="terminal-tag">INFO</span>
                            <span>Awaiting SSE real-time stream binding registration...</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- FABRIC PANEL -->
            <div id="panel-fabric" class="panel">
                <div style="display: grid; grid-template-columns: 1fr 380px; gap: 2rem;">
                    <div class="card">
                        <div class="card-header">
                            <span class="card-title">Registered Fabric Nodes</span>
                        </div>
                        <table>
                            <thead>
                                <tr>
                                    <th>Node ID</th>
                                    <th>Device Type</th>
                                    <th>Connectivity Status</th>
                                    <th>Last Seen (Epoch)</th>
                                </tr>
                            </thead>
                            <tbody id="nodes-table-body">
                                <tr>
                                    <td colspan="4" style="text-align: center; color: var(--text-secondary)">No fabric nodes registered. Use registration tool.</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    <div class="card">
                        <div class="card-header">
                            <span class="card-title">Add Simulated Node</span>
                        </div>
                        <div class="form-group">
                            <label>Node Hostname / ID</label>
                            <input type="text" id="node-id-input" placeholder="e.g. desktop-workstation">
                        </div>
                        <div class="form-group">
                            <label>Device Platform Profile</label>
                            <select id="node-type-input">
                                <option value="DESKTOP">Desktop Workstation</option>
                                <option value="LAPTOP">Laptop Terminal</option>
                                <option value="MOBILE">Mobile Handheld</option>
                                <option value="CLOUD">Cloud Engine</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Live status</label>
                            <select id="node-status-input">
                                <option value="ONLINE">ONLINE (Healthy)</option>
                                <option value="OFFLINE">OFFLINE (Standby)</option>
                            </select>
                        </div>
                        <button style="width: 100%;" onclick="submitRegisterNode()">Register Local Node</button>
                    </div>
                </div>
            </div>

            <!-- SERVICE MESH PANEL -->
            <div id="panel-mesh" class="panel">
                <div class="card" style="margin-bottom: 2rem;">
                    <div class="card-header">
                        <span class="card-title">Mesh Telemetry & Cost Ledger</span>
                    </div>
                    <div class="provider-grid" id="mesh-provider-container">
                        <!-- Filled by JS -->
                    </div>
                </div>
            </div>

            <!-- CLOUD SYNC PANEL -->
            <div id="panel-sync" class="panel">
                <div style="display: grid; grid-template-columns: 350px 1fr; gap: 2rem;">
                    <div class="card">
                        <div class="card-header">
                            <span class="card-title">Sync Synchronization Broker</span>
                        </div>
                        <div class="form-group">
                            <label>Federation Network Link</label>
                            <div style="display: flex; gap: 1rem; margin-top: 0.5rem;">
                                <button id="btn-toggle-network" onclick="toggleSyncNetwork()" style="flex-grow: 1;">Connect Link</button>
                            </div>
                        </div>
                        <hr style="border-color: var(--border-color); margin: 1.5rem 0;">
                        <div class="form-group">
                            <span style="font-size: 0.875rem; color: var(--text-secondary);">Simulate configuration push:</span>
                        </div>
                        <div class="form-group">
                            <label>Key</label>
                            <input type="text" id="sync-key" placeholder="user_preferences:theme">
                        </div>
                        <div class="form-group">
                            <label>Value</label>
                            <input type="text" id="sync-value" placeholder="dark-glass">
                        </div>
                        <button style="width:100%;" onclick="pushSyncValue()">Push Value Change</button>
                    </div>

                    <div class="card">
                        <div class="card-header">
                            <span class="card-title">Replicated Local Storage</span>
                        </div>
                        <table>
                            <thead>
                                <tr>
                                    <th>Key</th>
                                    <th>Value</th>
                                </tr>
                            </thead>
                            <tbody id="sync-table-body">
                                <tr>
                                    <td colspan="2" style="text-align: center; color: var(--text-secondary);">Empty database cache.</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- MEMORY PANEL -->
            <div id="panel-memory" class="panel">
                <div style="display: grid; grid-template-columns: 350px 1fr; gap: 2rem;">
                    <div class="card">
                        <div class="card-header">
                            <span class="card-title">Federated Layer Write-Loop</span>
                        </div>
                        <div class="form-group">
                            <label>Memory Layer Target</label>
                            <select id="mem-layer-input">
                                <option value="session">Session RAM Cache</option>
                                <option value="working">Working Context Cache</option>
                                <option value="long_term">Long-Term Storage (Federated)</option>
                                <option value="project">Project Configuration (Federated)</option>
                                <option value="cloud">Cloud Remote Space</option>
                                <option value="graph">Knowledge Graph (Federated)</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Key</label>
                            <input type="text" id="mem-key-input" placeholder="e.g. system_model">
                        </div>
                        <div class="form-group">
                            <label>Data payload</label>
                            <input type="text" id="mem-val-input" placeholder="e.g. gpt-4o">
                        </div>
                        <button style="width: 100%;" onclick="submitWriteMemory()">Record Memory Log</button>
                    </div>

                    <div class="card">
                        <div class="card-header">
                            <span class="card-title">Memory Scopes Status & Values</span>
                        </div>
                        <table>
                            <thead>
                                <tr>
                                    <th>Scope</th>
                                    <th>Record Count</th>
                                    <th>Entries Details</th>
                                </tr>
                            </thead>
                            <tbody id="memory-table-body">
                                <!-- Populated by script -->
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- ROUTER PLAYGROUND PANEL -->
            <div id="panel-router" class="panel">
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Interactive AI Service Mesh Router Playground</span>
                    </div>
                    <div class="form-group">
                        <label>Input Prompt Query</label>
                        <textarea id="router-prompt" rows="3" placeholder="Draft a distributed enterprise synchronization design blueprint..."></textarea>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Scoring / Load Balancer Strategy</label>
                            <select id="router-strategy">
                                <option value="least-latency">Least Latency (Milliseconds optimization)</option>
                                <option value="cost-priority">Cost Priority (Budget execution efficiency)</option>
                                <option value="round-robin">Round-Robin (Fair-share rotation)</option>
                            </select>
                        </div>
                        <div class="form-group" style="justify-content: flex-end;">
                            <button onclick="executeRouterPrompt()" style="height: 43px;">Deploy Prompt to Mesh</button>
                        </div>
                    </div>

                    <div class="playground-results" id="router-results-box">
                        <h4 style="font-weight: 600; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem;">
                            <span style="color: var(--success); font-size: 1.25rem;">✔</span> Request Successfully Routed
                        </h4>
                        <div style="font-size: 0.9rem; margin-bottom: 1rem;" id="results-provider-node">Provider Used: ...</div>
                        
                        <div class="form-group">
                            <label>Agent Output Response</label>
                            <div style="background: #09090b; border: 1px solid var(--border-color); padding: 1rem; border-radius: 8px; font-family: var(--font-mono); font-size: 0.875rem;" id="results-response-box">
                                ...
                            </div>
                        </div>

                        <div class="metric-badges">
                            <div class="metric-badge">
                                <div class="metric-label">Execution Cost</div>
                                <div class="metric-val" id="results-cost">$0.0000</div>
                            </div>
                            <div class="metric-badge">
                                <div class="metric-label">Compute Latency</div>
                                <div class="metric-val" id="results-latency">0.00s</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

        </div>
    </div>

    <script>
        let token = "";
        let sseSource = null;

        // On document ready
        window.addEventListener('DOMContentLoaded', async () => {
            document.getElementById('display-port').innerText = window.location.port || '80';
            await authenticateAndRun();
        });

        async function authenticateAndRun() {
            try {
                // Fetch dynamic oauth token
                const response = await fetch('/oauth/token', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        client_id: 'jarvis_client',
                        client_secret: 'jarvis_secret'
                    })
                });
                const authData = await response.json();
                if (authData && authData.access_token) {
                    token = authData.access_token;
                    logToTerminal("System", "SUCCESS", "OAuth dynamic validation passed. Access token stored.");
                    
                    // Bind SSE stream
                    bindSSEStream();
                    
                    // Run polling routines
                    await updateAllData();
                    setInterval(updateAllData, 3000);
                } else {
                    logToTerminal("System", "ERROR", "OAuth verification failed. System locked.");
                }
            } catch (err) {
                logToTerminal("System", "ERROR", "Authentication route failure: " + err.message);
            }
        }

        function bindSSEStream() {
            if (sseSource) {
                sseSource.close();
            }
            // Bind using query param token
            sseSource = new EventSource('/api/v1/stream?token=' + encodeURIComponent(token));
            sseSource.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    logToTerminal(data.event_type, "NOTIFY", JSON.stringify(data.payload));
                } catch(e) {}
            };
            sseSource.onerror = function() {
                logToTerminal("Stream", "WARNING", "SSE Stream connection disconnected. Attempting automatic reconnection...");
            };
        }

        function logToTerminal(tag, level, message) {
            const term = document.getElementById("system-terminal");
            const line = document.createElement("div");
            line.className = "terminal-line";
            
            const timeSpan = document.createElement("span");
            timeSpan.className = "terminal-time";
            timeSpan.innerText = "[" + new Date().toLocaleTimeString() + "]";
            
            const tagSpan = document.createElement("span");
            tagSpan.className = "terminal-tag";
            tagSpan.innerText = tag.toUpperCase();
            
            const msgSpan = document.createElement("span");
            msgSpan.innerText = "(" + level + ") " + message;
            
            line.appendChild(timeSpan);
            line.appendChild(tagSpan);
            line.appendChild(msgSpan);
            term.appendChild(line);
            
            // Auto scroll to bottom
            term.scrollTop = term.scrollHeight;
        }

        async function switchTab(tabId) {
            document.querySelectorAll(".nav-item").forEach(item => item.classList.remove("active"));
            document.querySelectorAll(".panel").forEach(panel => panel.classList.remove("active"));
            
            // Find nav item by content or context
            event.currentTarget.classList.add("active");
            document.getElementById("panel-" + tabId).classList.add("active");
            await updateAllData();
        }

        async function fetchAPI(url, options = {}) {
            if (!options.headers) {
                options.headers = {};
            }
            options.headers["Authorization"] = "Bearer " + token;
            const res = await fetch(url, options);
            if (res.status === 401) {
                // Re-authenticate
                await authenticateAndRun();
                return null;
            }
            return res.json();
        }

        async function updateAllData() {
            if (!token) return;
            try {
                // 1. Health/Overview update
                const health = await fetchAPI('/api/v1/health');
                
                // 2. Nodes list
                const nodesData = await fetchAPI('/api/v1/nodes');
                if (nodesData && nodesData.nodes) {
                    document.getElementById('count-nodes').innerText = nodesData.nodes.length;
                    populateNodesTable(nodesData.nodes);
                }

                // 3. Cloud Sync state
                const syncData = await fetchAPI('/api/v1/sync');
                if (syncData) {
                    const online = syncData.online;
                    document.getElementById('sync-status').innerText = online ? "ONLINE" : "OFFLINE";
                    document.getElementById('sync-status').style.color = online ? "var(--success)" : "var(--danger)";
                    document.getElementById('sync-desc').innerText = syncData.offline_queue_size + " updates pending in queue";
                    
                    const btn = document.getElementById('btn-toggle-network');
                    btn.innerText = online ? "Disconnect Link" : "Connect Link";
                    btn.className = online ? "btn-outline" : "";
                    
                    populateSyncTable(syncData.local_store);
                }

                // 4. Mesh info
                const meshData = await fetchAPI('/api/v1/mesh');
                if (meshData && meshData.providers) {
                    let onlineCount = 0;
                    let totalCount = 0;
                    for (let p in meshData.providers) {
                        totalCount++;
                        if (meshData.providers[p].online) onlineCount++;
                    }
                    document.getElementById('mesh-active-count').innerText = onlineCount + "/" + totalCount;
                    populateMeshProviders(meshData.providers);
                }

                // 5. Memory scopes info
                const memData = await fetchAPI('/api/v1/memory');
                if (memData && memData.status) {
                    populateMemoryTable(memData.status, memData.data);
                }

            } catch (err) {
                console.error("Failed fetching panel metrics: ", err);
            }
        }

        function populateNodesTable(nodes) {
            const tbody = document.getElementById("nodes-table-body");
            if (!nodes || nodes.length === 0) {
                tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-secondary)">No fabric nodes registered. Use registration tool.</td></tr>`;
                return;
            }
            tbody.innerHTML = nodes.map(n => `
                <tr>
                    <td style="font-family: var(--font-mono); font-weight: bold;">${n.id}</td>
                    <td><span style="font-size: 0.75rem; background: #27272a; padding: 0.15rem 0.5rem; border-radius: 4px;">${n.device_type}</span></td>
                    <td>
                        <span style="color: ${n.status === 'ONLINE' ? 'var(--success)' : 'var(--text-secondary)'}; display: flex; align-items: center; gap: 0.25rem;">
                            <span style="width: 6px; height: 6px; border-radius: 50%; background-color: ${n.status === 'ONLINE' ? 'var(--success)' : 'var(--text-secondary)'}"></span>
                            ${n.status}
                        </span>
                    </td>
                    <td style="font-family: var(--font-mono);">${new Date(n.last_seen * 1000).toLocaleString()}</td>
                </tr>
            `).join('');
        }

        function populateSyncTable(store) {
            const tbody = document.getElementById("sync-table-body");
            const keys = Object.keys(store || {});
            if (keys.length === 0) {
                tbody.innerHTML = `<tr><td colspan="2" style="text-align: center; color: var(--text-secondary);">Empty database cache.</td></tr>`;
                return;
            }
            tbody.innerHTML = keys.map(k => `
                <tr>
                    <td style="font-family: var(--font-mono); font-weight: 500; color: #a78bfa;">${k}</td>
                    <td style="font-family: var(--font-mono);">${JSON.stringify(store[k])}</td>
                </tr>
            `).join('');
        }

        function populateMeshProviders(providers) {
            const container = document.getElementById("mesh-provider-container");
            container.innerHTML = Object.keys(providers).map(name => {
                const p = providers[name];
                return `
                    <div class="prov-card" style="border-left: 3px solid ${p.online ? 'var(--success)' : 'var(--danger)'}">
                        <div class="prov-status">
                            <span style="color: ${p.online ? 'var(--success)' : 'var(--danger)'}; font-size: 0.85rem; font-weight: 600;">
                                ${p.online ? 'ONLINE' : 'OFFLINE'}
                            </span>
                        </div>
                        <h4 style="font-size: 1.15rem; font-weight: bold; margin-bottom: 0.5rem; color: #f4f4f5; text-transform: capitalize;">${name}</h4>
                        <div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.25rem;">
                            Cost/1k: <span style="color: var(--text-primary); font-weight: 600;">$${p.cost}</span>
                        </div>
                        <div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.25rem;">
                            Avg Latency: <span style="color: var(--text-primary); font-weight: 600;">${p.latency_ms.toFixed(0)} ms</span>
                        </div>
                        <div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.25rem;">
                            Calls Logged: <span style="color: var(--text-primary); font-weight: 600;">${p.calls}</span>
                        </div>
                        <div style="font-size: 0.85rem; color: var(--text-secondary);">
                            Total Cost: <span style="color: var(--text-primary); font-weight: 600;">$${(p.cost * p.tokens / 1000).toFixed(4)}</span>
                        </div>
                    </div>
                `;
            }).join('');
        }

        function populateMemoryTable(status, data) {
            const tbody = document.getElementById("memory-table-body");
            tbody.innerHTML = Object.keys(status).map(layer => {
                const contents = data[layer] || {};
                const keys = Object.keys(contents);
                const desc = keys.length > 0 
                    ? keys.map(k => `<span style="color:#c084fc;">${k}</span>: ${JSON.stringify(contents[k])}`).join(', ')
                    : `<span style="color:var(--text-secondary)">No items</span>`;
                return `
                    <tr>
                        <td style="font-weight: 600; text-transform: capitalize;">${layer.replace('_', ' ')}</td>
                        <td style="font-family: var(--font-mono);">${status[layer]}</td>
                        <td style="font-size: 0.85rem; font-family: var(--font-mono);">${desc}</td>
                    </tr>
                `;
            }).join('');
        }

        async function submitRegisterNode() {
            const node_id = document.getElementById("node-id-input").value.trim();
            const device_type = document.getElementById("node-type-input").value;
            const status = document.getElementById("node-status-input").value;
            if (!node_id) {
                alert("Please enter a Node ID!");
                return;
            }
            await fetchAPI('/api/v1/nodes/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ node_id, device_type, status })
            });
            document.getElementById("node-id-input").value = "";
            logToTerminal("Panel", "SUCCESS", `Simulated node '${node_id}' registered successfully.`);
            await updateAllData();
        }

        async function submitWriteMemory() {
            const layer = document.getElementById("mem-layer-input").value;
            const key = document.getElementById("mem-key-input").value.trim();
            const value = document.getElementById("mem-val-input").value.trim();
            if (!key || !value) {
                alert("Please complete key and payload fields!");
                return;
            }
            await fetchAPI('/api/v1/memory/write', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ layer, key, value })
            });
            document.getElementById("mem-key-input").value = "";
            document.getElementById("mem-val-input").value = "";
            logToTerminal("Panel", "SUCCESS", `Wrote memory to '${layer}': ${key}.`);
            await updateAllData();
        }

        async function toggleSyncNetwork() {
            const syncData = await fetchAPI('/api/v1/sync');
            const newStatus = !syncData.online;
            await fetchAPI('/api/v1/sync/status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ online: newStatus })
            });
            logToTerminal("Panel", "SUCCESS", `Network link changed to ${newStatus ? 'ONLINE' : 'OFFLINE'}.`);
            await updateAllData();
        }

        async function pushSyncValue() {
            const key = document.getElementById("sync-key").value.trim();
            const value = document.getElementById("sync-value").value.trim();
            if (!key) {
                alert("Key is required!");
                return;
            }
            await fetchAPI('/api/v1/sync/push', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key, value })
            });
            document.getElementById("sync-key").value = "";
            document.getElementById("sync-value").value = "";
            logToTerminal("Panel", "SUCCESS", `Pushed local sync change: ${key}`);
            await updateAllData();
        }

        async function executeRouterPrompt() {
            const prompt = document.getElementById("router-prompt").value.trim();
            const strategy = document.getElementById("router-strategy").value;
            if (!prompt) {
                alert("Please type a prompt first!");
                return;
            }
            
            // Show processing box
            const box = document.getElementById("router-results-box");
            box.style.display = "block";
            document.getElementById("results-provider-node").innerText = "Routing payload through proxy pool...";
            document.getElementById("results-response-box").innerText = "Awaiting response token streams...";
            document.getElementById("results-cost").innerText = "$0.0000";
            document.getElementById("results-latency").innerText = "0.00s";

            const res = await fetchAPI('/api/v1/route', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt, strategy })
            });

            if (res) {
                if (res.success) {
                    document.getElementById("results-provider-node").innerHTML = `Routed successfully to provider: <span style="color:#a78bfa; font-weight:bold; text-transform:uppercase;">${res.provider}</span>`;
                    document.getElementById("results-response-box").innerText = res.response;
                    document.getElementById("results-cost").innerText = "$" + res.cost.toFixed(5);
                    document.getElementById("results-latency").innerText = res.latency_sec.toFixed(2) + "s";
                } else {
                    document.getElementById("results-provider-node").innerHTML = `<span style="color:var(--danger)">Routing Error: All backends unreachable</span>`;
                    document.getElementById("results-response-box").innerText = res.error;
                }
            }
            await updateAllData();
        }
    </script>
</body>
</html>
"""
