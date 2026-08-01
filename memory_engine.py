"""Multi-Layer Memory Engine coordinating persistence, backups, and compression."""

from __future__ import annotations
import os
import json
import time
import zipfile
import shutil
import logging
from typing import Any

from knowledge_graph import ProductionKnowledgeGraph
from semantic_search import SemanticSearchEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("memory.engine")


class MemoryEngine:
    """Central Synaptic Router coordinating session, persistent, and graph memories."""

    _instance: MemoryEngine | None = None

    def __new__(cls, *args, **kwargs) -> MemoryEngine:
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, data_root: str = "logs/production_memory") -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.data_root = os.path.abspath(data_root)
        os.makedirs(self.data_root, exist_ok=True)

        # Connect graph and vector engines
        self.kg = ProductionKnowledgeGraph(os.path.join(self.data_root, "knowledge_graph.json"))
        self.semantic_index = SemanticSearchEngine(os.path.join(self.data_root, "semantic_index.json"))

        # RAM Layers
        self.session_mem: dict[str, Any] = {}
        self.working_mem: dict[str, Any] = {}

        # Persistence layers maps
        self.long_term_mem: dict[str, Any] = {}
        self.project_mem: dict[str, dict[str, Any]] = {}  # project_id -> metadata
        self.procedural_mem: dict[str, Any] = {}
        self.conversation_mem: list[dict[str, Any]] = []  # list of conversation items

        self.load_all_layers()

    def load_all_layers(self) -> None:
        """Loads all persistent memory layers from filesystem JSONs."""
        self.long_term_mem = self._load_file("long_term.json", {})
        self.project_mem = self._load_file("project.json", {})
        self.procedural_mem = self._load_file("procedural.json", {})
        self.conversation_mem = self._load_file("conversation.json", [])

    def save_all_layers(self) -> None:
        """Saves all persistent memory layers to filesystem JSONs."""
        self._save_file("long_term.json", self.long_term_mem)
        self._save_file("project.json", self.project_mem)
        self._save_file("procedural.json", self.procedural_mem)
        self._save_file("conversation.json", self.conversation_mem)

    def _load_file(self, filename: str, default: Any) -> Any:
        path = os.path.join(self.data_root, filename)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading memory file {filename}: {e}")
        return default

    def _save_file(self, filename: str, data: Any) -> None:
        path = os.path.join(self.data_root, filename)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving memory file {filename}: {e}")

    def write_memory(self, layer: str, key: str, value: Any, project_id: str | None = None) -> bool:
        """Saves values into a specific memory layer and updates indices."""
        layer_lower = layer.lower()
        now = time.time()

        if layer_lower == "session":
            self.session_mem[key] = value
        elif layer_lower == "working":
            self.working_mem[key] = value
        elif layer_lower == "long_term":
            self.long_term_mem[key] = value
            # Write entity node and semantic index
            self.kg.add_node(f"lt:{key}", "DOCUMENT", f"Long term: {key}", {"value": str(value)})
            self.semantic_index.add_document(
                doc_id=f"lt:{key}",
                content=f"Long term memory value of {key} is {str(value)}",
                timestamp=now,
                metadata={"layer": "long_term", "key": key}
            )
            self.save_all_layers()
        elif layer_lower == "project":
            proj_id = project_id or "default_project"
            if proj_id not in self.project_mem:
                self.project_mem[proj_id] = {}
            self.project_mem[proj_id][key] = value
            
            # Write project node and project relation
            self.kg.add_node(proj_id, "PROJECT", f"Project: {proj_id}")
            self.kg.add_node(f"proj:{proj_id}:{key}", "DOCUMENT", f"Project config: {key}", {"value": str(value)})
            self.kg.add_edge(proj_id, f"proj:{proj_id}:{key}", "REFERENCES")
            
            self.semantic_index.add_document(
                doc_id=f"proj:{proj_id}:{key}",
                content=f"Project {proj_id} configuration for {key} is {str(value)}",
                timestamp=now,
                metadata={"layer": "project", "project_id": proj_id, "key": key}
            )
            self.save_all_layers()
        elif layer_lower == "procedural":
            self.procedural_mem[key] = value
            self.save_all_layers()
        elif layer_lower == "conversation":
            # Add to conversation log list
            log_item = {
                "key": key,
                "value": value,
                "timestamp": now,
                "project_id": project_id
            }
            self.conversation_mem.append(log_item)
            
            # Write conversation node and index
            conv_node_id = f"conv:{int(now)}"
            self.kg.add_node(conv_node_id, "CONVERSATION", f"Log: {key}", {"text": str(value)})
            self.semantic_index.add_document(
                doc_id=conv_node_id,
                content=f"Conversation log: {key} - {str(value)}",
                timestamp=now,
                metadata={"layer": "conversation", "project_id": project_id, "conversation_key": key}
            )
            self.save_all_layers()
        else:
            logger.error(f"Memory layer '{layer}' not recognized.")
            return False

        # Integrate and propagate to Phase VI distributed memory manager if available
        try:
            from distributed_memory import DistributedMemory
            DistributedMemory().write_memory(layer, key, value)
        except Exception:
            pass

        return True

    def read_memory(self, layer: str, key: str, project_id: str | None = None) -> Any:
        """Retrieves a memory value from the designated layer."""
        layer_lower = layer.lower()
        if layer_lower == "session":
            return self.session_mem.get(key)
        elif layer_lower == "working":
            return self.working_mem.get(key)
        elif layer_lower == "long_term":
            return self.long_term_mem.get(key)
        elif layer_lower == "project":
            proj_id = project_id or "default_project"
            return self.project_mem.get(proj_id, {}).get(key)
        elif layer_lower == "procedural":
            return self.procedural_mem.get(key)
        elif layer_lower == "conversation":
            for log in reversed(self.conversation_mem):
                if log["key"] == key:
                    return log["value"]
            return None
        return None

    def compress_memory(self) -> dict[str, Any]:
        """Runs optimization sweeps: summarizing conversations, archiving old projects."""
        logger.info("Executing Memory Compression optimization sweeps...")
        summary_count = 0
        archive_count = 0
        now = time.time()

        # 1. Compress/Summarize conversation history if it gets too large (>10 logs)
        if len(self.conversation_mem) > 10:
            old_logs = self.conversation_mem[:-5]
            recent_logs = self.conversation_mem[-5:]
            
            # Combine old logs text
            combined_text = " | ".join([f"{item['key']}: {item['value']}" for item in old_logs])
            summary_key = f"summary_{int(now)}"
            summary_value = f"Compressed summary of older dialogues: {combined_text[:300]}..."
            
            # Write to long-term memory
            self.write_memory("long_term", summary_key, summary_value)
            
            # Remove old logs nodes from vector index
            for item in old_logs:
                # Remove from vector db
                conv_ts_node = f"conv:{int(item['timestamp'])}"
                self.semantic_index.remove_document(conv_ts_node)
                # Remove from KG
                self.kg.remove_node(conv_ts_node)
                
            self.conversation_mem = recent_logs
            summary_count = len(old_logs)
            logger.info(f"Summarized and compressed {summary_count} older conversation records.")

        # 2. Archive projects inactive for > 7 days (or simulated 10 seconds for test runs)
        for proj_id, metadata in list(self.project_mem.items()):
            last_activity = metadata.get("last_activity_ts", now)
            # Simulated archive boundary (7 days = 604800s, but let's check archived property)
            if now - last_activity > 604800.0:
                if metadata.get("status") != "ARCHIVED":
                    metadata["status"] = "ARCHIVED"
                    self.kg.add_node(proj_id, "PROJECT", f"Project: {proj_id}", {"status": "ARCHIVED"})
                    archive_count += 1
                    logger.info(f"Archived inactive project: '{proj_id}'")

        self.save_all_layers()
        return {
            "summarized_conversations": summary_count,
            "archived_projects": archive_count
        }

    def create_backup(self, backup_zip_path: str) -> bool:
        """Packs database JSON files into an archive zip backup."""
        logger.info(f"Creating memory database backup: {backup_zip_path}")
        os.makedirs(os.path.dirname(os.path.abspath(backup_zip_path)), exist_ok=True)
        
        # Save current state first
        self.save_all_layers()
        self.kg.save()
        self.semantic_index.save()

        try:
            with zipfile.ZipFile(backup_zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for file_name in os.listdir(self.data_root):
                    if file_name.endswith(".json"):
                        file_path = os.path.join(self.data_root, file_name)
                        zip_file.write(file_path, file_name)
            return True
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return False

    def restore_backup(self, backup_zip_path: str) -> bool:
        """Unpacks backup database files and recovers memory states."""
        logger.info(f"Restoring memory databases from backup: {backup_zip_path}")
        if not os.path.exists(backup_zip_path):
            logger.error("Backup archive path does not exist.")
            return False

        try:
            # Unzip to temp location first to validate files
            temp_dir = os.path.join(self.data_root, "temp_restore")
            os.makedirs(temp_dir, exist_ok=True)
            
            with zipfile.ZipFile(backup_zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # Validate that core files exist
            core_files = ["knowledge_graph.json", "semantic_index.json", "long_term.json", "conversation.json"]
            for f in core_files:
                if not os.path.exists(os.path.join(temp_dir, f)):
                    raise FileNotFoundError(f"Missing core database file in backup: {f}")

            # Overwrite active database files
            for file_name in os.listdir(temp_dir):
                src_path = os.path.join(temp_dir, file_name)
                dest_path = os.path.join(self.data_root, file_name)
                shutil.copy2(src_path, dest_path)

            # Clean up temp
            shutil.rmtree(temp_dir)

            # Re-load memory layers
            self.load_all_layers()
            self.kg.load()
            self.semantic_index.load()
            logger.info("Memory database restore finished successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False

    def corruption_detection(self) -> bool:
        """Validates JSON layouts and cascades cleanups on corrupt indices."""
        logger.info("Running Memory Corruption Detection sweeps...")
        corrupt = False

        # 1. Schema check on persistent files
        files_to_check = ["long_term.json", "project.json", "procedural.json", "conversation.json"]
        for f_name in files_to_check:
            path = os.path.join(self.data_root, f_name)
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        json.load(f)
                except Exception:
                    logger.warning(f"Corrupt JSON format in memory file: {f_name}. Resetting file.")
                    self._save_file(f_name, [] if f_name == "conversation.json" else {})
                    corrupt = True

        # 2. Graph edge integrity check
        graph_corrupt = False
        for edge in list(self.kg.edges):
            # If an edge points to non-existent nodes, remove it
            if edge["source"] not in self.kg.nodes or edge["target"] not in self.kg.nodes:
                self.kg.edges.remove(edge)
                graph_corrupt = True
                
        if graph_corrupt:
            corrupt = True
            self.kg.save()
            logger.warning("Repaired Knowledge Graph edges pointing to missing nodes.")

        return not corrupt

    def clear(self) -> None:
        """Reset state."""
        self.session_mem.clear()
        self.working_mem.clear()
        self.long_term_mem.clear()
        self.project_mem.clear()
        self.procedural_mem.clear()
        self.conversation_mem.clear()
        self.kg.clear()
        self.semantic_index.clear()
        
        # Remove any database files
        if os.path.exists(self.data_root):
            try:
                for entry in os.listdir(self.data_root):
                    path = os.path.join(self.data_root, entry)
                    if os.path.isfile(path):
                        os.remove(path)
            except Exception:
                pass
