import threading

from JARVIS.core.system.utils.service_heartbeat import publish_heartbeat, wrap_service_main
from JARVIS.runtime.jarvis_runtime import start_jarvis


def _start():
    # Start the heartbeat daemon FIRST so it begins writing heartbeat files
    # within ~2s, independently of how long start_jarvis() takes to initialise.
    # Running start_jarvis() in a joined daemon thread means:
    #   - the heartbeat loop is never blocked by slow imports / network calls
    #   - the process stays alive for as long as the voice engine runs
    #   - any unhandled exception in start_jarvis() still propagates via join()
    publish_heartbeat("voice_engine", "voice_engine.json")

    _exc_box = []

    def _run_jarvis():
        try:
            start_jarvis()
        except BaseException as exc:
            _exc_box.append(exc)

    worker = threading.Thread(target=_run_jarvis, daemon=True, name="voice-engine-main")
    worker.start()
    worker.join()

    # Re-raise so wrap_service_main can log it to service_crash.log
    if _exc_box:
        raise _exc_box[0]


if __name__ == "__main__":
    import sys

    from JARVIS.core.system.utils.port_manager import PortManager

    lock_socket = PortManager.acquire_service_lock("voice_service", 19101)
    if lock_socket is None:
        print("[VOICE SERVICE] Duplicate instance detected. Exiting.")
        sys.exit(1)
    try:
        wrap_service_main("voice_engine", _start)
    finally:
        lock_socket.close()
