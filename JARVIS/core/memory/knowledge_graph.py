"""Knowledge Graph for semantic linking of conversations, projects, files, notes, tasks, and rules."""

from __future__ import annotations

import json
import os
from typing import Any

from JARVIS.core.system.utils.jarvis_logging import get_logger

logger = get_logger("knowledge_graph")


class KnowledgeGraph:
    """Manages an in-memory property graph with local JSON persistence."""

    _instance: KnowledgeGraph | None = None

    def __new__(cls, *args, **kwargs) -> KnowledgeGraph:
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.graph_path = os.path.abspath(os.path.join("logs", "knowledge_graph.json"))
        self.nodes: dict[str, dict[str, Any]] = {}  # node_id -> {type, label, properties}
        self.edges: list[dict[str, Any]] = []  # list of {source, target, relation, properties}
        self.load()
        if not os.path.exists(self.graph_path):
            self.save()

    def load(self) -> None:
        """Load knowledge graph from JSON file."""
        if os.path.exists(self.graph_path):
            try:
                with open(self.graph_path, encoding="utf-8") as f:
                    data = json.load(f)
                    self.nodes = data.get("nodes", {})
                    self.edges = data.get("edges", [])
                logger.info("Loaded Knowledge Graph: %d nodes, %d edges.", len(self.nodes), len(self.edges))
            except Exception as e:
                logger.error("Failed to load Knowledge Graph: %s", e)
                self.nodes = {}
                self.edges = []
        else:
            self.nodes = {}
            self.edges = []

    def save(self) -> None:
        """Persist knowledge graph to JSON file."""
        os.makedirs(os.path.dirname(self.graph_path), exist_ok=True)
        try:
            with open(self.graph_path, "w", encoding="utf-8") as f:
                json.dump({"nodes": self.nodes, "edges": self.edges}, f, indent=2)
        except Exception as e:
            logger.error("Failed to save Knowledge Graph: %s", e)

    def add_node(self, node_id: str, node_type: str, label: str, properties: dict | None = None) -> None:
        """Add or update a node in the graph."""
        self.nodes[node_id] = {"type": node_type, "label": label, "properties": properties or {}}
        self.save()

    def add_edge(self, source: str, target: str, relation: str, properties: dict | None = None) -> None:
        """Add an edge between two existing nodes."""
        if source not in self.nodes or target not in self.nodes:
            logger.warning("Attempted to add edge between non-existent nodes: %s -> %s", source, target)
            return

        # Check if identical edge already exists
        for edge in self.edges:
            if edge["source"] == source and edge["target"] == target and edge["relation"] == relation:
                edge["properties"].update(properties or {})
                self.save()
                return

        self.edges.append({"source": source, "target": target, "relation": relation, "properties": properties or {}})
        self.save()

    def get_node(self, node_id: str) -> dict | None:
        """Retrieve a specific node."""
        return self.nodes.get(node_id)

    def get_related_nodes(self, node_id: str, relation: str | None = None) -> list[tuple[dict, str]]:
        """Retrieve nodes connected to node_id, optionally filtered by relation."""
        related = []
        for edge in self.edges:
            if relation and edge["relation"] != relation:
                continue
            if edge["source"] == node_id:
                target_node = self.nodes.get(edge["target"])
                if target_node:
                    related.append((target_node, edge["relation"]))
            elif edge["target"] == node_id:
                source_node = self.nodes.get(edge["source"])
                if source_node:
                    related.append((source_node, f"rev_{edge['relation']}"))
        return related

    def semantic_search(self, query: str) -> list[dict]:
        """Perform a keyword property match across all nodes in the graph."""
        query = query.lower()
        results = []
        for node_id, node in self.nodes.items():
            match = False
            if query in node_id.lower() or query in node["label"].lower() or query in node["type"].lower():
                match = True
            else:
                for k, v in node["properties"].items():
                    if query in str(v).lower():
                        match = True
                        break
            if match:
                res = node.copy()
                res["id"] = node_id
                results.append(res)
        return results

    def get_context_for_query(self, query: str) -> str:
        """Find nodes matching query and return a concatenated context block."""
        matched = self.semantic_search(query)
        if not matched:
            return ""

        context_parts = []
        for node in matched[:5]:  # limit to top 5
            part = f"- Node [{node['type']}] {node['label']}"
            props = [f"{k}={v}" for k, v in node["properties"].items()]
            if props:
                part += f" ({', '.join(props)})"
            context_parts.append(part)
        return "Knowledge Graph Context:\n" + "\n".join(context_parts)
