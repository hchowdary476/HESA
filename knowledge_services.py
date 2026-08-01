"""Knowledge Services and Semantic Search for the JARVIS AI Operating System."""

from __future__ import annotations
import math
import os
import re
import numpy as np
import threading
import logging
from typing import Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_os.knowledge_services")


class SimpleVectorizer:
    """Lightweight text vectorization using TF-IDF mapping with NumPy calculations."""

    def __init__(self) -> None:
        self.vocab: dict[str, int] = {}
        self.idf: dict[str, float] = {}
        self.doc_count = 0

    def tokenize(self, text: str) -> list[str]:
        """Cleans and tokenizes text."""
        return re.findall(r"\b\w+\b", text.lower())

    def fit(self, documents: list[str]) -> None:
        """Trains vocabulary and IDF weights on document corpus."""
        self.doc_count = len(documents)
        if self.doc_count == 0:
            return

        term_doc_occurrences: dict[str, int] = {}
        vocab_set = set()

        for doc in documents:
            tokens = set(self.tokenize(doc))
            for token in tokens:
                term_doc_occurrences[token] = term_doc_occurrences.get(token, 0) + 1
                vocab_set.add(token)

        self.vocab = {term: idx for idx, term in enumerate(sorted(vocab_set))}
        
        self.idf = {}
        for term, occurrences in term_doc_occurrences.items():
            # Standard smoothed IDF calculation
            self.idf[term] = math.log((1 + self.doc_count) / (1 + occurrences)) + 1

    def transform(self, text: str) -> np.ndarray:
        """Transforms a string into a normalized TF-IDF vector."""
        vector = np.zeros(len(self.vocab))
        if len(self.vocab) == 0:
            return vector

        tokens = self.tokenize(text)
        if not tokens:
            return vector

        # Count frequencies
        tf: dict[str, int] = {}
        for token in tokens:
            if token in self.vocab:
                tf[token] = tf.get(token, 0) + 1

        # Compute TF-IDF
        for term, freq in tf.items():
            vocab_idx = self.vocab[term]
            term_tf = freq / len(tokens)
            term_idf = self.idf.get(term, 1.0)
            vector[vocab_idx] = term_tf * term_idf

        # Normalize vector
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return vector


class KnowledgeServices:
    """Provides semantic search, document embeddings management, and knowledge synchronization."""

    _instance: KnowledgeServices | None = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs) -> KnowledgeServices:
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self, index_dir: str = "knowledge") -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.index_dir = os.path.abspath(index_dir)
        os.makedirs(self.index_dir, exist_ok=True)
        
        self.documents: list[dict[str, Any]] = []
        self.vectorizer = SimpleVectorizer()
        self.vectors: list[np.ndarray] = []
        self.kg = None
        self.lock = threading.Lock()
        
        # Load existing KnowledgeGraph if available
        try:
            from JARVIS.core.memory.knowledge_graph import KnowledgeGraph
            self.kg = KnowledgeGraph()
            logger.info("Knowledge Graph linked to KnowledgeServices.")
        except Exception as e:
            logger.warning(f"Could not link KnowledgeGraph: {e}")

        logger.info("Knowledge Services initialized.")

    def add_document(self, doc_id: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Indexes a text document for vector search."""
        with self.lock:
            doc = {
                "id": doc_id,
                "content": content,
                "metadata": metadata or {}
            }
            # Remove duplicate doc_id
            self.documents = [d for d in self.documents if d["id"] != doc_id]
            self.documents.append(doc)
            self._rebuild_index()
            
        logger.info(f"Indexed document: {doc_id} ({len(content)} chars)")

    def ingest_directory(self, folder_path: str, chunk_size: int = 500) -> int:
        """Parses all text files in a directory and splits them into indexed chunks."""
        count = 0
        if not os.path.exists(folder_path):
            return count

        for entry in os.listdir(folder_path):
            if entry.endswith((".txt", ".md")):
                file_path = os.path.join(folder_path, entry)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        text = f.read()
                    
                    # Split into overlapping chunks
                    words = text.split()
                    chunks = []
                    for i in range(0, len(words), chunk_size - 50):
                        chunk_words = words[i : i + chunk_size]
                        chunks.append(" ".join(chunk_words))
                        if len(chunk_words) < chunk_size:
                            break
                            
                    for idx, chunk in enumerate(chunks):
                        self.add_document(
                            doc_id=f"{entry}_chunk_{idx}",
                            content=chunk,
                            metadata={"source": file_path, "filename": entry, "chunk_index": idx}
                        )
                        count += 1
                except Exception as e:
                    logger.error(f"Failed to ingest file {file_path}: {e}")
        return count

    def semantic_search(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """Executes vector space cosine similarity search on indexed corpus."""
        with self.lock:
            if not self.documents or not self.vocab_size():
                # Perform fallback search via KnowledgeGraph if document index is empty
                if self.kg:
                    try:
                        nodes = self.kg.semantic_search(query)
                        return [{"id": n["id"], "content": n["label"], "score": 0.5, "metadata": n.get("properties", {})} for n in nodes[:top_k]]
                    except Exception:
                        pass
                return []

            query_vector = self.vectorizer.transform(query)
            scores = []
            for idx, doc_vector in enumerate(self.vectors):
                # Cosine Similarity between normalized vectors (dot product)
                sim = float(np.dot(query_vector, doc_vector))
                scores.append((sim, self.documents[idx]))

            # Sort descending by score
            scores.sort(key=lambda x: x[0], reverse=True)
            
            results = []
            for sim, doc in scores[:top_k]:
                # Only return documents with some similarity threshold
                results.append({
                    "id": doc["id"],
                    "content": doc["content"],
                    "metadata": doc["metadata"],
                    "score": sim
                })
            return results

    def get_ranked_context(self, query: str, max_chars: int = 2000) -> str:
        """Combines vector search and knowledge graph nodes into a single prompt context block."""
        results = self.semantic_search(query, top_k=5)
        
        # Pull extra context from Knowledge Graph
        graph_entities = []
        if self.kg:
            try:
                nodes = self.kg.semantic_search(query)
                for n in nodes[:3]:
                    graph_entities.append(f"Entity: {n['label']} (Type: {n.get('type', 'generic')})")
            except Exception:
                pass
                
        context_parts = []
        char_count = 0
        
        if graph_entities:
            context_parts.append("--- Knowledge Graph Facts ---")
            for ent in graph_entities:
                context_parts.append(ent)
                
        context_parts.append("--- Semantic Search Excerpts ---")
        for res in results:
            snippet = f"Source [{res['id']}]: {res['content']}"
            if char_count + len(snippet) > max_chars:
                break
            context_parts.append(snippet)
            char_count += len(snippet)
            
        return "\n".join(context_parts)

    def vocab_size(self) -> int:
        """Returns vocabulary size of semantic indexing engine."""
        return len(self.vectorizer.vocab)

    def _rebuild_index(self) -> None:
        """Rebuilds vocabulary and regenerates document vectors."""
        corpus = [doc["content"] for doc in self.documents]
        self.vectorizer.fit(corpus)
        
        self.vectors = []
        for doc in self.documents:
            self.vectors.append(self.vectorizer.transform(doc["content"]))
            
    def clear(self) -> None:
        """Resets indexes for clean testing runs."""
        with self.lock:
            self.documents.clear()
            self.vectors.clear()
            self.vectorizer = SimpleVectorizer()
