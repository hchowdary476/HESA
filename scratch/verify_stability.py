import os
import sys
import time
import subprocess
import psutil
import json

root_dir = r"c:\Users\veera\OneDrive\Desktop\Open.Jarvis-main"
python_exe = os.path.join(root_dir, ".venv", "Scripts", "python.exe")
main_script = os.path.join(root_dir, "jarvis.py")
hb_dir = os.path.join(root_dir, "logs", "heartbeats")

# Clear logs
for log_file in ["logs/error.log", "logs/service_crash.log", "logs/gui_test.log"]:
    fp = os.path.join(root_dir, log_file)
    if os.path.exists(fp):
        try:
            os.remove(fp)
        except Exception:
            pass

print("Launching HESA Application Suite with logging...")
env = os.environ.copy()
env["PYTHONPATH"] = root_dir + os.pathsep + env.get("PYTHONPATH", "")

gui_log_path = os.path.join(root_dir, "logs", "gui_test.log")
with open(gui_log_path, "w", encoding="utf-8") as gui_lf:
    gui_process = subprocess.Popen(
        [python_exe, main_script],
        cwd=root_dir,
        env=env,
        stdout=gui_lf,
        stderr=gui_lf
    )

time.sleep(12)  # Wait for boot and services to settle

# Find all spawned sub-processes
processes = []
try:
    parent = psutil.Process(gui_process.pid)
    processes.append(parent)
    for child in parent.children(recursive=True):
        processes.append(child)
except Exception as e:
    pass

duration = 30  # 30 seconds check
start_time = time.time()
stable = True
check_interval = 5

print("Starting runtime stability verification loop...")
while time.time() - start_time < duration:
    elapsed = int(time.time() - start_time)
    
    # Check if main GUI process is alive
    poll_val = gui_process.poll()
    if poll_val is not None:
        print(f"ALERT: Main GUI process exited unexpectedly with code {poll_val}!")
        stable = False
        break
        
    tot_threads = 0
    tot_memory = 0.0
    alive_count = 0
    
    for p in list(processes):
        try:
            if p.is_running():
                threads = p.num_threads()
                mem = p.memory_info().rss / (1024 * 1024)
                tot_threads += threads
                tot_memory += mem
                alive_count += 1
        except Exception:
            pass
            
    print(f"[{elapsed}s elapsed] Alive: {alive_count}/{len(processes)} | Threads: {tot_threads} | RAM: {tot_memory:.1f}MB")
    time.sleep(check_interval)

# Terminate HESA
print("Terminating HESA processes...")
gui_process.terminate()
try:
    gui_process.wait(timeout=5)
except Exception:
    gui_process.kill()

# Kill remaining service processes if any
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmd = proc.info.get('cmdline')
        if cmd and any("jarvis.py" in str(c).lower() or "supervisor" in str(c).lower() for c in cmd):
            if proc.pid != os.getpid():
                proc.kill()
    except Exception:
        pass

if not stable:
    print("\n--- GUI TEST LOG CONTENT ---")
    if os.path.exists(gui_log_path):
        with open(gui_log_path, "r", encoding="utf-8") as f:
            print(f.read())
    sys.exit(1)
else:
    print("\nSUCCESS: Runtime stability verification PASSED!")
    sys.exit(0)
