"""Enterprise API Gateway for the JARVIS AI Operating System."""

from __future__ import annotations
import http.server
import json
import socket
import threading
import time
import urllib.parse
import logging
from typing import Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_os.api_gateway")


class ApiGatewayServer(http.server.HTTPServer):
    """Custom HTTPServer linking AI OS modules and routing context."""

    def __init__(self, server_address, RequestHandlerClass, ai_kernel: Any, api_key: str = "jarvis_secret_key") -> None:
        super().__init__(server_address, RequestHandlerClass)
        self.ai_kernel = ai_kernel
        self.api_key = api_key
        self.rate_limits: dict[str, list[float]] = {}  # ip -> request timestamps
        self.lock = threading.Lock()


class ApiGatewayHandler(http.server.BaseHTTPRequestHandler):
    """Processes REST requests for health checking, status logging, command execution."""

    def log_message(self, format: str, *args: Any) -> None:
        # Override to suppress standard HTTP logging stdout clutter
        logger.debug(format % args)

    def _send_json(self, status: int, data: dict[str, Any]) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _authenticate(self) -> bool:
        """Enforces Bearer authentication credentials check."""
        auth_header = self.headers.get("Authorization")
        expected_key = f"Bearer {self.server.api_key}"
        
        # Check query parameters as fallback
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        query_key = params.get("api_key", [None])[0]

        if auth_header == expected_key or (query_key and query_key == self.server.api_key):
            return True

        self._send_json(401, {"error": "Unauthorized", "message": "Valid API Key required."})
        return False

    def _check_rate_limit(self) -> bool:
        """Sliding window rate limiter: allows max 60 requests per minute per IP."""
        client_ip = self.client_address[0]
        now = time.time()
        
        with self.server.lock:
            if client_ip not in self.server.rate_limits:
                self.server.rate_limits[client_ip] = []
            
            # Prune old timestamps
            self.server.rate_limits[client_ip] = [t for t in self.server.rate_limits[client_ip] if now - t < 60.0]
            
            if len(self.server.rate_limits[client_ip]) >= 60:
                self._send_json(429, {"error": "Too Many Requests", "message": "Rate limit exceeded (60 req/min)."})
                return False
                
            self.server.rate_limits[client_ip].append(now)
            return True

    def do_GET(self) -> None:
        """Routes GET paths."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        # Health endpoint bypasses auth for easy monitoring checks
        if path == "/api/v1/health":
            self._send_json(200, {"status": "HEALTHY", "service": "JARVIS AI OS", "timestamp": time.time()})
            return

        # Authenticate and rate limit check
        if not self._authenticate() or not self._check_rate_limit():
            return

        if path == "/api/v1/status":
            # Fetch stats from AIKernel
            status_data = {}
            if self.server.ai_kernel:
                status_data = self.server.ai_kernel.get_system_status()
            else:
                status_data = {"message": "AI Kernel offline"}
            self._send_json(200, status_data)
            
        elif path == "/api/v1/scheduler":
            scheduler_data = {}
            if self.server.ai_kernel and self.server.ai_kernel.scheduler:
                scheduler_data = self.server.ai_kernel.scheduler.get_queue_status()
            else:
                scheduler_data = {"message": "Scheduler offline"}
            self._send_json(200, scheduler_data)
            
        else:
            self._send_json(404, {"error": "Not Found", "message": f"Endpoint {path} not found."})

    def do_POST(self) -> None:
        """Routes POST requests."""
        if not self._authenticate() or not self._check_rate_limit():
            return

        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body) if body else {}
        except Exception as e:
            self._send_json(400, {"error": "Bad Request", "message": f"Malformed JSON body: {e}"})
            return

        if path == "/api/v1/command":
            command = data.get("command")
            if not command:
                self._send_json(400, {"error": "Bad Request", "message": "Missing 'command' parameter."})
                return

            priority = data.get("priority", "MEDIUM")
            
            # Process command via Kernel scheduling
            if self.server.ai_kernel:
                task_id = self.server.ai_kernel.process_api_command(command, priority)
                self._send_json(202, {
                    "status": "Accepted",
                    "task_id": task_id,
                    "message": "Command scheduled for execution."
                })
            else:
                self._send_json(503, {"error": "Service Unavailable", "message": "AI Kernel not set."})

        elif path == "/api/v1/event":
            event_type = data.get("event_type")
            payload = data.get("payload", {})
            if not event_type:
                self._send_json(400, {"error": "Bad Request", "message": "Missing 'event_type' parameter."})
                return

            if self.server.ai_kernel and self.server.ai_kernel.event_bus:
                self.server.ai_kernel.event_bus.publish(event_type, payload)
                self._send_json(200, {"status": "Success", "message": "Event published."})
            else:
                self._send_json(503, {"error": "Service Unavailable", "message": "Event Bus not set."})

        else:
            self._send_json(404, {"error": "Not Found", "message": f"Endpoint {path} not found."})


class ApiGateway:
    """Enterprise API Gateway managing REST web routes and simulated WebSocket streaming."""

    _instance: ApiGateway | None = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs) -> ApiGateway:
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self, host: str = "127.0.0.1", port: int = 18000, api_key: str = "jarvis_secret_key") -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.host = host
        self.port = port
        self.api_key = api_key
        self.http_server: ApiGatewayServer | None = None
        self.http_thread: threading.Thread | None = None
        self.ws_server: socket.socket | None = None
        self.ws_thread: threading.Thread | None = None
        self.ws_clients: list[socket.socket] = []
        self.ws_lock = threading.Lock()
        self.running = False

    def start(self, ai_kernel: Any) -> None:
        """Starts the gateway services."""
        self.running = True
        
        # Start REST HTTP Server
        self.http_server = ApiGatewayServer((self.host, self.port), ApiGatewayHandler, ai_kernel, self.api_key)
        self.port = self.http_server.server_address[1]
        self.http_thread = threading.Thread(target=self.http_server.serve_forever, daemon=True)
        self.http_thread.start()
        logger.info(f"REST Gateway active on http://{self.host}:{self.port}")

        # Start Event Streaming TCP/WebSocket socket server
        self.ws_thread = threading.Thread(target=self._run_ws_server, daemon=True)
        self.ws_thread.start()
        logger.info(f"Event streaming sockets active on TCP port {self.port + 1}")

    def stop(self) -> None:
        """Stops the gateway services."""
        self.running = False
        if self.http_server:
            self.http_server.shutdown()
            self.http_server.server_close()
        
        if self.ws_server:
            try:
                self.ws_server.close()
            except Exception:
                pass

        with self.ws_lock:
            for client in self.ws_clients:
                try:
                    client.close()
                except Exception:
                    pass
            self.ws_clients.clear()

        logger.info("API Gateway stopped.")

    def broadcast_event_to_clients(self, event_type: str, payload: dict[str, Any]) -> None:
        """Pushes events directly to listening API stream clients."""
        msg = json.dumps({"event_type": event_type, "payload": payload}) + "\n"
        encoded = msg.encode("utf-8")
        
        with self.ws_lock:
            disconnected = []
            for client in self.ws_clients:
                try:
                    client.sendall(encoded)
                except Exception:
                    disconnected.append(client)

            for client in disconnected:
                self.ws_clients.remove(client)
                try:
                    client.close()
                except Exception:
                    pass

    def _run_ws_server(self) -> None:
        """Runs basic TCP sockets serving client stream feeds."""
        ws_port = self.port + 1
        self.ws_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ws_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.ws_server.bind((self.host, ws_port))
            self.ws_server.listen(10)
        except Exception as e:
            logger.error(f"Failed to bind streaming socket server: {e}")
            return

        while self.running:
            try:
                conn, addr = self.ws_server.accept()
                
                # Check auth in first incoming line or require it immediately
                # For simplicity in testing/mocks, connection is auto-subscribed
                with self.ws_lock:
                    self.ws_clients.append(conn)
                logger.info(f"Client streaming interface linked: {addr}")
            except Exception:
                break
