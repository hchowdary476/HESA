# JARVIS AI OS 3.0 - Developer SDK Documentation

Welcome to the JARVIS AI OS 3.0 Development SDK. This SDK enables developers to expand JARVIS by writing custom agents, registering new automation tools, and plugging into the core Cognitive Database and Event Bus.

---

## 1. Creating a Custom Agent

To write a custom agent, inherit from `BaseAgent` in `JARVIS.sdk.base_agent` and override the `run_task` method.

### Example:

```python
from JARVIS.sdk.base_agent import BaseAgent

class CustomWeatherAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Weather Agent", model="Ollama-Qwen2")
        
    def run_task(self, prompt: str) -> str:
        # Custom logic or external API calls
        if "london" in prompt.lower():
            return "Sir, London weather is currently 15°C with light rain."
        return "Sir, weather is clear and optimal in your area."
```

---

## 2. Registering a Custom Tool

Use `BaseTool` in `JARVIS.sdk.base_tool` to encapsulate automation tasks.

### Example:

```python
from JARVIS.sdk.base_tool import BaseTool

def adjust_hue_light(prompt):
    # Code to communicate with Hue bridge
    return "Sir, lighting hue has been set to warm amber."

hue_tool = BaseTool(
    name="Hue Light Toggle",
    description="Adjusts local home environment lighting",
    func=adjust_hue_light
)
```

---

## 3. Registering with Agent Manager

Once custom agents/tools are defined, register them inside the `AgentManager` setup function so they are automatically routed:

```python
from JARVIS.core.ai_router.multi_agent_system import AgentManager
agent_mgr = AgentManager()

# Add to active routing pools
custom_agent = CustomWeatherAgent()
agent_mgr.agents["custom_weather"] = custom_agent
custom_agent.run_loop()
```
