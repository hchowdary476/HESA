# JARVIS Knowledge Graph & Long-Term Memory Engine Architecture (Phase VII)

This document describes the design, storage layout, scoring formula, and integration hooks of the JARVIS Production Memory platform.

---

## 1. Multi-Layer Memory Topology

The Memory Engine structures data across different speeds and lifecycles:

```mermaid
graph TD
    Query[User Query] --> ContextBuilder[Context Builder]

    subgraph RAM Layers (Non-Persistent)
        Session[Session Memory: Temporary request metrics]
        Working[Working Memory: Active task instructions]
    end

    subgraph Persistence Layers (JSON Files)
        LongTerm[Long-Term Memory: User preferences & habits]
        Project[Project Memory: Code descriptions, workspace states]
        Procedural[Procedural Memory: Repeated workflows & templates]
        Conversation[Conversation Memory: Dialog histories & summaries]
    end

    subgraph Synaptic Graph & Vector DB
        KG[ProductionKnowledgeGraph: Entity-Relationship property graph]
        SemanticSearch[SemanticSearchEngine: TF-IDF High-dimensional Vector Space]
    end

    ContextBuilder --> Session
    ContextBuilder --> Working
    ContextBuilder --> LongTerm
    ContextBuilder --> Project
    ContextBuilder --> KG
    ContextBuilder --> SemanticSearch
```

---

## 2. Mathematical Ranking & Scoring Formulations

To find the most relevant context snippets, the `SemanticSearchEngine` uses a composite scoring formula combining conceptual semantics, recency decay, and graph network connectivity:

$$\text{Composite Score} = (S_{\text{relevance}} \times 0.5) + (S_{\text{recency}} \times 0.25) + (S_{\text{relationship}} \times 0.25)$$

### 2.1. Relevance Score ($S_{\text{relevance}}$)
Conceptual relevance is measured by calculating the Cosine Similarity of normalized TF-IDF vectors representing the query $q$ and indexed document $d$:

$$S_{\text{relevance}} = \cos(\theta) = \frac{\vec{q} \cdot \vec{d}}{\|\vec{q}\| \|\vec{d}\|}$$

### 2.2. Recency Score ($S_{\text{recency}}$)
Time-decay represents the concept that older events are less relevant to active conversation focus. It is modeled using an exponential decay function:

$$S_{\text{recency}} = e^{-\lambda \Delta t}$$

- Where $\Delta t = t_{\text{current}} - t_{\text{document}}$ (measured in seconds).
- Where $\lambda = 5 \times 10^{-6}$ (giving a half-life of approximately 38 hours).

### 2.3. Relationship Strength ($S_{\text{relationship}}$)
This metric ranks items that are highly connected inside the Knowledge Graph. It counts the number of incident edges (connectivity degree) for node $n$ corresponding to document $d$:

$$S_{\text{relationship}} = \min\left(\frac{\text{Degree}(n)}{10}, 1.0\right)$$

---

## 3. Core Component Integrations

### 3.1. Cognitive Core Integration
The `CognitiveCore` imports `ContextBuilder` and routes requests as follows:
1. `ContextBuilder.build_context(command)` is triggered.
2. The compiled memory string is prepended as system instructions.
3. The response is processed, and interaction telemetry is sent to `MemoryManager.track_learning_interaction()` to learn user habits (preferred model, programming language, tools).
4. The conversation interaction is recorded to `MemoryEngine.write_memory("conversation", ...)`.

### 3.2. Workflow Engine Integration
When workflows are dispatched, run, or completed:
1. The `WorkflowScheduler` logs nodes and edges to the `ProductionKnowledgeGraph`.
2. Nodes of type `WORKFLOW` and `TOOL` are created, linked by relations like `USES` and `EXECUTED`.

### 3.3. Security & Isolation
- **Project Isolation**: Workspace data remains secure. If queries carry a `project_id` identifier, search matching restricts outcomes to identical project scopes.
- **Selective Forget**: Allows explicit erasure. Entering a query will purge files from both vector indices and property graph mappings.
