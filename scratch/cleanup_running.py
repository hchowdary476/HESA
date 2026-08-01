import os
import psutil

my_pid = os.getpid()
parent_pid = os.getppid()

print("Scanning for existing HESA/JARVIS processes:")
count = 0
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        pid = proc.info.get('pid')
        if pid in (my_pid, parent_pid):
            continue
        cmd = proc.info.get('cmdline')
        if cmd and any("jarvis.py" in str(c).lower() or "supervisor" in str(c).lower() for c in cmd):
            print(f"  PID {pid}: {proc.name()}")
            try:
                proc.kill()
                count += 1
            except Exception as ex:
                print(f"    Failed to kill: {ex}")
    except Exception:
        pass

print(f"Cleaned up {count} processes.")
