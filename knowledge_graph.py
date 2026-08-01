"""Production-grade Knowledge Graph representing entity relationships for JARVIS."""

from __future__ import annotations
import os
import json
import logging
from typing import Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("memory.knowledge_graph")


class ProductionKnowledgeGraph:
    """Manages an in-memory property graph with local JSON persistence."""

    _instance: ProductionKnowledgeGraph | None = None

    def __new__(cls, *args, **kwargs) -> ProductionKnowledgeGraph:
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path: str = "logs/production_memory/knowledge_graph.json") -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.db_path = os.path.abspath(db_path)
        self.nodes: dict[str, dict[str, Any]] = {}  # node_id -> {type, label, properties}
        self.edges: list[dict[str, Any]] = []      # list of {source, target, relation, properties}
        self.load()

    def load(self) -> None:
        """Load knowledge graph from JSON file."""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.nodes = data.get("nodes", {})
                    self.edges = data.get("edges", [])
                logger.info(f"Loaded Knowledge Graph: {len(self.nodes)} nodes, {len(self.edges)} edges.")
            except Exception as e:
                logger.error(f"Failed to load Knowledge Graph: {e}")
                self.nodes = {}
                self.edges = []
        else:
            self.nodes = {}
            self.edges = []

    def save(self) -> None:
        """Persist knowledge graph to JSON file."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump({
                    "nodes": self.nodes,
                    "edges": self.edges
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save Knowledge Graph: {e}")

    def add_node(self, node_id: str, node_type: str, label: str, properties: dict | None = None) -> None:
        """Add or update a node in the graph."""
        self.nodes[node_id] = {
            "type": node_type.upper(),  # USER, PROJECT, FILE, CONVERSATION, AGENT, WORKFLOW, TOOL, PLUGIN, DOCUMENT, TASK
            "label": label,
            "properties": properties or {}
        }
        self.save()

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        """Retrieve a specific node's details."""
        node = self.nodes.get(node_id)
        if node:
            res = node.copy()
            res["id"] = node_id
            return res
        return None

    def remove_node(self, node_id: str) -> bool:
        """Removes a node and cascades to delete all incident edges."""
        if node_id not in self.nodes:
            return False
        
        del self.nodes[node_id]
        # Cascade delete edges
        self.edges = [edge for edge in self.edges if edge["source"] != node_id and edge["target"] != node_id]
        self.save()
        logger.info(f"Removed node '{node_id}' and all associated edges.")
        return True

    def add_edge(self, source: str, target: str, relation: str, properties: dict | None = None) -> None:
        """Add an edge between two existing nodes."""
        if source not in self.nodes or target not in self.nodes:
            logger.warning(f"Edge creation rejected: nodes '{source}' or '{target}' do not exist.")
            return

        relation_upper = relation.upper()  # USES, CREATED, DEPENDS_ON, RELATED_TO, EXECUTED, REFERENCES, UPDATED

        # Check if identical edge already exists, update properties if so
        for edge in self.edges:
            if edge["source"] == source and edge["target"] == target and edge["relation"] == relation_upper:
                edge["properties"].update(properties or {})
                self.save()
                return

        self.edges.append({
            "source": source,
            "target": target,
            "relation": relation_upper,
            "properties": properties or {}
        })
        self.save()

    def remove_edge(self, source: str, target: str, relation: str) -> bool:
        """Removes a specific edge from the graph."""
        relation_upper = relation.upper()
        initial_count = len(self.edges)
        self.edges = [
            e for e in self.edges 
            if not (e["source"] == source and e["target"] == target and e["relation"] == relation_upper)
        ]
        if len(self.edges) < initial_count:
            self.save()
            return True
        return False

    def get_related_nodes(self, node_id: str, relation: str | None = None) -> list[dict[str, Any]]:
        """Retrieve details of nodes connected to node_id, optionally filtered by relation type."""
        related = []
        rel_upper = relation.upper() if relation else None
        
        for edge in self.edges:
            if rel_upper and edge["relation"] != rel_upper:
                continue
                
            if edge["source"] == node_id:
                target_node = self.get_node(edge["target"])
                if target_node:
                    target_node["relationship"] = edge["relation"]
                    target_node["direction"] = "OUTGOING"
                    target_node["edge_properties"] = edge["properties"]
                    related.append(target_node)
            elif edge["target"] == node_id:
                source_node = self.get_node(edge["source"])
                if source_node:
                    source_node["relationship"] = edge["relation"]
                    source_node["direction"] = "INCOMING"
                    source_node["edge_properties"] = edge["properties"]
                    related.append(source_node)
        return related

    def get_shortest_path(self, start_id: str, end_id: str) -> list[str] | None:
        """Finds the shortest path between start_id and end_id using Breadth-First Search (BFS)."""
        if start_id not in self.nodes or end_id not in self.nodes:
            return None
        if start_id == end_id:
            return [start_id]

        # Build adjacency map
        adj: dict[str, set[str]] = {nid: set() for nid in self.nodes}
        for edge in self.edges:
            src, tgt = edge["source"], edge["target"]
            # Treat as undirected for general shortest path traversal
            if src in adj and tgt in adj:
                adj[src].add(tgt)
                adj[tgt].add(src)

        # BFS queue elements contain: (current_node, path_taken)
        queue = [(start_id, [start_id])]
        visited = {start_id}

        while queue:
            curr, path = queue.pop(0)
            if curr == end_id:
                return path

            for neighbor in adj[curr]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None  # No path found

    def find_subgraph(self, node_types: list[str] | None = None, relations: list[str] | None = None) -> dict[str, Any]:
        """Filters nodes and edges to extract a matching subgraph layout."""
        filtered_nodes = {}
        node_types_upper = [t.upper() for t in node_types] if node_types else None
        relations_upper = [r.upper() for r in relations] if relations else None

        for nid, n in self.nodes.items():
            if not node_types_upper or n["type"] in node_types_upper:
                filtered_nodes[nid] = n

        filtered_edges = []
        for edge in self.edges:
            # Check edge relationship filter
            if relations_upper and edge["relation"] not in relations_upper:
                continue
            # Edge nodes must exist in our filtered list
            if edge["source"] in filtered_nodes and edge["target"] in filtered_nodes:
                filtered_edges.append(edge)

        return {
            "nodes": filtered_nodes,
            "edges": filtered_edges
        }

    def clear(self) -> None:
        """Clears the graph memory cache."""
        self.nodes.clear()
        self.edges.clear()
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass
