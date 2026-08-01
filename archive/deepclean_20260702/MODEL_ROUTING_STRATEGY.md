# Model Routing Strategy

## 1. Classification & Routing Map
The AI Router classifies incoming user commands into distinct categories and directs them to the optimal model configuration:

| Query Type | Preferred Model | Fallback Model | Rationale |
| :--- | :--- | :--- | :--- |
| **Coding** | ChatGPT / Claude | Gemini | High reasoning capabilities and syntax generation. |
| **Cyber Security** | ChatGPT / Claude | Gemini / Ollama | Deep contextual cybersecurity training profiles. |
| **Research** | ChatGPT / Gemini | Claude | Multi-source context retrieval and reasoning. |
| **Latest News** | Grok | ChatGPT / Gemini | Real-time web-crawling capabilities. |
| **Long Documents**| Gemini | Claude | 2M+ token context window. |
| **Offline Mode** | Ollama Local | None | Runs locally (Qwen/Llama/Mistral) without internet. |

## 2. Multi-AI Debate Mode
When a user asks for a comprehensive comparison (e.g. *"Jarvis, compare all AIs"* or during high-importance research), **Multi-AI Debate Mode** is triggered:

1. **Parallel Execution:** Dispatches the query concurrently to ChatGPT, Gemini, and Claude.
2. **Analysis & Score:** Enforces a self-correcting prompt template where the router evaluates each answer based on accuracy, conciseness, and depth.
3. **Merging:** Compiles key points from all three into a single, unified JARVIS response.
4. **GUI Display:** Renders each individual response alongside the unified answer in the Comparison Window.

## 3. Cyber Security / Intelligence Integration
- **SOC / Analysis Queries:** Routed to ChatGPT for parsing and format structuring.
- **Malware Analysis / MITRE Mapping:** Routed to Claude for highly detailed code and threat actor alignment.
- **Vulnerability / CVE Research:** Routed to Gemini for extensive database references.
