"""Context Builder automatically compiling prompts with relevant federated memory snippets."""

from __future__ import annotations
import logging
from typing import Any

from knowledge_graph import ProductionKnowledgeGraph
from semantic_search import SemanticSearchEngine
from memory_engine import MemoryEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("memory.context_builder")


class ContextBuilder:
    """Builds highly focused, relevant prompt context blocks from multiple memory scopes."""

    _instance: ContextBuilder | None = None

    def __new__(cls, *args, **kwargs) -> ContextBuilder:
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

    def build_context(self, user_query: str, project_id: str | None = None, limit_chars: int = 3000) -> str:
        """Assembles unified memory block context for AI orchestrator prompt execution."""
        logger.info(f"Assembling context parameters for query: '{user_query}'")
        
        context_parts: list[str] = []
        char_count = 0

        # ── 1. USER LEARNING & PREFERENCES ──
        # Fetch learnings from memory engine
        user_lang = self.memory.read_memory("long_term", "preferred_language")
        user_model = self.memory.read_memory("long_term", "preferred_model")
        pref_block = "User Preferences:\n"
        if user_lang:
            pref_block += f"- Preferred Language: {user_lang}\n"
        if user_model:
            pref_block += f"- Preferred AI Model: {user_model}\n"
        
        if user_lang or user_model:
            context_parts.append(pref_block)
            char_count += len(pref_block)

        # ── 2. PROJECT MEMORY SCOPE ──
        if project_id:
            proj_data = self.memory.read_memory("project", "metadata", project_id=project_id)
            if proj_data:
                proj_block = f"Project Context [{project_id}]:\n"
                for k, v in proj_data.items():
                    proj_block += f"- {k}: {v}\n"
                context_parts.append(proj_block)
                char_count += len(proj_block)

        # ── 3. SEMANTIC VECTOR MATCHES ──
        semantic_matches = self.semantic_index.search(user_query, top_k=3, project_id=project_id)
        if semantic_matches:
            vector_block = "Relevant Synaptic Memories:\n"
            for item in semantic_matches:
                snippet = f"- [{item['metadata'].get('layer', 'general')}]: {item['content']} (confidence: {item['score']:.2f})\n"
                if char_count + len(snippet) < limit_chars:
                    vector_block += snippet
                    char_count += len(snippet)
                else:
                    break
            context_parts.append(vector_block)

        # ── 4. KNOWLEDGE GRAPH RELEVANT ENTITIES ──
        if self.kg:
            nodes = self.kg.find_subgraph()["nodes"]
            graph_block = ""
            graph_matched = 0
            for nid, node in nodes.items():
                # Perform basic query mapping keyword search
                if user_query.lower() in node["label"].lower() or user_query.lower() in node["type"].lower():
                    snippet = f"- Node [{node['type']}] {node['label']} Details: {node['properties']}\n"
                    if char_count + len(snippet) < limit_chars:
                        if not graph_block:
                            graph_block = "Connected Graph Entities:\n"
                        graph_block += snippet
                        char_count += len(snippet)
                        graph_matched += 1
                        if graph_matched >= 3:
                            break
            if graph_block:
                context_parts.append(graph_block)

        # ── 5. RECENT CONVERSATIONS HISTORY ──
        recent_convs = self.memory.conversation_mem[-3:]
        if recent_convs:
            conv_block = "Recent Conversation Context:\n"
            for item in recent_convs:
                snippet = f"- {item['key']}: {item['value']}\n"
                if char_count + len(snippet) < limit_chars:
                    conv_block += snippet
                    char_count += len(snippet)
            context_parts.append(conv_block)

        # Combine items
        assembled = "\n".join(context_parts)
        if len(assembled) > limit_chars:
            assembled = assembled[:limit_chars] + "\n[Context Truncated]"
        return assembled
