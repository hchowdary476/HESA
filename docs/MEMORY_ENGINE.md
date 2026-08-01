# 💾 HESA Distributed Memory Engine

HESA features a multi-tiered memory architecture designed to retain context across sessions while respecting user privacy.

---

## 🏗️ Memory Layers

```
┌─────────────────────────────────────────────────────────┐
│ Layer 1: Working Memory (JSON / In-Memory RAM Cache)    │
│ - Short-term turn-by-turn conversation context          │
├─────────────────────────────────────────────────────────┤
│ Layer 2: Long-Term Store (SQLite 3 Database)            │
│ - Key-value user preferences, notes, and habits         │
├─────────────────────────────────────────────────────────┤
│ Layer 3: Knowledge Graph & Semantic Search Index        │
│ - TF-IDF / Keyword semantic node graph relationship map │
└─────────────────────────────────────────────────────────┘
```

---

## 🔧 Component Details

### 1. Working Memory (`memory_short_term.py`)
- Holds active conversation turn context up to a configurable history buffer (default: 10 turns).
- Flushed on system restart or when requested via `"clear working memory"`.

### 2. Persistent Store (`memory_store.py` / `memory.json`)
- Uses SQLite 3 (`memory.db`) or localized JSON storage for persistent key-value access.
- Supports scoped data namespaces: `user_preferences`, `system_habits`, `saved_notes`.

### 3. Knowledge Graph (`knowledge_graph.py` & `semantic_search.py`)
- Maps relationships between entities (e.g. `User --PREFERS--> Python`).
- Provides TF-IDF indexed document search for retrieving relevant context when building prompts.

---

## 🔒 Privacy Controls

- All memory stores reside locally on your disk under `logs/production_memory/` or `memory.json`.
- Enable Privacy Mode (`JARVIS_PRIVACY_MODE=true`) to prevent memory context from being sent to external Cloud LLM endpoints.
- Execute `"purge memory"` via voice or dashboard to scrub stored notes and indexes.
