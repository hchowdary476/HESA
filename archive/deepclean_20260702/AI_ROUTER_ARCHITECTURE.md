# AI Router Architecture - Multi-AI Intelligence Platform

## 1. System Overview
The JARVIS AI Router Engine serves as a unified intelligence gateway, orchestrating connections to multiple cloud LLM providers (OpenAI, Google Gemini, Anthropic Claude, xAI Grok, DeepSeek) and local fallback engines (Ollama).

```
          [ JARVIS Command Entry / Voice / GUI Input ]
                               ↓
                   [ Local Intent Router ]
                     /                 \
        (Local Action Match)     (No Match: AI Query)
                   /                     \
      [ Execute Actions ]          [ AI Router Engine ]
                                     /      |       \
                             [ Router ] [ Cache ] [ Cryptography ]
                                    /       |       \
                         [ Providers ]  [ Debate ] [ Failover ]
```

## 2. Core Engine Components
The system is implemented as an async, non-blocking engine:

- **AI Selector:** Inspects query semantics (e.g. keywords, length) and picks the preferred model based on the routing strategy.
- **Failover Handler:** Catches API timeouts/errors and dynamically falls back down the provider priority list.
- **Debate Coordinator:** Dispatches parallel requests to ChatGPT, Gemini, and Claude, compares their responses, scores them, and merges them into a unified answer.
- **Response Cache:** In-memory key-value cache (with SHA-256 keys and expiration) to skip redundant external requests.
- **Portability & Local Fallback:** Automatically switches to Ollama (running Qwen/Llama/Mistral) if offline or internet connectivity fails.

## 3. QML Integration
Two new UI widgets will be exposed through `JarvisBridge` properties:
- **AI Status Panel:** Shows the active model, response latency, status (Online/Offline), and estimated token costs.
- **Multi-AI Comparison Window:** Dynamically renders parallel debate outputs alongside the final unified answer.
