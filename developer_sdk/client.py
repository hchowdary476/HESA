"""Python Client wrapper for the JARVIS Distributed platform REST APIs."""

from __future__ import annotations
import requests
from typing import Any


class AINamespace:
    def __init__(self, client: JarvisClient) -> None:
        self.client = client

    def route(self, prompt: str, strategy: str = "least-latency") -> dict[str, Any]:
        """Routes prompt to optimal model in service mesh proxy pool."""
        return self.client.post("/api/v1/route", {"prompt": prompt, "strategy": strategy})


class MemoryNamespace:
    def __init__(self, client: JarvisClient) -> None:
        self.client = client

    def read_all(self) -> dict[str, Any]:
        """Retrieves statistics and values across all memory layers."""
        return self.client.get("/api/v1/memory")

    def write(self, layer: str, key: str, value: Any, project_id: str | None = None) -> dict[str, Any]:
        """Records a new memory log entry."""
        payload = {"layer": layer, "key": key, "value": value}
        if project_id:
            payload["project_id"] = project_id
        return self.client.post("/api/v1/memory/write", payload)


class GraphNamespace:
    def __init__(self, client: JarvisClient) -> None:
        self.client = client

    def list_nodes(self) -> dict[str, Any]:
        """Returns routing details of connected fabric devices."""
        return self.client.get("/api/v1/nodes")

    def register_node(self, node_id: str, device_type: str = "DESKTOP", status: str = "ONLINE") -> dict[str, Any]:
        """Registers a new node in the fabric."""
        return self.client.post("/api/v1/nodes/register", {
            "node_id": node_id,
            "device_type": device_type,
            "status": status
        })


class WorkflowNamespace:
    def __init__(self, client: JarvisClient) -> None:
        self.client = client

    def get_status(self) -> dict[str, Any]:
        """Fetches active execution histories and queues status."""
        return self.client.get("/api/v1/health")  # fallback status


class PluginsNamespace:
    def __init__(self, client: JarvisClient) -> None:
        self.client = client

    def get_mesh_analytics(self) -> dict[str, Any]:
        """Collects load-balancer latency and cost metrics across providers."""
        return self.client.get("/api/v1/mesh")


class JarvisClient:
    """Official developer client for interfacing with JARVIS Operating Platforms."""

    def __init__(self, base_url: str = "http://127.0.0.1:18010", token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        
        # Initialize namespaces
        self.ai = AINamespace(self)
        self.memory = MemoryNamespace(self)
        self.graph = GraphNamespace(self)
        self.workflow = WorkflowNamespace(self)
        self.plugins = PluginsNamespace(self)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def get(self, endpoint: str) -> dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        resp = requests.get(url, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def post(self, endpoint: str, json_data: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        resp = requests.post(url, headers=self._headers(), json=json_data)
        resp.raise_for_status()
        return resp.json()
