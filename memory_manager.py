"""Memory Manager for JARVIS - Governance, backups, telemetry, and selective forget controls."""

from __future__ import annotations
import os
import time
import logging
from typing import Any

from knowledge_graph import ProductionKnowledgeGraph
from semantic_search import SemanticSearchEngine
from memory_engine import MemoryEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("memory.manager")


class MemoryManager:
    """Manages diagnostics, privacy limits, selective forget, and ACL permissions."""

    _instance: MemoryManager | None = None

    def __new__(cls, *args, **kwargs) -> MemoryManager:
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        
        self.kg = ProductionKnowledgeGraph()
        self.semantic_index = SemanticSearchEngine()
        self.memory = MemoryEngine()

        # Learnings cache
        self.tool_frequencies: dict[str, int] = {}
        self.model_frequencies: dict[str, int] = {}
        self.language_frequencies: dict[str, int] = {}
        self.project_frequencies: dict[str, int] = {}

    def get_memory_analytics(self) -> dict[str, Any]:
        """Gathers growth statistics, database sizes, and retrieval latencies."""
        logger.info("Computing Memory Subsystem Analytics...")
        
        # Calculate local database files sizes
        db_root = self.memory.data_root
        total_bytes = 0
        if os.path.exists(db_root):
            for entry in os.listdir(db_root):
                file_path = os.path.join(db_root, entry)
                if os.path.isfile(file_path):
                    total_bytes += os.path.getsize(file_path)

        # Measure simulated search latency
        t0 = time.time()
        self.semantic_index.search("health", top_k=1)
        latency_ms = (time.time() - t0) * 1000.0

        # Most used tools
        sorted_tools = sorted(self.tool_frequencies.items(), key=lambda x: x[1], reverse=True)
        most_used_tool = sorted_tools[0][0] if sorted_tools else "None"

        # Most used projects
        sorted_projects = sorted(self.project_frequencies.items(), key=lambda x: x[1], reverse=True)
        most_used_project = sorted_projects[0][0] if sorted_projects else "None"

        return {
            "memory_size_bytes": total_bytes,
            "knowledge_nodes": len(self.kg.nodes),
            "knowledge_relationships": len(self.kg.edges),
            "retrieval_speed_ms": latency_ms,
            "learning_statistics": {
                "preferred_model": self.get_preferred_model(),
                "preferred_language": self.get_preferred_language(),
                "most_used_tool": most_used_tool,
                "most_used_project": most_used_project
            },
            "growth_rate_percentage": 0.0  # calculated over time
        }

    def track_learning_interaction(self, model: str, language: str, tools_used: list[str], project_id: str | None = None) -> None:
        """Tracks tool, model, and language frequencies to adapt preference suggestions."""
        if model:
            self.model_frequencies[model] = self.model_frequencies.get(model, 0) + 1
            # Update in long-term memory
            self.memory.write_memory("long_term", "preferred_model", self.get_preferred_model())
        
        if language:
            self.language_frequencies[language] = self.language_frequencies.get(language, 0) + 1
            self.memory.write_memory("long_term", "preferred_language", self.get_preferred_language())
            
        for t in tools_used:
            self.tool_frequencies[t] = self.tool_frequencies.get(t, 0) + 1
            
        if project_id:
            self.project_frequencies[project_id] = self.project_frequencies.get(project_id, 0) + 1

    def get_preferred_model(self) -> str:
        """Determines most frequent AI model."""
        if not self.model_frequencies:
            return "Gemini 1.5 Pro"  # default fallback
        return max(self.model_frequencies, key=self.model_frequencies.get)

    def get_preferred_language(self) -> str:
        """Determines most frequent coding language."""
        if not self.language_frequencies:
            return "Python"
        return max(self.language_frequencies, key=self.language_frequencies.get)

    def selective_forget(self, query: str) -> dict[str, int]:
        """Deletes memories matching semantic text query."""
        logger.info(f"Selective Forget: purging files matching query '{query}'")
        
        # 1. Search vector DB for matching document nodes
        matches = self.semantic_index.search(query, top_k=20)
        deleted_docs = 0
        deleted_nodes = 0

        for item in matches:
            if item.get("relevance", 0.0) > 0.0:
                doc_id = item["id"]
                # Remove document from vector DB
                if self.semantic_index.remove_document(doc_id):
                    deleted_docs += 1
                # Remove node from KnowledgeGraph
                if self.kg.remove_node(doc_id):
                    deleted_nodes += 1

        # Also search raw long-term dictionary keys matching query
        for k in list(self.memory.long_term_mem.keys()):
            if query.lower() in k.lower() or query.lower() in str(self.memory.long_term_mem[k]).lower():
                del self.memory.long_term_mem[k]
                deleted_nodes += 1
                self.kg.remove_node(f"lt:{k}")
                self.semantic_index.remove_document(f"lt:{k}")

        self.memory.save_all_layers()
        
        return {
            "deleted_documents": deleted_docs,
            "deleted_graph_nodes": deleted_nodes
        }

    def verify_project_isolation(self, target_project_id: str, caller_project_id: str) -> bool:
        """Prevents data leaks across workspaces."""
        if not target_project_id or not caller_project_id:
            return True
        return target_project_id == caller_project_id

    def check_permissions(self, node_id: str, client_role: str = "USER") -> bool:
        """Verifies access privilege levels before returning search nodes."""
        node = self.kg.get_node(node_id)
        if not node:
            return True
        
        # ACL properties check
        required_role = node.get("properties", {}).get("acl_permission", "USER")
        
        # Roles hierarchy check
        roles_hierarchy = {"GUEST": 0, "USER": 1, "ADMIN": 2}
        client_rank = roles_hierarchy.get(client_role, 1)
        required_rank = roles_hierarchy.get(required_role, 1)
        
        return client_rank >= required_rank

    def memory_cleanup(self) -> None:
        """Cleans temporary caches and expired session variables."""
        logger.info("Executing Memory Cleanup sweeps...")
        self.memory.session_mem.clear()
        self.memory.working_mem.clear()
        logger.info("Cleaned session memory layers.")

    def clear(self) -> None:
        """Reset state."""
        self.tool_frequencies.clear()
        self.model_frequencies.clear()
        self.language_frequencies.clear()
        self.project_frequencies.clear()
        self.memory.clear()
