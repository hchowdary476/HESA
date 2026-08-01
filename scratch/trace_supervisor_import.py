"""Run the actual supervisor module but with crash-catching wrapper.
This mimics exactly what `pythonw -m JARVIS.services.supervisor` does,
but catches any crash and writes it to a log file."""
import sys, os, traceback

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(_root)
sys.path.insert(0, _root)

_log_path = os.path.join("logs", "_supervisor_crash_trace.log")
os.makedirs("logs", exist_ok=True)

# Redirect stdout/stderr to files so pythonw output is captured
_out = open(os.path.join("logs", "_supervisor_stdout.log"), "w", encoding="utf-8")
_err = open(os.path.join("logs", "_supervisor_stderr.log"), "w", encoding="utf-8")
sys.stdout = _out
sys.stderr = _err

with open(_log_path, "w", encoding="utf-8") as log:
    log.write(f"=== SUPERVISOR CRASH TRACE (pid={os.getpid()}) ===\n")
    log.write(f"sys.executable = {sys.executable}\n")
    log.write(f"cwd = {os.getcwd()}\n\n")
    log.flush()

    try:
        log.write(">>> Importing JARVIS.services.supervisor...\n")
        log.flush()
        import JARVIS.services.supervisor
        log.write(">>> Module imported successfully.\n")
        log.flush()
        
        # The __main__ block won't run because __name__ != "__main__"
        # So we manually run its code:
        log.write(">>> Running __main__ equivalent...\n")
        log.flush()
        
        # Step 1: stale process killer
        log.write(">>> Step 1: Stale process killer...\n")
        log.flush()
        import psutil as _psu
        _self_pid = os.getpid()
        _killed = []
        for _proc in _psu.process_iter(['pid', 'name', 'cmdline']):
            try:
                if _proc.pid == _self_pid:
                    continue
                _cmdline = " ".join(_proc.info.get('cmdline') or []).lower()
                if "jarvis.services.supervisor" in _cmdline or (
                    "supervisor.py" in _cmdline and "jarvis" in _cmdline
                ):
                    log.write(f"  Would kill PID {_proc.pid}: {_cmdline[:80]}\n")
                    _killed.append(_proc.pid)
            except Exception:
                pass
        log.write(f"  Stale process scan complete. Matched: {_killed}\n")
        log.flush()
        
        # Step 2: Port lock
        log.write(">>> Step 2: Port lock...\n")
        log.flush()
        import time
        from JARVIS.core.system.utils.port_manager import PortManager
        lock_socket = PortManager.acquire_service_lock("supervisor", 19100)
        log.write(f"  Lock result: {lock_socket}\n")
        log.flush()
        
        if lock_socket is None:
            log.write("  !!! LOCK FAILED — this is the bug !!!\n")
            # Check who holds the port
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2)
                s.connect(("127.0.0.1", 19100))
                log.write("  Port 19100 is actively listening (someone else holds it)\n")
                s.close()
            except ConnectionRefusedError:
                log.write("  Port 19100: connection refused (bound but not accepting)\n")
            except TimeoutError:
                log.write("  Port 19100: connection timed out\n")
            except Exception as e:
                log.write(f"  Port 19100 probe: {e}\n")
        else:
            lock_socket.close()
            log.write("  Lock acquired and released OK\n")

        log.write(">>> ALL STEPS COMPLETED <<<\n")

    except SystemExit as e:
        log.write(f"\n!!! SystemExit: {e}\n")
        log.write(traceback.format_exc())
    except Exception as e:
        log.write(f"\n!!! EXCEPTION: {e}\n")
        log.write(traceback.format_exc())

_out.close()
_err.close()
