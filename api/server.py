"""Developer REST & WebSocket API gateway server for JARVIS."""

from __future__ import annotations
import http.server
import socketserver
import json
import time
import urllib.parse
import logging
import threading
from typing import Any

from remote_api import RemoteApiHandler, ThreadedRemoteApiServer, RemoteGateway
from service_mesh import AIServiceMesh
from knowledge_graph import ProductionKnowledgeGraph
from workflow_engine import Workflow
from workflow_scheduler import WorkflowScheduler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("developer.api_server")


class DeveloperApiHandler(RemoteApiHandler):
    """Extends RemoteApiHandler to expose Swagger OpenAPI layouts and developer endpoints."""

    def do_GET(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        # 1. Serve OpenAPI spec JSON
        if path == "/openapi.json":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(OPENAPI_SPEC).encode("utf-8"))
            return

        # 2. Serve Swagger Documentation Playground
        if path == "/docs":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(SWAGGER_HTML.encode("utf-8"))
            return

        # 3. Handle standard REST health checks
        if path == "/api/v1/health":
            super().do_GET()
            return

        # Authenticate and rate limit all developer API routes
        if not self._authenticate() or not self._check_rate_limit():
            return

        if path == "/api/v1/graph":
            kg = ProductionKnowledgeGraph()
            self._send_json(200, {
                "nodes": list(kg.nodes.values()),
                "edges": kg.edges
            })
            
        elif path == "/api/v1/plugins":
            # List registry stats
            from plugin_manager import PluginManager
            mgr = PluginManager()
            self._send_json(200, {"plugins": mgr.get_plugin_metrics()})
            
        elif path == "/api/v1/diagnostics":
            import psutil
            import threading
            proc = psutil.Process()
            self._send_json(200, {
                "cpu_percent": proc.cpu_percent(),
                "memory_rss_mb": proc.memory_info().rss / (1024 * 1024),
                "threads_count": threading.active_count()
            })
            
        else:
            # Fallback to remote_api.py routes (e.g. /api/v1/memory, /api/v1/nodes, /api/v1/mesh, /api/v1/stream)
            super().do_GET()

    def do_POST(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        # Authenticate and limit POST requests
        if path == "/oauth/token":
            super().do_POST()
            return

        if not self._authenticate() or not self._check_rate_limit():
            return

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body) if body else {}
        except Exception as e:
            self._send_json(400, {"error": "Bad Request", "message": str(e)})
            return

        if path == "/api/v1/ai":
            # Alternate route for routing prompts
            prompt = data.get("prompt")
            strategy = data.get("strategy", "least-latency")
            if not prompt:
                self._send_json(400, {"error": "Bad Request", "message": "Missing prompt."})
                return
            mesh = AIServiceMesh()
            res = mesh.failover_execute(prompt, strategy)
            self.server.gateway.broadcast_event("REQUEST_ROUTED", {"prompt": prompt, "result": res})
            self._send_json(200, res)

        elif path == "/api/v1/workflow":
            # Dispatch workflow JSON data
            name = data.get("name")
            nodes_data = data.get("nodes", [])
            if not name or not nodes_data:
                self._send_json(400, {"error": "Bad Request", "message": "Workflow name and nodes list required."})
                return
                
            try:
                wf_str = json.dumps({"name": name, "nodes": nodes_data})
                wf = Workflow.from_json(wf_str)
                scheduler = WorkflowScheduler()
                
                # Execute in background thread
                scheduler.execute(wf, callback=lambda w: self.server.gateway.broadcast_event("WORKFLOW_COMPLETED", {"name": w.name, "status": w.status}))
                self.server.gateway.broadcast_event("WORKFLOW_STARTED", {"name": wf.name})
                self._send_json(200, {"status": "SUCCESS", "message": "Workflow run enqueued."})
            except Exception as e:
                self._send_json(400, {"error": "Bad Request", "message": f"DAG parsing error: {e}"})
                
        else:
            # Fallback (e.g. /api/v1/nodes/register, /api/v1/sync/push, /api/v1/memory/write)
            # Reconstruct request body wrapper to keep handler clean
            self.rfile = urllib.parse.BytesIO(json.dumps(data).encode("utf-8"))
            super().do_POST()


class DeveloperGateway(RemoteGateway):
    """Developer API server hosting the subclassed OpenAPI endpoint handler."""

    def start(self) -> None:
        self.running = True
        self.http_server = ThreadedRemoteApiServer((self.host, self.port), DeveloperApiHandler)
        self.http_server.oauth_manager = self.oauth_manager
        self.http_server.rate_limiter = self.rate_limiter
        self.http_server.fabric = self.fabric
        self.http_server.sync_manager = self.sync_manager
        self.http_server.memory = self.memory
        self.http_server.service_mesh = self.service_mesh
        self.http_server.gateway = self
        self.http_server.start_time = time.time()

        self.port = self.http_server.server_address[1]
        self.http_thread = threading.Thread(target=self.http_server.serve_forever, daemon=True)
        self.http_thread.start()
        logger.info(f"OpenAPI Server & Swagger UI live on http://{self.host}:{self.port}/docs")

        self.tcp_thread = threading.Thread(target=self._run_tcp_server, daemon=True)
        self.tcp_thread.start()


# Swagger Spec definitions
OPENAPI_SPEC = {
  "openapi": "3.0.0",
  "info": {
    "title": "JARVIS Developer Platform API",
    "version": "1.0.0",
    "description": "Secure API endpoints to automate, extend, and integrate with the JARVIS AI Operating Platform."
  },
  "paths": {
    "/oauth/token": {
      "post": {
        "summary": "Retrieve OAuth Authorization Bearer Token",
        "requestBody": {
          "required": True,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "client_id": {"type": "string"},
                  "client_secret": {"type": "string"}
                }
              }
            }
          }
        },
        "responses": {
          "200": {"description": "Access token wrapper details"}
        }
      }
    },
    "/api/v1/health": {
      "get": {
        "summary": "Public health status checking",
        "responses": {
          "200": {"description": "System health details"}
        }
      }
    },
    "/api/v1/ai": {
      "post": {
        "summary": "Route client prompt through the service mesh balancer",
        "responses": {
          "200": {"description": "LLM text execution response"}
        }
      }
    },
    "/api/v1/graph": {
      "get": {
        "summary": "Expose entire property KnowledgeGraph nodes and relationships",
        "responses": {
          "200": {"description": "Nodes and edges listings"}
        }
      }
    },
    "/api/v1/diagnostics": {
      "get": {
        "summary": "Expose system resource allocations and thread states",
        "responses": {
          "200": {"description": "Memory and thread status metrics"}
        }
      }
    }
  }
}

SWAGGER_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>JARVIS OpenAPI Playground</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui.css" />
  <style>
    body { background-color: #09090b; color: #f4f4f5; font-family: sans-serif; margin: 0; }
    .swagger-ui .topbar { display: none; }
    .swagger-ui .info .title { color: #8b5cf6 !important; }
    .swagger-ui { filter: invert(0.9) hue-rotate(180deg); }
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-bundle.js"></script>
  <script>
    window.onload = () => {
      window.ui = SwaggerUIBundle({
        url: '/openapi.json',
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIBundle.SwaggerUIStandalonePreset
        ]
      });
    };
  </script>
</body>
</html>
"""
