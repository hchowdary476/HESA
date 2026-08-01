import time
import threading
import webview
from PySide6.QtWidgets import QApplication, QLabel

class SplashAPI:
    def __init__(self):
        self.logs = []
        self.completed = False

    def get_boot_logs(self):
        return self.logs

    def quick_action(self, action):
        print(f"Quick action clicked: {action}")

    def send_command(self, cmd):
        return f"Reply to: {cmd}"

def load_services_mock(api, window):
    # Mocking service loading
    services = ["ai_router", "memory_engine", "voice_engine", "automation_engine"]
    for svc in services:
        time.sleep(1)
        api.logs.append({"message": f"[BOOT] Starting {svc.replace('_', ' ').title()}...", "kind": "info"})
        print(f"Mock loaded: {svc}")
    
    time.sleep(1)
    api.logs.append({"message": "System healthy. Ready.", "kind": "success"})
    time.sleep(1)
    
    # Close window
    window.destroy()

def test_flow():
    api = SplashAPI()
    window = webview.create_window(
        "HESA OS Boot Sequence",
        "JARVIS/gui/jarvis_os/jarvis_os.html",
        js_api=api,
        width=850,
        height=600,
        resizable=False,
        frameless=True
    )
    
    # Start thread to load services
    t = threading.Thread(target=load_services_mock, args=(api, window), daemon=True)
    t.start()
    
    # Run pywebview event loop
    webview.start()
    
    # Now start PySide6 QApplication
    print("Starting PySide6...")
    app = QApplication([])
    lbl = QLabel("Main Dashboard QML Simulation")
    lbl.show()
    app.exec()

if __name__ == "__main__":
    test_flow()
