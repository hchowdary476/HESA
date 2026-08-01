import json
import os
import sys
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

from JARVIS.core.automation.groq_router import analyze_with_groq

# Global cloud state
CLOUD_MEMORY_FILE = os.path.join("logs", "cloud_memory.json")
START_TIME = time.time()


def load_cloud_memory():
    if os.path.exists(CLOUD_MEMORY_FILE):
        try:
            with open(CLOUD_MEMORY_FILE, encoding="utf-8") as f:
                data = json.load(f)
                # Ensure structure exists
                if "preferences" not in data:
                    data["preferences"] = {}
                if "notes" not in data:
                    data["notes"] = []
                if "reminders" not in data:
                    data["reminders"] = []
                if "history" not in data:
                    data["history"] = []
                return data
        except Exception:
            pass
    # Fallback to local memory if possible, otherwise empty default
    local_mem_path = os.path.abspath("memory.json")
    if os.path.exists(local_mem_path):
        try:
            with open(local_mem_path, encoding="utf-8") as f:
                data = json.load(f)
                if "reminders" not in data:
                    data["reminders"] = []
                if "history" not in data:
                    data["history"] = []
                return data
        except Exception:
            pass

    return {
        "preferences": {"preferred_language": "telugu", "language_mode": "telugu", "wake_word": "jarvis", "recovery_pin": "1234"},
        "notes": [],
        "reminders": [],
        "history": [],
    }


def save_cloud_memory(data):
    os.makedirs(os.path.dirname(CLOUD_MEMORY_FILE), exist_ok=True)
    try:
        with open(CLOUD_MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


class CloudContinuityHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Prevent spamming stdout
        pass

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        # Return 404 for all GET requests as companion UI and metrics are removed
        self.send_json({"error": "Not Found"}, 404)

    def do_POST(self):
        url_parsed = urllib.parse.urlparse(self.path)
        path = url_parsed.path

        # Read JSON body
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = b""
        if content_length > 0:
            post_data = self.rfile.read(content_length)

        try:
            body = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            self.send_json({"error": "Invalid JSON payload"}, 400)
            return

        if not self.check_auth():
            self.send_json({"error": "Unauthorized"}, 401)
            return

        if path == "/api/chat":
            command = body.get("command", "")
            if not command:
                self.send_json({"error": "Command is required"}, 400)
                return

            try:
                # Intercept some cloud queries directly
                mem = load_cloud_memory()
                # Run the standard analyze_with_groq command router
                action = analyze_with_groq(command)
                response_text = action.get("response", "I could not process that, sir.")

                # Append to cloud history
                history = mem.get("history", [])
                history.append({"user": command, "jarvis": response_text, "timestamp": time.time()})
                if len(history) > 50:
                    history = history[-50:]
                mem["history"] = history
                save_cloud_memory(mem)

                self.send_json({"response": response_text, "action": action.get("action", "talk"), "params": action.get("params", {})})
            except Exception as e:
                self.send_json({"response": f"I encountered an issue processing that on the cloud: {e}"}, 500)
        else:
            self.send_json({"error": "Not Found"}, 404)

    def check_auth(self):
        auth_header = self.headers.get("Authorization")
        if auth_header == "Bearer session_ok":
            return True
        return False

    def send_json(self, data, code=200):
        try:
            res_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(res_bytes)
        except Exception:
            pass


def start_cloud_server(port=8008):
    server = HTTPServer(("0.0.0.0", port), CloudContinuityHandler)
    print(f"[CLOUD CONTROLLER] Cloud Continuity Server online at http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8008
    start_cloud_server(port)
