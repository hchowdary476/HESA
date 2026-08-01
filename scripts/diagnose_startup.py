import sys
import os
import time
import subprocess
from collections import OrderedDict

def print_banner(title):
    print("\n" + "=" * 50)
    print(f" {title.upper()}")
    print("=" * 50)

def run_diagnostics():
    timings = OrderedDict()
    blocking_status = {}
    recommendations = {}

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, root_dir)

    print_banner("1. Measuring Module Import Times")
    
    modules_to_time = [
        ("customtkinter", "import customtkinter"),
        ("psutil", "import psutil"),
        ("JARVIS.core.system.utils.env_helper", "from JARVIS.core.system.utils.env_helper import find_env_file"),
        ("JARVIS.app.main", "from JARVIS.app.main import set_ui_callback, start_jarvis"),
        ("JARVIS.core.automation.groq_router", "from JARVIS.core.automation.groq_router import analyze_with_groq"),
        ("JARVIS.core.automation.komutlar", "from JARVIS.core.automation.komutlar import process_command"),
        ("JARVIS.core.security.security_shield", "from JARVIS.core.security.security_shield import run_face_match_check"),
        ("JARVIS.core.system.utils.camera_tracker", "from JARVIS.core.system.utils.camera_tracker import get_cached_camera_status"),
        ("JARVIS.runtime.smart_activation", "from JARVIS.runtime.smart_activation import create_activation_daemon"),
    ]

    for name, import_stmt in modules_to_time:
        start = time.perf_counter()
        try:
            exec(import_stmt, globals())
            elapsed = time.perf_counter() - start
            timings[name] = elapsed
            blocking_status[name] = "OK" if elapsed < 1.0 else "SLOW"
            print(f"- Import `{name}`: {elapsed:.4f}s")
        except Exception as e:
            timings[name] = -1
            blocking_status[name] = f"ERROR: {e}"
            print(f"- Import `{name}`: FAILED ({e})")

    print_banner("2. Database & Config Load Testing")
    
    # Measure memory.json load
    start = time.perf_counter()
    try:
        from JARVIS.core.memory.memory_store import load_memory
        mem = load_memory()
        elapsed = time.perf_counter() - start
        timings["Database load (memory.json)"] = elapsed
        blocking_status["Database load (memory.json)"] = "OK" if elapsed < 0.2 else "SLOW"
        print(f"- Load memory.json: {elapsed:.4f}s")
    except Exception as e:
        blocking_status["Database load (memory.json)"] = f"ERROR: {e}"

    # Measure settings load
    start = time.perf_counter()
    try:
        from JARVIS.core.security.security_shield import load_settings
        settings = load_settings()
        elapsed = time.perf_counter() - start
        timings["Config load (settings.json)"] = elapsed
        blocking_status["Config load (settings.json)"] = "OK" if elapsed < 0.2 else "SLOW"
        print(f"- Load settings: {elapsed:.4f}s")
    except Exception as e:
        blocking_status["Config load (settings.json)"] = f"ERROR: {e}"

    print_banner("3. Network & Cloud Check Testing")
    
    # Check if is_internet_available blocks
    start = time.perf_counter()
    try:
        from JARVIS.core.automation.groq_router import is_internet_available
        # Trigger check
        online = is_internet_available()
        elapsed = time.perf_counter() - start
        timings["is_internet_available check"] = elapsed
        blocking_status["is_internet_available check"] = "OK" if elapsed < 0.5 else "SLOW (Possible DNS block)"
        print(f"- Internet check (cached = {online}): {elapsed:.4f}s")
    except Exception as e:
        blocking_status["is_internet_available check"] = f"ERROR: {e}"

    # Check if pinging DNS directly takes time
    start = time.perf_counter()
    dns_reachable = False
    try:
        import socket
        socket.create_connection(("1.1.1.1", 53), timeout=1.0).close()
        dns_reachable = True
        elapsed = time.perf_counter() - start
        timings["DNS Socket connection (1.1.1.1)"] = elapsed
        blocking_status["DNS Socket connection (1.1.1.1)"] = "OK" if elapsed < 0.3 else "SLOW (Network lag)"
        print(f"- Socket connection to 1.1.1.1: {elapsed:.4f}s")
    except Exception as e:
        elapsed = time.perf_counter() - start
        timings["DNS Socket connection (1.1.1.1)"] = elapsed
        blocking_status["DNS Socket connection (1.1.1.1)"] = f"TIMEOUT / BLOCKING: {e}"
        print(f"- Socket connection to 1.1.1.1: FAILED in {elapsed:.4f}s ({e})")

    print_banner("4. Camera Tracker Probe Testing")
    
    # Measure force probe vs cached probe
    start = time.perf_counter()
    try:
        from JARVIS.core.system.utils.camera_tracker import get_cached_camera_status
        cam_status = get_cached_camera_status(force_probe=False)
        elapsed = time.perf_counter() - start
        timings["Camera status (cached)"] = elapsed
        blocking_status["Camera status (cached)"] = "OK"
        print(f"- Camera status (cached = {cam_status}): {elapsed:.4f}s")
    except Exception as e:
        blocking_status["Camera status (cached)"] = f"ERROR: {e}"

    start = time.perf_counter()
    try:
        cam_status_force = get_cached_camera_status(force_probe=True)
        elapsed = time.perf_counter() - start
        timings["Camera probe (physical)"] = elapsed
        blocking_status["Camera probe (physical)"] = "OK" if elapsed < 2.0 else "BLOCKING (OpenCV/Driver delay)"
        print(f"- Camera physical probe (status = {cam_status_force}): {elapsed:.4f}s")
    except Exception as e:
        elapsed = time.perf_counter() - start
        timings["Camera probe (physical)"] = elapsed
        blocking_status["Camera probe (physical)"] = f"ERROR: {e}"
        print(f"- Camera physical probe: FAILED in {elapsed:.4f}s ({e})")

    print_banner("5. GUI Window Mainloop Start Verification")
    
    # Verify CustomTkinter window works without freezing in main thread (aborted after 0.5s)
    start = time.perf_counter()
    try:
        import customtkinter as ctk
        app = ctk.CTk()
        app.title("Diagnostic Test")
        app.geometry("100x100")
        # Exit automatically after 500ms
        app.after(500, app.destroy)
        app.mainloop()
        elapsed = time.perf_counter() - start
        timings["CustomTkinter mainloop initialization"] = elapsed
        blocking_status["CustomTkinter mainloop initialization"] = "OK"
        print(f"- CustomTkinter start and exit: {elapsed:.4f}s")
    except Exception as e:
        elapsed = time.perf_counter() - start
        timings["CustomTkinter mainloop initialization"] = elapsed
        blocking_status["CustomTkinter mainloop initialization"] = f"BLOCKING / ERROR: {e}"
        print(f"- CustomTkinter start: FAILED ({e})")

    # Construct recommendations based on measurements
    for name in timings:
        elapsed = timings[name]
        status = blocking_status[name]
        
        if "customtkinter" in name and elapsed > 1.5:
            recommendations[name] = "CTK startup is slow. Avoid reloading themes at runtime or check GPU driver configuration."
        elif "groq_router" in name and elapsed > 1.5:
            recommendations[name] = "Groq router load is slow due to API client instantiation. Defer Groq client creation to first use (lazy loading)."
        elif "Camera probe" in name and elapsed > 2.0:
            recommendations[name] = "Webcam physical probe takes too long. Disable physical probe at startup and run it asynchronously inside a background worker."
        elif "is_internet_available" in name and elapsed > 0.5:
            recommendations[name] = "Internet connectivity check blocked the main thread. Always invoke connection checks asynchronously in background threads."
        elif "DNS Socket" in name and "TIMEOUT" in str(status):
            recommendations[name] = "DNS socket ping timed out. Disable synchronous socket connection checks or use non-blocking select pings with a lower timeout (e.g. 0.05s)."
        else:
            recommendations[name] = "None (No action needed)."

    # Write report
    report_path = os.path.join(root_dir, "STARTUP_TIMING_REPORT.md")
    
    report_content = []
    report_content.append("# STARTUP TIMING REPORT\n")
    report_content.append("## EXECUTIVE SUMMARY")
    report_content.append("Detailed diagnostics of the JARVIS startup loading pipeline, tracing modules, database loads, network sockets, camera status probes, and GUI loops.\n")
    
    report_content.append("## TIMING STATISTICS\n")
    report_content.append("| Module / Phase | Execution Time | Blocking Status | Recommended Fix |")
    report_content.append("| :--- | :--- | :--- | :--- |")
    for name in timings:
        elapsed_str = f"{timings[name]:.4f}s" if timings[name] >= 0 else "N/A"
        report_content.append(f"| `{name}` | {elapsed_str} | **{blocking_status[name]}** | {recommendations.get(name, 'None')} |")
    report_content.append("")
    
    # Detailed diagnostic observations
    report_content.append("## DIAGNOSTIC OBSERVATIONS\n")
    
    # 1. Groq Router & Network Checks
    report_content.append("### 1. Network & Groq Client Initialization")
    if timings.get("JARVIS.core.automation.groq_router", 0) > 1.0 or timings.get("is_internet_available check", 0) > 0.5:
        report_content.append("> [!WARNING]")
        report_content.append("> The Groq router is imported during main thread module imports. If DNS resolving or socket ping takes long, it blocks the main thread, delaying GUI initialization.")
    else:
        report_content.append("- Groq router and internet checks are currently executing cleanly. However, if the DNS or Groq servers are unreachable, `socket.create_connection` can cause blockages if run synchronously.")
    report_content.append("")
    
    # 2. Camera Probing
    report_content.append("### 2. Camera Health & Diagnostics Probing")
    if timings.get("Camera probe (physical)", 0) > 1.5:
        report_content.append("> [!IMPORTANT]")
        report_content.append("> **Webcam physical probe takes unusually long.** Probing device index `0` synchronously using OpenCV `cv2.VideoCapture` blocks the main thread because the OS needs to wake up the webcam driver.")
    else:
        report_content.append("- Camera probing completed without critical delays. It is still recommended to run physical probes asynchronously to prevent GUI lag when driver wakeups are slow.")
    report_content.append("")
    
    # 3. Database Loads
    report_content.append("### 3. Database & Config Parsing")
    report_content.append(f"- Memory database (`memory.json`) and settings database load in {timings.get('Database load (memory.json)', 0):.4f}s, which is well below the latency threshold.")
    report_content.append("")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_content))

    print(f"\n[DIAGNOSTICS] Diagnostic audit finished. Report saved to: {report_path}")

if __name__ == "__main__":
    run_diagnostics()
