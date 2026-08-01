"""Unit test suite verifying HESA OS Local-First Voice Assistant Architecture.

Tests cover:
  1. Wake Word detection ('SAI') & False positive rejection ('say', 'sigh', 'sai ram')
  2. Intent Classification: LOCAL_COMMAND vs AI_QUERY
  3. Memory lookup (< 50ms requirement) & preference saving
  4. Task-type AI Routing (coding -> Claude, reasoning -> OpenAI, general -> Gemini, offline -> Ollama)
  5. Safety confirmation guard for dangerous actions (shutdown, restart)
"""
from __future__ import annotations

import sys
import os
import time

_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

os.environ["JARVIS_WAKE_DEBUG"] = "0"

import pytest
from JARVIS.core.voice.wake_word import analyze_wake_word
from JARVIS.core.automation.local_intent_router import classify_intent, route_local_intent
from JARVIS.core.memory.memory_preferences import detect_and_save_preference, get_preference, set_preference
from JARVIS.core.ai_router.ai_orchestrator import AIOrchestrator


def test_wake_word_sai():
    assert analyze_wake_word("hey sai open calculator")["detected"]
    assert analyze_wake_word("sai open chrome")["detected"]
    assert analyze_wake_word("hi sai play music")["detected"]
    assert analyze_wake_word("okay sai shutdown system")["detected"]

    # Rejections
    assert not analyze_wake_word("say")["detected"]
    assert not analyze_wake_word("sigh")["detected"]
    assert not analyze_wake_word("side")["detected"]
    assert not analyze_wake_word("sai ram")["detected"]
    assert not analyze_wake_word("science")["detected"]


def test_intent_classification():
    # Local commands
    cat1, act1 = classify_intent("open calculator")
    assert cat1 == "LOCAL_COMMAND"
    assert isinstance(act1, dict) and act1["action"] == "open_app"

    cat2, act2 = classify_intent("increase volume")
    assert cat2 == "LOCAL_COMMAND"

    cat3, act3 = classify_intent("take screenshot")
    assert cat3 == "LOCAL_COMMAND"

    # AI Queries
    cat4, task4 = classify_intent("write python code for binary search")
    assert cat4 == "AI_QUERY"
    assert task4 == "coding"

    cat5, task5 = classify_intent("solve this math reasoning puzzle")
    assert cat5 == "AI_QUERY"
    assert task5 == "reasoning"

    cat6, task6 = classify_intent("what is DBMS")
    assert cat6 == "AI_QUERY"
    assert task6 == "general"


def test_memory_engine_speed():
    set_preference("favorite_language", "Python")
    t0 = time.perf_counter()
    resp = detect_and_save_preference("What is my favorite language?")
    latency_ms = (time.perf_counter() - t0) * 1000

    assert resp == "Your favorite language is Python."
    assert latency_ms < 50.0, f"Memory lookup took {latency_ms:.2f}ms (must be < 50ms)"


def test_safety_confirmation_flags():
    act = route_local_intent("shutdown pc")
    assert act is not None
    assert act.get("action") == "shutdown"
    assert act.get("requires_confirmation") is True


def test_ai_router_task_priorities(monkeypatch):
    orc = AIOrchestrator()
    # Mock query_provider to return immediately so we measure routing decision latency
    monkeypatch.setattr(orc, "query_provider", lambda provider, prompt: f"mock {provider} response")

    t0 = time.perf_counter()
    res = orc.query_with_failover("write python code", task_type="coding")
    decision_ms = (time.perf_counter() - t0) * 1000

    assert res == "mock claude response"
    assert decision_ms < 100.0, f"Routing decision took {decision_ms:.2f}ms (must be < 100ms)"

