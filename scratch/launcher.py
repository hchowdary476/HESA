"""
launcher.py — launch jarvis.py via pythonw.exe and watch the log.
Uses a single open file handle for both stdout and stderr (same fd).
"""
import os, sys, subprocess, time, socket

root = r"c:\Users\veera\OneDrive\Desktop\Open.Jarvis-main"
pythonw = os.path.join(root, ".venv", "Scripts", "pythonw.exe")
main = os.path.join(root, "jarvis.py")
log_path = os.path.join(root, "logs", "_real_launch.log")
hb_dir = os.path.join(root, "logs", "heartbeats")
lock_port = 19106

os.makedirs(os.path.join(root, "logs"), exist_ok=True)

# ── 1. Kill stale python processes ────────────────────────────────────────────
import psutil
my_pid = os.getpid()
killed = []
for proc in psutil.process_iter(['pid', 'name']):
    try:
        if proc.pid == my_pid: continue
        if 'python' in (proc.info.get('name') or '').lower():
            proc.kill()
            killed.append(proc.pid)
    except Exception:
        pass

if killed:
    print(f"[CLEAN] Killed PIDs: {killed}")
    time.sleep(3)   # let OS release port

# ── 2. Wait for port to be free ───────────────────────────────────────────────
print(f"[WAIT] Checking port {lock_port}...")
for i in range(20):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", lock_port))
        s.close()
        print(f"[WAIT] Port {lock_port} free (checked {i}s)")
        break
    except OSError:
        print(f"[WAIT]  {i}s: port busy...")
        time.sleep(1)

# ── 3. Launch via pythonw.exe ─────────────────────────────────────────────────
env = os.environ.copy()
env["PYTHONPATH"] = root

with open(log_path, "w", encoding="utf-8") as log_f:
    log_f.write(f"=== HESA Real Launch via pythonw.exe ===\n")
    log_f.write(f"Launched: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    log_f.write(f"pythonw: {pythonw}\n\n")

# Open single file handle for both stdout AND stderr
log_fh = open(log_path, "a", encoding="utf-8")
proc = subprocess.Popen(
    [pythonw, main],
    cwd=root,
    env=env,
    stdout=log_fh,
    stderr=log_fh,   # same fd — this is valid for Popen (unlike Start-Process)
)
print(f"[LAUNCH] PID: {proc.pid}")

# ── 4. Monitor log ────────────────────────────────────────────────────────────
REQUIRED = [
    "[VOICE] ENGINE STARTED",
    "[VOICE] WAKE THREAD CREATED",
    "[VOICE] WAKE LOOP ENTERED",
    "[VOICE] MIC STARTED",
]
found = set()
lines_seen = 0
start = time.time()
WATCH = 50

print(f"[MONITOR] Watching log for {WATCH}s (PID {proc.pid})...\n")

while time.time() - start < WATCH:
    elapsed = int(time.time() - start)
    ret = proc.poll()
    if ret is not None:
        print(f"\n[!] Process exited at {elapsed}s with code {ret}")
        break

    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        new = lines[lines_seen:]
        for ln in new:
            ln = ln.rstrip()
            if ln:
                print(f"  [{elapsed:2d}s] {ln}")
            for tag in REQUIRED:
                if tag in ln:
                    found.add(tag)
            if "Failed to acquire service lock" in ln:
                print("\n[!] Port lock still held — aborting")
                proc.terminate()
                sys.exit(1)
        lines_seen = len(lines)
    except Exception:
        pass

    if found == set(REQUIRED):
        print(f"\n[OK] All [VOICE] stage tags found after {elapsed}s!")
        break

    time.sleep(0.5)

# ── 5. Heartbeat status ───────────────────────────────────────────────────────
hb_rows = []
if os.path.exists(hb_dir):
    for hbf in sorted(os.listdir(hb_dir)):
        fp = os.path.join(hb_dir, hbf)
        try:
            age = time.time() - os.path.getmtime(fp)
            online = age < 15
            hb_rows.append((hbf.replace(".json",""), online, age))
        except Exception:
            pass

# ── 6. Terminate ──────────────────────────────────────────────────────────────
log_fh.close()
if proc.poll() is None:
    proc.terminate()
    try: proc.wait(timeout=5)
    except Exception: proc.kill()

# ── 7. Report ─────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("STEP 2 — REAL LAUNCH [VOICE] STAGE REPORT")
print("="*60)
for tag in REQUIRED:
    ok = tag in found
    print(f"  {'FOUND [OK]  ' if ok else 'MISSING [!!]'}  {tag}")

print()
print("STEP 3 — HEARTBEAT STATUS (GUI Modules tab)")
print("-"*60)
if hb_rows:
    for name, online, age in hb_rows:
        mark = "ONLINE (fresh)" if online else f"STALE  ({age:.0f}s old)"
        print(f"  {name:35s}  {mark}")
else:
    print("  No heartbeat files found")

print()
missing = set(REQUIRED) - found
if not missing:
    print("RESULT: PASS — All [VOICE] stages confirmed in real pythonw.exe launch")
    sys.exit(0)
else:
    print(f"RESULT: FAIL — Missing stages: {list(missing)}")
    sys.exit(1)
