"""
JARVIS GUI Startup Performance Measurement Tool
Measures import times, module load times, and memory usage during startup.
"""
import time
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

class StartupProfiler:
    def __init__(self):
        self.timings = {}
        self.memory_snapshots = {}
        
    def measure_import(self, module_name, import_func):
        """Measure time and memory for a single import."""
        import psutil
        process = psutil.Process()
        
        mem_before = process.memory_info().rss / 1024 / 1024  # MB
        start = time.perf_counter()
        
        try:
            result = import_func()
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
        
        elapsed = (time.perf_counter() - start) * 1000  # ms
        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        mem_delta = mem_after - mem_before
        
        self.timings[module_name] = {
            'time_ms': elapsed,
            'mem_before_mb': mem_before,
            'mem_after_mb': mem_after,
            'mem_delta_mb': mem_delta,
            'success': success,
            'error': error,
            'blocking': elapsed > 100  # >100ms is blocking
        }
        
        return result
    
    def generate_report(self):
        """Generate formatted report."""
        print("\n" + "="*80)
        print("JARVIS GUI STARTUP PERFORMANCE AUDIT")
        print("="*80 + "\n")
        
        # Sort by load time
        sorted_timings = sorted(self.timings.items(), key=lambda x: x[1]['time_ms'], reverse=True)
        
        total_time = sum(t['time_ms'] for t in self.timings.values())
        blocking_modules = [m for m, t in self.timings.items() if t['blocking']]
        
        print(f"{'Module':<40} {'Time (ms)':<12} {'RAM (MB)':<12} {'Status':<12}")
        print("-"*80)
        
        for module, timing in sorted_timings:
            status = "✅ OK" if timing['success'] else "❌ FAIL"
            if timing['blocking']:
                status += " ⚠️ SLOW"
            
            print(f"{module:<40} {timing['time_ms']:>10.2f} {timing['mem_delta_mb']:>+10.2f} {status:<12}")
        
        print("-"*80)
        print(f"{'TOTAL':<40} {total_time:>10.2f} ms")
        print(f"\n⚠️  Blocking modules (>100ms): {len(blocking_modules)}")
        print(f"📊 Total modules measured: {len(self.timings)}")
        
        return self.timings

if __name__ == "__main__":
    profiler = StartupProfiler()
    
    print("🔍 Measuring JARVIS GUI startup performance...")
    print("Please wait, this will take a moment...\n")
    
    # 1. Environment setup
    profiler.measure_import("dotenv", lambda: __import__('dotenv'))
    profiler.measure_import("load_dotenv", lambda: __import__('dotenv').load_dotenv())
    
    # 2. Core Python libraries
    profiler.measure_import("os", lambda: __import__('os'))
    profiler.measure_import("sys", lambda: __import__('sys'))
    profiler.measure_import("threading", lambda: __import__('threading'))
    profiler.measure_import("json", lambda: __import__('json'))
    profiler.measure_import("pathlib", lambda: __import__('pathlib'))
    
    # 3. Third-party dependencies
    profiler.measure_import("psutil", lambda: __import__('psutil'))
    profiler.measure_import("customtkinter", lambda: __import__('customtkinter'))
    profiler.measure_import("numpy", lambda: __import__('numpy'))
    profiler.measure_import("speech_recognition", lambda: __import__('speech_recognition'))
    
    # 4. Edge TTS
    profiler.measure_import("edge_tts", lambda: __import__('edge_tts'))
    
    # 5. Groq
    profiler.measure_import("groq", lambda: __import__('groq'))
    
    # 6. Optional heavy imports
    try:
        profiler.measure_import("mediapipe", lambda: __import__('mediapipe'))
    except:
        pass
    
    try:
        profiler.measure_import("opencv (cv2)", lambda: __import__('cv2'))
    except:
        pass
    
    try:
        profiler.measure_import("sounddevice", lambda: __import__('sounddevice'))
    except:
        pass
    
    try:
        profiler.measure_import("vosk", lambda: __import__('vosk'))
    except:
        pass
    
    try:
        profiler.measure_import("pywebview", lambda: __import__('webview'))
    except:
        pass
    
    # 7. JARVIS modules
    profiler.measure_import("JARVIS.core.system.utils.env_helper", 
                           lambda: __import__('JARVIS.core.system.utils.env_helper', fromlist=['find_env_file']))
    
    profiler.measure_import("JARVIS.gui.ui_theme", 
                           lambda: __import__('JARVIS.gui.ui_theme', fromlist=['PALETTE']))
    
    profiler.measure_import("JARVIS.gui.ui_pages", 
                           lambda: __import__('JARVIS.gui.ui_pages', fromlist=['build_info_page']))
    
    profiler.measure_import("JARVIS.core.automation.groq_router", 
                           lambda: __import__('JARVIS.core.automation.groq_router', fromlist=['client']))
    
    profiler.measure_import("JARVIS.core.voice.ses_motoru", 
                           lambda: __import__('JARVIS.core.voice.ses_motoru', fromlist=['speak']))
    
    profiler.measure_import("JARVIS.core.voice.speech_backend", 
                           lambda: __import__('JARVIS.core.voice.speech_backend', fromlist=['transcribe_audio']))
    
    profiler.measure_import("JARVIS.core.system.observability", 
                           lambda: __import__('JARVIS.core.system.observability', fromlist=['build_slo_report']))
    
    # Generate report
    results = profiler.generate_report()
    
    # Save detailed JSON report
    import json
    with open('GUI_STARTUP_REPORT.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Detailed report saved to: GUI_STARTUP_REPORT.json")
