import os
import time
import json
from JARVIS.core.automation import groq_router

def run_validation():
    print("=== HYBRID AI ROUTING VALIDATION ===")
    
    # 1. Non-blocking Cache Check Speed
    start = time.perf_counter()
    online = groq_router.is_internet_available()
    latency = groq_router.get_cached_latency()
    elapsed = (time.perf_counter() - start) * 1000.0
    print(f"Network Check: {'ONLINE' if online else 'OFFLINE'} (Latency: {latency}ms)")
    print(f"Non-blocking Probe Execution Time: {elapsed:.3f}ms")
    assert elapsed < 5.0, f"Probe took {elapsed:.3f}ms (expected < 5.0ms)"
    
    # 2. Priority Routing Config Resolution
    print(f"Primary Provider Config: {os.getenv('JARVIS_PRIMARY_AI', 'GROQ')}")
    print(f"Secondary Provider Config: {os.getenv('JARVIS_SECONDARY_AI', 'GEMINI')}")
    print(f"Offline Provider Config: {os.getenv('JARVIS_OFFLINE_AI', 'OLLAMA')}")
    
    # 3. Stats Tracking and JSON Validation
    result = groq_router.analyze_with_groq("hello")
    print(f"Processed command result: {result.get('action')}")
    
    stats = groq_router.get_hybrid_ai_status()
    print("Active stats recorded:")
    print(json.dumps(stats, indent=2))
    
    assert "stats" in stats, "stats dictionary not found"
    assert "GROQ" in stats["stats"], "GROQ provider stats missing"
    assert "GEMINI" in stats["stats"], "GEMINI provider stats missing"
    assert "OLLAMA" in stats["stats"], "OLLAMA provider stats missing"
    
    print("\nRouting validation succeeded successfully.")

if __name__ == "__main__":
    run_validation()
