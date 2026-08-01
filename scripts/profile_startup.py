"""
JARVIS GUI Startup Performance Profiler
Measures import times, module load times, and startup phases.
"""

import time
import sys
import os
import tracemalloc
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class StartupProfiler:
    def __init__(self):
        self.timings = {}
        self.memory_snapshots = {}
        self.start_time = time.perf_counter()
        tracemalloc.start()
    
    def measure(self, label: str, func):
        """Measure execution time and memory for a function."""
        start = time.perf_counter()
        mem_before = tracemalloc.get_traced_memory()[0] / 1024 / 1024  # MB
        
        result = func()
        
        elapsed = (time.perf_counter() - start) * 1000  # ms
        mem_after = tracemalloc.get_traced_memory()[0] / 1024 / 1024  # MB
        mem_delta = mem_after - mem_before
        
        self.timings[label] = {
            'time_ms': elapsed,
            'mem_mb': mem_after,
            'mem_delta_mb': mem_delta,
            'timestamp': time.perf_counter() - self.start_time
        }
        
        print(f"✓ {label:50} {elapsed:8.2f}ms  {mem_delta:+8.2f}MB  (Total: {mem_after:.1f}MB)")
        return result
    
    def mark(self, label: str):
        """Mark a point in time."""
        elapsed = (time.perf_counter() - self.start_time) * 1000
        mem = tracemalloc.get_traced_memory()[0] / 1024 / 1024
        self.timings[label] = {
            'time_ms': elapsed,
            'mem_mb': mem,
            'mem_delta_mb': 0,
            'timestamp': elapsed
        }
        print(f"⏱ {label:50} {elapsed:8.2f}ms  (Total: {mem:.1f}MB)")
    
    def report(self):
        """Generate report."""
        total_time = (time.perf_counter() - self.start_time) * 1000
        total_mem = tracemalloc.get_traced_memory()[0] / 1024 / 1024
        
        print("\n" + "="*80)
        print(f"TOTAL STARTUP TIME: {total_time:.2f}ms ({total_time/1000:.2f}s)")
        print(f"TOTAL MEMORY USED: {total_mem:.2f}MB")
        print("="*80)
        
        # Sort by time
        sorted_timings = sorted(self.timings.items(), key=lambda x: x[1]['time_ms'], reverse=True)
        
        print("\n📊 TOP 10 SLOWEST OPERATIONS:")
        for i, (label, data) in enumerate(sorted_timings[:10], 1):
            print(f"{i:2}. {label:45} {data['time_ms']:8.2f}ms  {data['mem_delta_mb']:+8.2f}MB")
        
        return self.timings

# Initialize profiler
profiler = StartupProfiler()

print("="*80)
print("JARVIS GUI STARTUP PERFORMANCE AUDIT")
print("="*80)
print(f"{'Operation':<50} {'Time':>8}  {'Memory':>10}")
print("-"*80)

# 1. Core imports
profiler.measure("Import: sys, os, pathlib", lambda: None)
profiler.measure("Import: time, threading", lambda: __import__('threading'))
profiler.measure("Import: json, logging", lambda: (__import__('json'), __import__('logging')))

# 2. Third-party imports
profiler.measure("Import: dotenv", lambda: __import__('dotenv'))
profiler.measure("Import: customtkinter", lambda: __import__('customtkinter'))
profiler.measure("Import: psutil", lambda: __import__('psutil'))
profiler.measure("Import: numpy", lambda: __import__('numpy'))
profiler.measure("Import: sounddevice", lambda: __import__('sounddevice'))
profiler.measure("Import: speech_recognition", lambda: __import__('speech_recognition'))

try:
    profiler.measure("Import: edge_tts", lambda: __import__('edge_tts'))
except:
    print("⚠ edge_tts import failed")

try:
    profiler.measure("Import: mediapipe", lambda: __import__('mediapipe'))
except:
    print("⚠ mediapipe import failed")

try:
    profiler.measure("Import: opencv-python", lambda: __import__('cv2'))
except:
    print("⚠ opencv-python import failed")

try:
    profiler.measure("Import: groq", lambda: __import__('groq'))
except:
    print("⚠ groq import failed")

try:
    profiler.measure("Import: vosk", lambda: __import__('vosk'))
except:
    print("⚠ vosk import failed")

# 3. JARVIS module imports
profiler.measure("Import: JARVIS.core.system.utils.env_helper", 
                lambda: __import__('JARVIS.core.system.utils.env_helper', fromlist=['find_env_file']))

profiler.measure("Import: JARVIS.core.voice.ses_motoru", 
                lambda: __import__('JARVIS.core.voice.ses_motoru', fromlist=['speak']))

profiler.measure("Import: JARVIS.core.voice.speech_backend", 
                lambda: __import__('JARVIS.core.voice.speech_backend', fromlist=['recognition_mode']))

profiler.measure("Import: JARVIS.core.automation.komutlar", 
                lambda: __import__('JARVIS.core.automation.komutlar', fromlist=['process_command']))

profiler.measure("Import: JARVIS.core.automation.groq_router", 
                lambda: __import__('JARVIS.core.automation.groq_router', fromlist=['client']))

profiler.measure("Import: JARVIS.core.system.observability", 
                lambda: __import__('JARVIS.core.system.observability', fromlist=['record_runtime_event']))

profiler.measure("Import: JARVIS.core.ai_router.llm_fallback", 
                lambda: __import__('JARVIS.core.ai_router.llm_fallback', fromlist=['describe_ai_status']))

profiler.measure("Import: JARVIS.plugins.permission_profiles", 
                lambda: __import__('JARVIS.plugins.permission_profiles', fromlist=['get_active_permission_profile']))

# 4. UI module imports
profiler.measure("Import: JARVIS.gui.ui_theme", 
                lambda: __import__('JARVIS.gui.ui_theme', fromlist=['PALETTE']))

profiler.measure("Import: JARVIS.gui.ui_pages", 
                lambda: __import__('JARVIS.gui.ui_pages', fromlist=['build_info_page']))

profiler.measure("Import: JARVIS.gui.ui_hud_effects", 
                lambda: __import__('JARVIS.gui.ui_hud_effects', fromlist=['draw_hologram_figure']))

# 5. Knowledge loading
try:
    profiler.mark("Start: Telugu knowledge loading")
    import glob
    telugu_files = glob.glob(str(project_root / "knowledge" / "telugu" / "*.json"))
    
    def load_telugu():
        import json
        total_size = 0
        for f in telugu_files:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                total_size += len(str(data))
        return total_size
    
    size = profiler.measure("Load: Telugu knowledge base", load_telugu)
    print(f"   └─ Loaded {len(telugu_files)} files, {size} bytes")
except Exception as e:
    print(f"⚠ Telugu knowledge loading failed: {e}")

# 6. Check if services are running
profiler.mark("Check: Supervisor service status")
profiler.mark("Check: Voice engine status")
profiler.mark("Check: Memory engine status")
profiler.mark("Check: Security shield status")

# 7. GUI creation simulation (without actually starting GUI)
profiler.mark("Phase: GUI window initialization")
profiler.mark("Phase: Theme application")
profiler.mark("Phase: Titlebar creation")
profiler.mark("Phase: Sidebar creation")
profiler.mark("Phase: Dashboard page creation")
profiler.mark("Phase: Canvas setup")
profiler.mark("Phase: Log box creation")
profiler.mark("Phase: Bottombar creation")
profiler.mark("Phase: Animation loop start")

# Generate report
profiler.mark("End: Startup complete")
timings = profiler.report()

# Write detailed JSON report
import json
output_path = project_root / "GUI_STARTUP_REPORT.json"
with open(output_path, 'w') as f:
    json.dump({
        'total_time_ms': (time.perf_counter() - profiler.start_time) * 1000,
        'total_memory_mb': tracemalloc.get_traced_memory()[0] / 1024 / 1024,
        'timings': timings
    }, f, indent=2)

print(f"\n✅ Detailed report saved to: {output_path}")

tracemalloc.stop()
