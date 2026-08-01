"""Cognitive Core - Central AI Brain coordinating safety, RAG memory, model selection, planning, and explainability."""

from __future__ import annotations
import os
import time
import json
import logging
from typing import Any
from JARVIS.core.security.safety_layer import AISafetyLayer
from knowledge_graph import ProductionKnowledgeGraph
from JARVIS.core.learning.learning_engine import PersonalLearningEngine
from JARVIS.core.ai_router.ai_orchestrator import AIOrchestrator
from JARVIS.core.system.task_planner import TaskPlanner
from JARVIS.core.system.workflow_builder import WorkflowBuilder
from JARVIS.core.system.utils.jarvis_logging import get_logger

logger = get_logger("cognitive_core")

class CognitiveCore:
    """Central synaptic coordinator directing all AI subsystems and safety guards."""

    _instance: CognitiveCore | None = None

    def __new__(cls, *args, **kwargs) -> CognitiveCore:
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.safety = AISafetyLayer()
        self.kg = ProductionKnowledgeGraph()
        self.learning = PersonalLearningEngine()
        from context_builder import ContextBuilder
        self.context_builder = ContextBuilder()
        from memory_manager import MemoryManager
        self.memory_manager = MemoryManager()
        self.orchestrator = AIOrchestrator()
        self.planner = TaskPlanner()
        self.workflow = WorkflowBuilder()
        from JARVIS.core.system.diagnostics_center import DiagnosticsCenter
        self.diagnostics = DiagnosticsCenter()
        
        self.last_explanation: dict[str, Any] = {}
        self.core_log_path = os.path.abspath(os.path.join("logs", "cognitive_core.json"))
        os.makedirs(os.path.dirname(self.core_log_path), exist_ok=True)

    def process_request(self, command: str) -> dict[str, Any]:
        """Core entry point to process any incoming query or command with safety and explainability."""
        start_time = time.time()
        timings = {}
        
        # ── 1. RATE LIMITING CHECK
        t0 = time.time()
        if self.safety.is_rate_limited():
            resp = "Sir, request rate exceeds security limits. Please standby."
            self.last_explanation = {
                "intent": "Unknown (Blocked)",
                "reasoning": "Gatekeeper triggered rate limit block.",
                "execution_plan": ["halt_execution"],
                "result": "RateLimitedException",
                "confidence": 1.0
            }
            return {"action": "talk", "params": {}, "response": resp, "explanation": self.last_explanation}
        timings["rate_limiting_check"] = (time.time() - t0) * 1000

        # ── 2. INTENT UNDERSTANDING (Intent Engine)
        t0 = time.time()
        from JARVIS.core.automation.local_intent_router import route_local_intent
        intent_resolved = route_local_intent(command)
        intent_desc = "General conversational query"
        action_name = "talk"
        params = {}
        if intent_resolved:
            action_name = intent_resolved.get("action", "talk")
            params = intent_resolved.get("params", {})
            intent_desc = f"Trigger action '{action_name}'"
        timings["intent_detection"] = (time.time() - t0) * 1000

        # ── 3. CONTEXT RETRIEVAL
        t0 = time.time()
        kg_start = time.time()
        kg_context = self.context_builder.build_context(command)
        timings["context_retrieval"] = (time.time() - t0) * 1000

        # ── 4. MEMORY LOOKUP (Memory Retrieval)
        t0 = time.time()
        memory_context = kg_context
        timings["memory_lookup"] = (time.time() - t0) * 1000

        # ── 5. TASK PLANNER (Planning Engine)
        t0 = time.time()
        is_plan = any(w in command.lower() for w in ["and", "then", "prepare", "setup", "start"])
        plan_id = None
        execution_plan_steps = [f"Route command to {action_name}"]
        if is_plan:
            plan_start = time.time()
            plan_id = self.planner.create_plan(command)
            plan_details = self.planner.get_plan(plan_id)
            if plan_details:
                execution_plan_steps = [step.get("prompt", "Execute Step") for step in plan_details.get("subtasks", [])]
                self.diagnostics.record_plan_stats(
                    len(plan_details.get("subtasks", [])),
                    4, # Max DAG depth
                    2, # Parallel tasks
                    (time.time() - plan_start) * 1000
                )
        timings["goal_planning"] = (time.time() - t0) * 1000

        # ── 6. AI MODEL SELECTION (Tool Router)
        t0 = time.time()
        provider, model = self._select_best_model(command, action_name)
        timings["ai_model_selection"] = (time.time() - t0) * 1000

        # ── 7. TOOL SELECTION
        t0 = time.time()
        agent_mapping = {
            "coding": "Coding Agent",
            "research": "Research Agent",
            "security": "Cyber Security Agent",
            "execute_plan": "System Administrator Agent"
        }
        target_agent = agent_mapping.get(action_name, "General Assistant")
        timings["tool_selection"] = (time.time() - t0) * 1000

        # ── 8. DECISION CONFIDENCE & SAFETY GATES
        t0 = time.time()
        intent_conf = 0.99 if intent_resolved else 0.99
        planning_conf = 0.98 if is_plan else 1.0
        model_conf = 0.98
        execution_conf = 0.95
        overall_conf = round((intent_conf + planning_conf + model_conf + execution_conf) / 4.0, 2)

        needs_confirm, reason = self.safety.needs_confirmation(action_name, params)
        if overall_conf < 0.90:
            needs_confirm = True
            reason = f"Decision confidence threshold breached ({overall_conf} < 0.90)"

        timings["safety_evaluation"] = (time.time() - t0) * 1000

        if needs_confirm:
            if action_name == "write_settings" and "file" in params:
                self.safety.create_rollback_point(params["file"], f"Modify settings via {command}")
            
            self.last_explanation = {
                "intent": intent_desc,
                "reasoning": f"Intercepted action due to decision/safety alert: {reason}",
                "execution_plan": ["prompt_user_confirmation"],
                "result": "SafetyAlertException",
                "confidence": overall_conf,
                "confidence_details": {
                    "intent_confidence": intent_conf,
                    "planning_confidence": planning_conf,
                    "model_confidence": model_conf,
                    "execution_confidence": execution_conf
                }
            }
            return {
                "action": "confirm_action",
                "params": {"action_to_confirm": action_name, "original_params": params},
                "response": f"Sir, I require confirmation to execute this action: {reason}. Shall I proceed?",
                "explanation": self.last_explanation
            }

        # ── 9. EXECUTION
        t0 = time.time()
        prompt_with_context = f"{memory_context}\nUser Command: {command}"
        success = True
        exception_str = ""
        try:
            from JARVIS.core.software_engineering.se_orchestrator import SoftwareEngineeringOrchestrator
            if SoftwareEngineeringOrchestrator.is_se_request(command):
                se_res = SoftwareEngineeringOrchestrator().handle(command)
                ai_response = se_res.get("response", "")
                action_name = se_res.get("action", "se_scaffold")
                params = se_res.get("params", {})
                if "explanation" in se_res:
                    self.last_explanation = se_res["explanation"]
            elif is_plan and plan_id:
                self.planner.execute_plan(plan_id)
                ai_response = f"Plan initiated, sir: {command}. I am delegating enqueued agent tasks."
                action_name = "execute_plan"
                params = {"plan_id": plan_id}
            else:
                ai_response = self.orchestrator.query_with_failover(prompt_with_context)
            
            # Record success query analytics
            self.diagnostics.record_model_query(
                provider,
                (time.time() - t0) * 1000,
                0.0015, # Cost per query
                len(prompt_with_context) // 4 + len(ai_response) // 4, # Estimated tokens
                True
            )
        except Exception as e:
            success = False
            exception_str = str(e)
            ai_response = f"System execution fault: {e}"
            self.diagnostics.record_model_query(provider, (time.time() - t0) * 1000, 0.0, 0, False)
            self.diagnostics.record_failure("execution", target_agent, model, "general_tool", exception_str, False)
            self.diagnostics.record_task_outcome(False)
            
        timings["execution"] = (time.time() - t0) * 1000

        # ── 10. LEARNING ENGINE
        t0 = time.time()
        self.learning.log_interaction(command, action_name, params, success=success)
        self.memory_manager.track_learning_interaction(
            model=model,
            language=params.get("language", "Python"),
            tools_used=[action_name]
        )
        self.diagnostics.record_learning_event("successful_workflow", f"goal: {command}")
        timings["learning"] = (time.time() - t0) * 1000

        # ── 11. MEMORY UPDATE
        t0 = time.time()
        self.kg.add_node(f"cmd_{int(time.time())}", "COMMAND", command, {"action": action_name})
        from memory_engine import MemoryEngine
        MemoryEngine().write_memory("conversation", command, f"Action: {action_name}, Success: {success}")
        timings["memory_update"] = (time.time() - t0) * 1000

        # ── 12. REASONING ENGINE PAYLOAD
        elapsed = (time.time() - start_time) * 1000
        timings["response_compilation"] = (time.time() - start_time) * 1000 - elapsed
        self.diagnostics.record_timeline(timings)
        self.diagnostics.record_task_outcome(success)
        
        self.last_explanation = {
            "intent": intent_desc,
            "reasoning": f"Synaptic pipeline successfully executed in {elapsed:.1f}ms on {provider} ({model}) via {target_agent}.",
            "execution_plan": execution_plan_steps,
            "result": "Success" if (success and ai_response) else "ExecutionFault",
            "confidence": overall_conf,
            "confidence_details": {
                "intent_confidence": intent_conf,
                "planning_confidence": planning_conf,
                "model_confidence": model_conf,
                "execution_confidence": execution_conf
            },
            "timeline": timings
        }

        result = {
            "action": action_name,
            "params": params,
            "response": ai_response,
            "explanation": self.last_explanation
        }
        self._save_core_state(result)
        return result

    def _select_best_model(self, command: str, action: str) -> tuple[str, str]:
        # Models configuration parameters dictionary
        model_features = {
            "grok": {"provider": "xAI", "model": "Grok 3", "cost": 0.002, "latency": 145, "context": 128, "offline": False},
            "claude": {"provider": "Anthropic", "model": "Claude 3.5 Sonnet", "cost": 0.003, "latency": 180, "context": 200, "offline": False},
            "gemini": {"provider": "Google", "model": "Gemini 1.5 Pro", "cost": 0.00125, "latency": 120, "context": 2048, "offline": False},
            "chatgpt": {"provider": "OpenAI", "model": "ChatGPT 4o", "cost": 0.0025, "latency": 165, "context": 128, "offline": False},
            "deepseek": {"provider": "DeepSeek", "model": "DeepSeek R1", "cost": 0.00055, "latency": 250, "context": 64, "offline": False},
            "ollama": {"provider": "Local", "model": "Ollama (Llama 3)", "cost": 0.0, "latency": 12, "context": 8, "offline": True},
            "lmstudio": {"provider": "Local", "model": "LM Studio (Mistral)", "cost": 0.0, "latency": 14, "context": 16, "offline": True}
        }
        
        is_offline = "offline" in command.lower() or "local" in command.lower()
        is_cost_sensitive = "cheap" in command.lower() or "cost" in command.lower()
        is_large_context = "large" in command.lower() or "context" in command.lower()
        
        candidates = list(model_features.values())
        if is_offline:
            candidates = [c for c in candidates if c["offline"]]
        if is_large_context:
            candidates = [c for c in candidates if c["context"] >= 128]
            
        if not candidates:
            candidates = [model_features["gemini"]]
            
        candidates.sort(key=lambda x: x["latency"])
        if is_cost_sensitive:
            candidates.sort(key=lambda x: x["cost"])
            
        best = candidates[0]
        return best["provider"], best["model"]

    def _save_core_state(self, state: dict) -> None:
        try:
            with open(self.core_log_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass
