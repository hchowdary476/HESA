"""Multi-Agent AI System - Implements specialized agents, task queues, tools, and health monitoring."""

from __future__ import annotations
import queue
import threading
import time
import logging
from typing import Any, Callable
from JARVIS.core.system.utils.jarvis_logging import get_logger

logger = get_logger("multi_agent_system")

class Agent:
    """Specialized AI Agent with isolated state, tools, queue, and model configuration."""

    def __init__(self, name: str, description: str, system_prompt: str, capabilities: list[str], tools: list[Callable], preferred_model: str) -> None:
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
        self.capabilities = capabilities
        self.tools = tools
        self.preferred_model = preferred_model
        self.task_queue: queue.Queue[dict] = queue.Queue()
        self.memory: list[dict] = []
        self.cpu_usage = 0.0
        self.memory_usage = 5.0  # Simulated MBs base
        self.status = "IDLE"  # IDLE, BUSY, OFFLINE
        self.error_count = 0
        self.success_count = 0

    def add_task(self, task_id: str, prompt: str, callback: Callable | None = None) -> None:
        """Enqueue a new task for the agent."""
        self.task_queue.put({
            "id": task_id,
            "prompt": prompt,
            "callback": callback,
            "enqueued_at": time.time()
        })
        logger.info("Enqueued task %s to Agent %s.", task_id, self.name)

    def execute_next_task(self, block: bool = False, timeout: float | None = None) -> dict | None:
        """De-queue and run the next task in the queue."""
        import queue
        if not block and self.task_queue.empty():
            return None

        try:
            task = self.task_queue.get(block=block, timeout=timeout)
        except queue.Empty:
            return None
        self.status = "BUSY"
        self.cpu_usage = 12.5  # Simulate load
        logger.info("Agent %s starting task: %s", self.name, task["prompt"])
        
        start_time = time.time()
        success = True
        result = ""
        
        # Simulate tool execution and RAG lookup
        try:
            # Match prompt to tools
            matched_tool = None
            for tool in self.tools:
                if tool.__name__.lower() in task["prompt"].lower():
                    matched_tool = tool
                    break
            
            if matched_tool:
                result = matched_tool(task["prompt"])
            else:
                # Default query resolution
                result = f"Resolved via {self.preferred_model}: Completed task '{task['prompt']}' successfully."
                
            self.success_count += 1
            # Add to local short-term memory
            self.memory.append({"role": "user", "content": task["prompt"]})
            self.memory.append({"role": "assistant", "content": result})
            if len(self.memory) > 10:
                self.memory.pop(0)
        except Exception as e:
            logger.error("Error running task in Agent %s: %s", self.name, e)
            result = f"Execution error: {e}"
            self.error_count += 1
            success = False

        self.status = "IDLE"
        self.cpu_usage = 0.0
        self.task_queue.task_done()
        
        task_report = {
            "id": task["id"],
            "prompt": task["prompt"],
            "success": success,
            "result": result,
            "elapsed_ms": (time.time() - start_time) * 1000
        }
        
        if task["callback"]:
            try:
                task["callback"](task_report)
            except Exception as e:
                logger.error("Callback failed in Agent %s: %s", self.name, e)

        return task_report

    def get_health(self) -> dict[str, Any]:
        """Return real-time agent health telemetry."""
        total = self.success_count + self.error_count
        rate = (self.success_count / total * 100.0) if total > 0 else 100.0
        queue_len = self.task_queue.qsize()
        est_completion_time = queue_len * 5.0
        return {
            "name": self.name,
            "status": self.status,
            "cpu": self.cpu_usage,
            "ram": self.memory_usage,
            "success_rate": round(rate, 1),
            "pending_tasks": queue_len,
            "errors": self.error_count,
            "capabilities": self.capabilities,
            "preferred_model": self.preferred_model,
            "tools": [t.__name__ for t in self.tools],
            "est_completion_time": est_completion_time
        }


class AgentManager:
    """Orchestrates and routes requests to the 10 Core AI Agents."""

    _instance: AgentManager | None = None

    def __new__(cls, *args, **kwargs) -> AgentManager:
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.agents: dict[str, Agent] = {}
        self._setup_agents()

    def _setup_agents(self) -> None:
        # Mock tools mapping
        def tool_code_gen(p): return "Code generated and verified successfully."
        def tool_search_web(p): return "Search yields 4 relevant documentation links."
        def tool_security_audit(p): return "Cyber logs audit complete: 0 vulnerabilities found."
        def tool_os_cmd(p): return "Application started, window focused."
        def tool_train_ml(p): return "ML model trained. R2 score: 0.94."
        def tool_learn_habits(p): return "User habits analyzed. Suggestions updated."

        agent_configs = [
            ("Coding Agent", "Write code efficiently", "Generate clean code", ["coding", "formatting", "linting", "pytest"], [tool_code_gen], "Claude 3.5 Sonnet"),
            ("Research Agent", "Fetches documentation/papers", "Perform system research", ["research", "literature", "arxiv", "web_search"], [tool_search_web], "Gemini 1.5 Pro"),
            ("AI & ML Agent", "Trains models, dataset indexing", "Run training models", ["train", "dataset", "benchmarks", "sweeps"], [tool_train_ml], "Gemini 1.5 Pro"),
            ("Cyber Security Agent", "Audits connections and CVEs", "Audit logs", ["security", "port_scan", "log_audit", "cve"], [tool_security_audit], "ChatGPT 4o"),
            ("Developer Agent", "Handles build, test and refactor", "Build and compile", ["build", "compile", "refactor", "deploy"], [tool_code_gen], "Claude 3.5 Sonnet"),
            ("Windows System Agent", "Controls registry, services and CLI", "Execute Windows commands", ["system", "shutdown", "restart", "sleep", "lock", "process"], [tool_os_cmd], "Ollama (Llama 3)"),
            ("Automation Agent", "Controls keyboard, mouse, triggers", "Trigger automation scripts", ["keyboard", "mouse", "spotify", "play"], [tool_os_cmd], "LM Studio (Mistral)"),
            ("Memory Agent", "Maintains local context and notes", "Retrieve context from knowledge graph", ["memory", "habit", "routine", "learn", "notes"], [tool_learn_habits], "Ollama (Llama 3)"),
            # Software Engineering Specialized Agents
            ("Architect Agent", "Analyse requirements and select tech stack", "Design software architecture specs", ["architecture", "spec", "design", "requirements"], [tool_code_gen], "Claude 3.5 Sonnet"),
            ("Frontend Agent", "Generates user interface layouts", "Generate React, Next.js, and HTML frontend assets", ["frontend", "ui", "react", "next", "html"], [tool_code_gen], "Claude 3.5 Sonnet"),
            ("Backend Agent", "Generates REST APIs and schemas", "Generate FastAPI, Django, Flask, database schemas, auth modules", ["backend", "api", "fastapi", "flask", "django", "spring"], [tool_code_gen], "Claude 3.5 Sonnet"),
            ("Mobile Agent", "Generates Flutter and Android mobile client code", "Generate mobile flutter widgets, sign configurations, gradle rules", ["mobile", "android", "flutter", "apk"], [tool_code_gen], "Claude 3.5 Sonnet"),
            ("Testing Agent", "Generates test suites and run validations", "Generate pytest unit tests, vitest specs, check coverage", ["testing", "unit_test", "integration_test", "coverage"], [tool_code_gen], "Claude 3.5 Sonnet"),
            ("Debugger Agent", "Analyzes stack traces and compiler/runtime errors", "Debug errors, compile and trace fixes", ["debugger", "debug", "error_fix"], [tool_code_gen], "Claude 3.5 Sonnet"),
            ("Documentation Agent", "Generates README, API docs, and architecture diagrams", "Generate README, API docs, architecture diagrams, deployment files", ["documentation", "readme", "api_docs", "changelog"], [tool_code_gen], "Claude 3.5 Sonnet"),
            ("DevOps Agent", "Generates dockerfiles and ci-cd pipelines", "Generate Docker files, docker-compose orchestration, github actions", ["devops", "docker", "ci_cd", "github_actions"], [tool_code_gen], "Claude 3.5 Sonnet")
        ]

        for name, desc, prompt, capabilities, tools, model in agent_configs:
            key = name.lower().replace(" ", "_").replace("&", "and")
            self.agents[key] = Agent(name, desc, prompt, capabilities, tools, model)

    def get_agent(self, key: str) -> Agent | None:
        """Fetch agent object by key."""
        return self.agents.get(key)

    def route_command(self, command: str) -> str:
        """Identify which agent should handle the user command based on capabilities."""
        cmd = command.lower()
        # 1. Direct match on capabilities
        for key, agent in self.agents.items():
            for cap in agent.capabilities:
                if cap.lower() in cmd:
                    return key
        # 2. Fallback keyword matching
        if any(w in cmd for w in ["code", "script", "refactor", "bug", "write", "py"]):
            return "coding_agent"
        if any(w in cmd for w in ["search", "google", "arxiv", "paper", "documentation", "literature"]):
            return "research_agent"
        if any(w in cmd for w in ["port", "cyber", "security", "threat", "cve", "hack", "firewall"]):
            return "cyber_security_agent"
        if any(w in cmd for w in ["train", "dataset", "tuning", "sweep", "benchmark"]):
            return "ai_and_ml_agent"
        if any(w in cmd for w in ["build", "compile", "refactor", "deploy"]):
            return "developer_agent"
        if any(w in cmd for w in ["shutdown", "restart", "sleep", "lock", "uptime", "ram", "cpu", "registry", "service"]):
            return "windows_system_agent"
        if any(w in cmd for w in ["spotify", "music", "play", "volume", "next", "press", "click"]):
            return "automation_agent"
        if any(w in cmd for w in ["memory", "habit", "routine", "learn", "behavior", "working hour", "note"]):
            return "memory_agent"
        
        return "coding_agent"

    def run_agent_loops(self) -> None:
        """Continuously process enqueued agent tasks on worker loops."""
        def _worker(agent: Agent):
            while True:
                try:
                    agent.execute_next_task(block=True, timeout=1.0)
                except Exception:
                    pass

        for agent in self.agents.values():
            t = threading.Thread(target=_worker, args=(agent,), daemon=True)
            t.start()
            logger.info("Started background execution worker thread for %s.", agent.name)

    def get_agents_telemetry(self) -> list[dict[str, Any]]:
        """Gather health, status, and stats of all core agents."""
        return [agent.get_health() for agent in self.agents.values()]
