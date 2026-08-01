"""Unit and integration tests for JARVIS Knowledge Graph & Long-Term Memory Engine."""

import os
import shutil
import time
import unittest

from context_builder import ContextBuilder
from knowledge_graph import ProductionKnowledgeGraph
from memory_engine import MemoryEngine
from memory_manager import MemoryManager
from semantic_search import SemanticSearchEngine


class TestProductionMemory(unittest.TestCase):
    def setUp(self) -> None:
        self.data_root = os.path.abspath("logs/test_production_memory")
        os.makedirs(self.data_root, exist_ok=True)

        # Re-initialize clean test singletons
        self.kg = ProductionKnowledgeGraph(os.path.join(self.data_root, "knowledge_graph.json"))
        self.kg.clear()

        self.semantic_index = SemanticSearchEngine(os.path.join(self.data_root, "semantic_index.json"))
        self.semantic_index.clear()

        self.engine = MemoryEngine(self.data_root)
        self.engine.clear()

        # Connect clean singletons to manager and builder
        self.manager = MemoryManager()
        self.manager.kg = self.kg
        self.manager.semantic_index = self.semantic_index
        self.manager.memory = self.engine

        self.builder = ContextBuilder()
        self.builder.kg = self.kg
        self.builder.semantic_index = self.semantic_index
        self.builder.memory = self.engine

    def tearDown(self) -> None:
        self.engine.clear()
        if os.path.exists(self.data_root):
            try:
                shutil.rmtree(self.data_root)
            except Exception:
                pass

    def test_knowledge_graph_operations(self) -> None:
        """Verify node addition, BFS shortest path traversal, and cascade edge removals."""
        # 1. Add nodes
        self.kg.add_node("user_1", "USER", "Alice")
        self.kg.add_node("proj_A", "PROJECT", "Neural Network API")
        self.kg.add_node("file_X", "FILE", "train.py")
        self.kg.add_node("tool_Y", "TOOL", "compile_tool")

        # 2. Add edges
        self.kg.add_edge("user_1", "proj_A", "CREATED")
        self.kg.add_edge("proj_A", "file_X", "REFERENCES")
        self.kg.add_edge("file_X", "tool_Y", "USES")

        # Verify adjacency nodes
        related = self.kg.get_related_nodes("file_X")
        self.assertEqual(len(related), 2)  # proj_A (incoming) and tool_Y (outgoing)

        # 3. BFS Shortest Path: user_1 -> proj_A -> file_X -> tool_Y (length 4 nodes)
        path = self.kg.get_shortest_path("user_1", "tool_Y")
        self.assertEqual(path, ["user_1", "proj_A", "file_X", "tool_Y"])

        # Path between unconnected nodes returns None
        self.kg.add_node("isolated_node", "USER", "Isolated")
        self.assertIsNone(self.kg.get_shortest_path("user_1", "isolated_node"))

        # 4. Remove node cascades
        self.kg.remove_node("file_X")
        self.assertIsNone(self.kg.get_node("file_X"))
        # Edges incident on file_X should be deleted
        self.assertEqual(len(self.kg.edges), 1)  # only user_1 -> proj_A remains

    def test_semantic_search_and_decay_ranking(self) -> None:
        """Verify vector similarity matching with exponential time decay and KG connectivity weight."""
        # 1. Add identical text snippets at different timestamps to isolate recency decay
        now = time.time()

        # doc_new is brand new
        self.semantic_index.add_document("doc_new", "neural network training details", timestamp=now)
        # doc_old is 2 days old
        self.semantic_index.add_document("doc_old", "neural network training details", timestamp=now - 172800.0)

        results = self.semantic_index.search("neural network training")
        self.assertEqual(results[0]["id"], "doc_new")
        self.assertGreater(results[0]["score"], results[1]["score"])

        # 2. Verify relationship strength booster
        # doc_connected is 2 days old but has multiple connections in KnowledgeGraph
        self.semantic_index.add_document("doc_connected", "neural network training details", timestamp=now - 172800.0)
        self.kg.add_node("doc_connected", "DOCUMENT", "Doc Node")
        self.kg.add_node("hub_node", "USER", "Hub User")
        self.kg.add_node("file_node", "FILE", "File Node")
        self.kg.add_edge("hub_node", "doc_connected", "REFERENCES")
        self.kg.add_edge("file_node", "doc_connected", "USES")

        # Now, doc_connected should score higher than doc_old because of relationship connectivity strength
        results_with_graph = self.semantic_index.search("neural network training")

        scores_by_id = {r["id"]: r["score"] for r in results_with_graph}
        self.assertGreater(scores_by_id["doc_connected"], scores_by_id["doc_old"])

    def test_memory_engine_lifecycle_and_compression(self) -> None:
        """Verify multi-layer reading/writing and automatic conversation log compression."""
        # Write to Session and Project scopes
        self.engine.write_memory("session", "key_a", "val_1")
        self.engine.write_memory("project", "main_language", "Python", project_id="neural_net")

        self.assertEqual(self.engine.read_memory("session", "key_a"), "val_1")
        self.assertEqual(self.engine.read_memory("project", "main_language", project_id="neural_net"), "Python")

        # Fill conversation list to trigger compression (>10 logs)
        for i in range(12):
            self.engine.write_memory("conversation", f"query_{i}", f"answer_{i}")

        self.assertEqual(len(self.engine.conversation_mem), 12)

        # Trigger manual compression
        stats = self.engine.compress_memory()
        self.assertEqual(stats["summarized_conversations"], 7)
        self.assertEqual(len(self.engine.conversation_mem), 5)  # last 5 retained

        # Verify summary node was pushed into long-term memory
        summaries = [k for k in self.engine.long_term_mem.keys() if k.startswith("summary_")]
        self.assertEqual(len(summaries), 1)

    def test_backup_restore_and_corruption_detection(self) -> None:
        """Verify memory export packing, corruption validation checks, and data restoration."""
        self.engine.write_memory("long_term", "user_preferences", "dark_mode")
        self.kg.add_node("test_node", "USER", "Backup node")

        # Create zip backup
        zip_path = os.path.join(self.data_root, "backups/memory_backup.zip")
        success_backup = self.engine.create_backup(zip_path)
        self.assertTrue(success_backup)
        self.assertTrue(os.path.exists(zip_path))

        # Erase active database
        self.engine.clear()
        self.assertEqual(len(self.engine.long_term_mem), 0)
        self.assertEqual(len(self.kg.nodes), 0)

        # Restore from backup
        success_restore = self.engine.restore_backup(zip_path)
        self.assertTrue(success_restore)

        # Verify content
        self.assertEqual(self.engine.read_memory("long_term", "user_preferences"), "dark_mode")
        self.assertIsNotNone(self.kg.get_node("test_node"))

        # Corruption check validation
        # Create corrupted edge (pointing to non-existent target)
        self.kg.edges.append({"source": "test_node", "target": "non_existent", "relation": "DEPENDS_ON", "properties": {}})
        self.kg.save()

        is_clean_init = self.engine.corruption_detection()
        self.assertFalse(is_clean_init)  # repairs occurred

        # Corrupted edge should be pruned
        is_clean_post = self.engine.corruption_detection()
        self.assertTrue(is_clean_post)  # databases are clean now

    def test_context_builder_prompts(self) -> None:
        """Verify prompt assembler compiles markdown inputs matching preferences and histories."""
        self.engine.write_memory("long_term", "preferred_language", "Go")
        self.engine.write_memory("long_term", "preferred_model", "Claude 3.5 Sonnet")
        self.engine.write_memory("conversation", "search neural network", "neural network training")

        context = self.builder.build_context("neural network")
        self.assertIn("Go", context)
        self.assertIn("Claude 3.5 Sonnet", context)
        self.assertIn("search neural network", context)

    def test_memory_manager_selective_forget_and_privacy(self) -> None:
        """Verify memory manager governance, selective forget sweeps, and project bounds."""
        # Add values
        self.engine.write_memory("long_term", "secret_passcode", "12345")
        self.engine.write_memory("long_term", "favorite_color", "blue")

        self.semantic_index.add_document("doc_passcode", "the secret passcode is 12345", metadata={"layer": "long_term"})
        self.kg.add_node("doc_passcode", "DOCUMENT", "Secret code node")

        # Selective Forget on 'passcode'
        forget_stats = self.manager.selective_forget("passcode")
        self.assertEqual(forget_stats["deleted_documents"], 1)

        # Passcode should be deleted, blue should be retained
        self.assertIsNone(self.engine.read_memory("long_term", "secret_passcode"))
        self.assertEqual(self.engine.read_memory("long_term", "favorite_color"), "blue")
        self.assertIsNone(self.kg.get_node("doc_passcode"))

        # Project boundary verification
        self.assertTrue(self.manager.verify_project_isolation("project_1", "project_1"))
        self.assertFalse(self.manager.verify_project_isolation("project_1", "project_2"))


if __name__ == "__main__":
    unittest.main()
