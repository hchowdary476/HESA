"""
Real HESA Startup Log Capture — v2
====================================
Launches jarvis.py via pythonw.exe (matching Registry Run key exactly),
captures all output via log file, and tails for required [VOICE] stage tags.

Handles the Windows port lock TIME_WAIT issue by waiting after killing stale
processes before launching fresh.

Step 2 proof: verify [VOICE] ENGINE STARTED, WAKE THREAD CREATED,
WAKE LOOP ENTERED, MIC STARTED appear in the real startup log.
"""
import os, sys, subprocess, time, socket

root = r"c:\Users\veera\OneDrive\Desktop\Open.Jarvis-main"
pythonw = os.path.join(root, ".venv", "Scripts", "pythonw.exe")
main = os.path.join(root, "jarvis.py")
log = os.path.join(root, "logs", "_real_launch.log")
hb_dir = os.path.join(root, "logs", "heartbeats")
lock_port = 19106

os.makedirs(os.path.join(root, "logs"), exist_ok=True)

# ── Step 1: Kill ALL python/pythonw processes except ourselves ───────────────
import psutil
my_pid = os.getpid()
killed = []
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if proc.pid == my_pid:
            continue
        name = (proc.info.get('name') or '').lower()
        if 'python' in name:
            proc.kill()
            killed.append(proc.pid)
    except Exception:
        pass

if killed:
    print(f"[CLEAN] Killed {len(killed)} python processes: {killed}")
else:
    print("[CLEAN] No python processes to kill.")

# ── Step 2: Wait for port 19106 to be released (TIME_WAIT) ──────────────────
print(f"[WAIT] Waiting for port {lock_port} to be released...")
wait_start = time.time()
max_wait = 30
while time.time() - wait_start < max_wait:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", lock_port))
        s.close()
        print(f"[WAIT] Port {lock_port} is free after {time.time()-wait_start:.1f}s")
        break
    except OSError:
        time.sleep(1)
else:
    print(f"[WARN] Port {lock_port} still busy after {max_wait}s — launching anyway")

# ── Step 3: Clear previous log ───────────────────────────────────────────────
with open(log, "w", encoding="utf-8") as f:
    f.write(f"=== HESA Real Launch Log via pythonw.exe ===\n")
    f.write(f"Launched at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

env = os.environ.copy()
env["PYTHONPATH"] = root

print(f"\n[LAUNCH] Executing: {pythonw}")
print(f"         Script:    {main}")
print(f"         Log file:  {log}\n")

proc = subprocess.Popen(
    [pythonw, main],
    cwd=root,
    env=env,
    stdout=open(log, "a", encoding="utf-8"),
    stderr=subprocess.STDOUT
)
print(f"[LAUNCH] Process PID: {proc.pid}")

# ── Step 4: Watch log for required [VOICE] stage tags ───────────────────────
REQUIRED_TAGS = [
    "[VOICE] ENGINE STARTED",
    "[VOICE] WAKE THREAD CREATED",
    "[VOICE] WAKE LOOP ENTERED",
    "[VOICE] MIC STARTED",
]
WATCH_SECONDS = 60
POLL_INTERVAL = 0.5

print(f"\n[MONITOR] Watching startup log for {WATCH_SECONDS}s...")
start = time.time()
found = set()
lines_seen = 0
exit_early = False

while time.time() - start < WATCH_SECONDS:
    elapsed = int(time.time() - start)

    # Check if process exited immediately (port lock failure)
    ret = proc.poll()
    if ret is not None:
        print(f"\n[ERROR] Process exited with code {ret} at {elapsed}s")
        break

    try:
        with open(log, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
        new_lines = all_lines[lines_seen:]
        for line in new_lines:
            line = line.rstrip()
            if line:
                print(f"  [{elapsed:2d}s] {line}")
            for tag in REQUIRED_TAGS:
                if tag in line:
                    found.add(tag)
            # Detect port failure
            if "Failed to acquire service lock" in line:
                print(f"\n[ERROR] Port lock failed — another HESA still running!")
                exit_early = True
                break
        lines_seen = len(all_lines)
    except Exception as e:
        print(f"  Log read error: {e}")

    if exit_early:
        break

    # Early exit if all tags found
    if found == set(REQUIRED_TAGS):
        print(f"\n[OK] All [VOICE] stage tags detected after {elapsed}s!")
        break

    time.sleep(POLL_INTERVAL)

# ── Step 5: Check heartbeats ─────────────────────────────────────────────────
hb_status = []
if os.path.exists(hb_dir):
    for hbf in sorted(os.listdir(hb_dir)):
        fp = os.path.join(hb_dir, hbf)
        try:
            age = time.time() - os.path.getmtime(fp)
            status = "ONLINE (fresh)" if age < 15 else f"STALE ({age:.0f}s old)"
            hb_status.append((hbf.replace(".json",""), status))
        except Exception:
            pass

# ── Step 6: Terminate HESA ───────────────────────────────────────────────────
if proc.poll() is None:
    print(f"\n[STOP] Terminating HESA (PID {proc.pid})...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()

# ── Step 7: Final Report ─────────────────────────────────────────────────────
print("\n" + "="*60)
print("STEP 2: REAL LAUNCH STAGE LOG REPORT")
print("="*60)
for tag in REQUIRED_TAGS:
    status = "FOUND   [OK]" if tag in found else "MISSING [FAIL]"
    print(f"  {status}  {tag}")

print()
print("STEP 3: HEARTBEAT STATUS (GUI Modules Tab)")
print("-"*60)
if hb_status:
    for name, status in hb_status:
        print(f"  {name:35s}  {status}")
else:
    print("  No heartbeat files found")

print()
missing = set(REQUIRED_TAGS) - found
if not missing and not exit_early:
    print("OVERALL: PASS — All [VOICE] stages confirmed in real launch")
else:
    if exit_early:
        print("OVERALL: BLOCKED — Port lock still held. Try again after 30s.")
    else:
        print(f"OVERALL: PARTIAL — Missing: {list(missing)}")
print("="*60)
sys.exit(0 if (not missing and not exit_early) else 1)
