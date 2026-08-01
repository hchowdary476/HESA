"""High-dimensional Semantic Search Engine using composite TF-IDF and decay ranking."""

from __future__ import annotations
import os
import json
import math
import re
import time
import logging
import numpy as np
from typing import Any

from knowledge_graph import ProductionKnowledgeGraph

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("memory.semantic_search")


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
            self.idf[term] = math.log((1 + self.doc_count) / (1 + occurrences)) + 1

    def transform(self, text: str) -> np.ndarray:
        """Transforms a string into a normalized TF-IDF vector."""
        vector = np.zeros(len(self.vocab))
        if len(self.vocab) == 0:
            return vector

        tokens = self.tokenize(text)
        if not tokens:
            return vector

        tf: dict[str, int] = {}
        for token in tokens:
            if token in self.vocab:
                tf[token] = tf.get(token, 0) + 1

        for term, freq in tf.items():
            vocab_idx = self.vocab[term]
            term_tf = freq / len(tokens)
            term_idf = self.idf.get(term, 1.0)
            vector[vocab_idx] = term_tf * term_idf

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return vector


class SemanticSearchEngine:
    """Provides semantic vector space similarity search with composite scoring."""

    _instance: SemanticSearchEngine | None = None

    def __new__(cls, *args, **kwargs) -> SemanticSearchEngine:
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path: str = "logs/production_memory/semantic_index.json") -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.db_path = os.path.abspath(db_path)
        self.documents: list[dict[str, Any]] = []  # list of {id, content, timestamp, metadata}
        self.vectorizer = SimpleVectorizer()
        self.vectors: list[np.ndarray] = []
        self.kg = ProductionKnowledgeGraph()
        self.load()

    def load(self) -> None:
        """Load vector documents indexing data."""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    self.documents = json.load(f)
                self._rebuild_index()
                logger.info(f"Loaded semantic index: {len(self.documents)} documents.")
            except Exception as e:
                logger.error(f"Failed to load semantic index: {e}")
                self.documents = []
        else:
            self.documents = []

    def save(self) -> None:
        """Saves current index structure to local database path."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(self.documents, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save semantic index: {e}")

    def add_document(self, doc_id: str, content: str, timestamp: float | None = None, metadata: dict | None = None) -> None:
        """Indexes or updates a document for vector matching."""
        doc = {
            "id": doc_id,
            "content": content,
            "timestamp": timestamp or time.time(),
            "metadata": metadata or {}
        }
        # Keep list unique on id
        self.documents = [d for d in self.documents if d["id"] != doc_id]
        self.documents.append(doc)
        self._rebuild_index()
        self.save()

    def remove_document(self, doc_id: str) -> bool:
        """Deletes a document from the search indexing structure."""
        initial_len = len(self.documents)
        self.documents = [d for d in self.documents if d["id"] != doc_id]
        if len(self.documents) < initial_len:
            self._rebuild_index()
            self.save()
            return True
        return False

    def _rebuild_index(self) -> None:
        """Re-fits vocabulary and calculates TF-IDF vectors for active documents."""
        corpus = [doc["content"] for doc in self.documents]
        self.vectorizer.fit(corpus)
        self.vectors = [self.vectorizer.transform(doc["content"]) for doc in self.documents]

    def search(self, query: str, top_k: int = 5, project_id: str | None = None) -> list[dict[str, Any]]:
        """Performs a multi-factor ranking search over the indexed corpus."""
        if not self.documents or not self.vectorizer.vocab:
            return []

        query_vector = self.vectorizer.transform(query)
        now = time.time()
        scored_results = []

        for idx, doc in enumerate(self.documents):
            # Check project isolation boundary if project_id is provided
            doc_project = doc["metadata"].get("project_id")
            if project_id and doc_project and doc_project != project_id:
                continue

            # 1. Relevance: Cosine Similarity
            relevance = float(np.dot(query_vector, self.vectors[idx]))

            # 2. Recency: Exponential decay
            doc_ts = doc.get("timestamp", now)
            # Decay rate chosen: half-life is around 38 hours with 5e-6 lambda
            time_diff = max(0.0, now - doc_ts)
            recency = math.exp(-0.000005 * time_diff)

            # 3. Relationship Strength: Connection counts in KnowledgeGraph
            edge_count = 0
            if self.kg:
                try:
                    edge_count = len(self.kg.get_related_nodes(doc["id"]))
                except Exception:
                    pass
            # Normalized log-bounded connectivity metric
            relationship_strength = min(edge_count / 10.0, 1.0)

            # 4. Composite Scoring: 50% relevance, 25% recency, 25% relationships
            composite_score = (relevance * 0.5) + (recency * 0.25) + (relationship_strength * 0.25)

            scored_results.append({
                "id": doc["id"],
                "content": doc["content"],
                "metadata": doc["metadata"],
                "score": composite_score,
                "relevance": relevance,
                "recency": recency,
                "relationship_strength": relationship_strength,
                "timestamp": doc_ts
            })

        # Sort descending by score
        scored_results.sort(key=lambda x: x["score"], reverse=True)
        return scored_results[:top_k]

    def clear(self) -> None:
        """Clear memory cache."""
        self.documents.clear()
        self.vectors.clear()
        self.vectorizer = SimpleVectorizer()
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass
