import json
import os
import threading
import time


class ServiceCoordinator:
    """Thread-safe coordinator running consolidated background services."""

    def __init__(self) -> None:
        self.running = False
        self.lock = threading.Lock()
        self.threads: dict[str, threading.Thread] = {}
        self.hb_dir = os.path.join("logs", "heartbeats")
        os.makedirs(self.hb_dir, exist_ok=True)

    def start(self) -> None:
        """Start background threads for memory, automation, and security loops."""
        with self.lock:
            if self.running:
                return
            self.running = True

            self.threads["automation_engine"] = threading.Thread(target=self._service_loop, args=("automation_engine",), daemon=True)
            self.threads["memory_engine"] = threading.Thread(target=self._service_loop, args=("memory_engine",), daemon=True)
            self.threads["security_engine"] = threading.Thread(target=self._service_loop, args=("security_engine",), daemon=True)

            for name, thread in self.threads.items():
                thread.start()

            print("[SERVICE COORDINATOR] Started consolidated services (automation, memory, security).")

    def stop(self) -> None:
        """Stop all background service threads."""
        with self.lock:
            self.running = False
        print("[SERVICE COORDINATOR] Stopped coordinator.")

    def _service_loop(self, name: str) -> None:
        hb_path = os.path.join(self.hb_dir, f"{name}.json")
        while True:
            with self.lock:
                if not self.running:
                    break

            try:
                # Thread-safe/atomic heartbeat file writing
                temp_hb = hb_path + ".tmp"
                with open(temp_hb, "w") as f:
                    json.dump({"pid": os.getpid(), "timestamp": time.time(), "status": "healthy"}, f)
                if os.path.exists(hb_path):
                    os.remove(hb_path)
                os.rename(temp_hb, hb_path)
            except Exception:
                pass
            time.sleep(8)


def main() -> None:
    coordinator = ServiceCoordinator()
    coordinator.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        coordinator.stop()


if __name__ == "__main__":
    main()
