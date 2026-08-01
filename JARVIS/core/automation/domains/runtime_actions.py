"""Runtime and desktop actions."""

from __future__ import annotations

import datetime
import os
import time
import webbrowser

import psutil
import pyautogui
import pyperclip

from JARVIS.core.system.observability import record_runtime_event
from JARVIS.core.ai_router.url_safety import build_google_search_url, normalize_web_url
from JARVIS.runtime.process_runner import launch_process, run_command
from JARVIS.runtime.runtime_safety import block_message, is_destructive_action, is_destructive_action_allowed
from JARVIS.core.security.jarvis_admin import format_actionable_message

APPLICATIONS = {
    "chrome": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ],
    "steam": [
        r"C:\Program Files (x86)\Steam\steam.exe",
        r"C:\Program Files\Steam\steam.exe",
    ],
    "epic": [
        r"C:\Program Files\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe",
    ],
    "spotify": [
        os.path.join(os.environ.get("APPDATA", ""), r"Spotify\Spotify.exe"),
    ],
    "discord": [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Discord\Update.exe"),
        os.path.join(os.environ.get("APPDATA", ""), r"Discord\Discord.exe"),
    ],
    "vscode": [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Programs\Microsoft VS Code\Code.exe"),
        r"C:\Program Files\Microsoft VS Code\Code.exe",
    ],
    "word": [r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE"],
    "excel": [r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE"],
    "powerpoint": [r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE"],
    "paint": ["mspaint.exe"],
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "explorer": ["explorer.exe"],
    "taskmgr": ["taskmgr.exe"],
    "cmd": ["cmd.exe"],
    "whatsapp": [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"WhatsApp\WhatsApp.exe"),
    ],
}

DEFAULT_CPU_SAMPLE_INTERVAL = 0.1
LOCAL_SUMMARY_SENTENCE_LIMIT = 2


def env_float(name: str, default: float, minimum: float = 0.0) -> float:
    """Read a bounded float from the environment."""

    try:
        return max(minimum, float(os.getenv(name, default)))
    except ValueError:
        return default


def cpu_sample_interval() -> float:
    """Return a fast, configurable CPU sampling interval."""

    return env_float("JARVIS_CPU_SAMPLE_INTERVAL", DEFAULT_CPU_SAMPLE_INTERVAL)


def app_launch_delay() -> float:
    """Return a short post-launch pause for apps that need startup time."""

    return env_float("JARVIS_APP_LAUNCH_DELAY", 0.2)


def desktop_action_delay(name: str, default: float) -> float:
    """Return a configurable delay for desktop actions."""

    return env_float(name, default)


def summarize_text_locally(text: str, sentence_limit: int = LOCAL_SUMMARY_SENTENCE_LIMIT) -> str | None:
    """Return a small extractive summary without a cloud provider."""

    clean_text = " ".join((text or "").split())
    if not clean_text:
        return None
    sentences = [part.strip() for part in clean_text.replace("?", ".").replace("!", ".").split(".") if part.strip()]
    if not sentences:
        return clean_text[:400]
    summary = ". ".join(sentences[: max(1, sentence_limit)])
    return summary + ("." if not summary.endswith(".") else "")


def launch_app(app_name: str, *, speak, logger) -> bool:
    """Find and launch an application."""

    if app_name.lower() == "whatsapp":
        try:
            # WhatsApp is commonly installed as a Microsoft Store UWP app on Windows.
            # We first try to launch via the registered protocol handler.
            webbrowser.open("whatsapp:")
            record_runtime_event("app_launch", "launched whatsapp via UWP protocol", "info", {"path": "whatsapp:"})
            return True
        except Exception as e:
            logger.warning("Failed to launch WhatsApp via UWP protocol: %s", e)

    if app_name.lower() == "settings":
        try:
            # Settings app on Windows has a registered ms-settings protocol.
            webbrowser.open("ms-settings:")
            record_runtime_event("app_launch", "launched settings via ms-settings protocol", "info", {"path": "ms-settings:"})
            return True
        except Exception as e:
            logger.warning("Failed to launch Settings via protocol: %s", e)

    import shutil
    paths = APPLICATIONS.get(app_name.lower(), [app_name])
    for path in paths:
        if os.path.exists(path) or shutil.which(path):
            launch_process([path])
            record_runtime_event("app_launch", f"launched {app_name}", "info", {"path": path})
            return True
    try:
        launch_process([app_name])
        record_runtime_event("app_launch", f"launched {app_name}", "info", {"path": app_name})
        return True
    except OSError as exc:
        logger.exception("Failed to launch app %s: %s", app_name, exc)
        record_runtime_event("app_launch_error", f"failed {app_name}", "warning", {"error": str(exc)})
        speak(
            format_actionable_message(
                f"I couldn't locate {app_name}, sir.",
                "The executable path was not found or Windows blocked the launch.",
                "Install the app, or provide the full executable path in APPLICATIONS.",
            )
        )
        return False


def handle_runtime_action(action: str, params: dict, context: dict) -> bool | None:
    """Handle desktop and system actions."""

    speak = context["speak"]
    logger = context["logger"]
    summarize_text = context.get("summarize_text")

    if is_destructive_action(action) and not is_destructive_action_allowed():
        logger.warning("Blocked destructive runtime action: %s", action)
        record_runtime_event("runtime_action_blocked", f"blocked {action}", "warning", {"action": action})
        speak(block_message(action))
        return False

    if action == "open_app":
        launch_app(params.get("app", ""), speak=speak, logger=logger)
        delay = app_launch_delay()
        if delay:
            time.sleep(delay)
        return True

    if action == "open_web":
        url = normalize_web_url(params.get("url", ""))
        if not url:
            speak("I blocked that URL, sir. Reason: only http and https browser links are allowed.")
            record_runtime_event("url_blocked", "blocked unsafe URL", "warning", {"action": action})
            return False
        webbrowser.open(url)
        return True

    if action == "search_google":
        webbrowser.open(build_google_search_url(params.get("query", "")))
        return True

    if action == "get_time":
        now = datetime.datetime.now().strftime("%H:%M")
        speak(f"The current time is {now}, sir.")
        return True

    if action == "get_date":
        today = datetime.datetime.now()
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        months = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        speak(f"Today is {days[today.weekday()]}, {months[today.month - 1]} {today.day}, {today.year}.")
        return True

    if action == "get_battery":
        battery = psutil.sensors_battery()
        if battery:
            status = "charging" if battery.power_plugged else "on battery"
            speak(f"Battery is at {int(battery.percent)} percent and {status}, sir.")
        else:
            speak("No battery detected, sir.")
        return True

    if action == "get_ram":
        ram = psutil.virtual_memory()
        speak(
            f"Memory usage is at {ram.percent} percent. "
            f"{round(ram.used / 1024**3, 1)} of {round(ram.total / 1024**3, 1)} gigabytes in use, sir."
        )
        return True

    if action == "get_cpu":
        cpu = psutil.cpu_percent(interval=cpu_sample_interval())
        speak(f"CPU usage is at {cpu} percent, sir.")
        return True

    if action == "screenshot":
        folder = os.path.join(os.environ.get("USERPROFILE", ""), "Pictures")
        os.makedirs(folder, exist_ok=True)
        file_path = os.path.join(folder, f"jarvis_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        delay = desktop_action_delay("JARVIS_SCREENSHOT_DELAY", 0.2)
        if delay:
            time.sleep(delay)
        screenshot = pyautogui.screenshot()
        screenshot.save(file_path)
        speak("Screenshot saved to your Pictures folder, sir.")
        launch_process(["explorer", f"/select,{file_path}"])
        return True

    if action == "read_clipboard":
        try:
            text = pyperclip.paste()
            if text and text.strip():
                if len(text) > 800:
                    speak("The text is quite long, sir. Reading the first portion.")
                    text = text[:800]
                speak(text)
            else:
                speak("The clipboard is empty, sir.")
        except (OSError, RuntimeError, pyperclip.PyperclipException) as exc:
            logger.exception("Clipboard read failed: %s", exc)
            speak("I couldn't read the clipboard, sir.")
        return True

    if action == "summarize_clipboard":
        try:
            text = pyperclip.paste()
            if text and text.strip():
                summary = summarize_text(text) if callable(summarize_text) else None
                speak(summary or summarize_text_locally(text) or "I had trouble summarizing that, sir.")
            else:
                speak("The clipboard is empty, sir.")
        except (OSError, RuntimeError, pyperclip.PyperclipException) as exc:
            logger.exception("Clipboard summarization failed: %s", exc)
            speak("I couldn't access the clipboard, sir.")
        return True

    if action == "type_text":
        text = params.get("text", "")
        if text:
            delay = desktop_action_delay("JARVIS_TYPE_DELAY", 0.1)
            if delay:
                time.sleep(delay)
            pyautogui.typewrite(text, interval=0.05)
        return True

    if action == "press_key":
        key = params.get("key", "")
        if key:
            if "+" in key:
                pyautogui.hotkey(*key.split("+"))
            else:
                pyautogui.press(key)
        return True

    if action == "mouse_click":
        x = params.get("x", 0)
        y = params.get("y", 0)
        button = params.get("button", "left")
        if button == "double":
            pyautogui.doubleClick(x, y)
        else:
            pyautogui.click(x, y, button=button)
        return True

    if action == "scroll":
        direction = params.get("direction", "down")
        amount = params.get("amount", 3)
        pyautogui.scroll(amount if direction == "up" else -amount)
        return True

    if action == "minimize_all":
        pyautogui.hotkey("win", "d")
        return True

    if action == "maximize_window":
        pyautogui.hotkey("win", "up")
        return True

    if action == "close_window":
        pyautogui.hotkey("alt", "f4")
        return True

    if action == "lock_screen":
        run_command(["rundll32.exe", "user32.dll,LockWorkStation"])
        return True

    if action == "face_match":
        from JARVIS.core.security.security_shield import run_face_match_check
        run_face_match_check(app=context.get("app"))
        return True

    if action == "sleep":
        delay = desktop_action_delay("JARVIS_SLEEP_ACTION_DELAY", 1.0)
        if delay:
            time.sleep(delay)
        run_command(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
        return True

    if action == "shutdown":
        run_command(["shutdown", "/s", "/t", "5"], allow_destructive=True)
        return False

    if action == "restart":
        run_command(["shutdown", "/r", "/t", "5"], allow_destructive=True)
        return False

    if action == "close_app":
        app_name = params.get("app", "")
        if not app_name:
            return False
        target = app_name.lower()
        closed = False
        for proc in psutil.process_iter(['name']):
            try:
                if target in proc.info['name'].lower():
                    proc.terminate()
                    closed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        if closed:
            speak(f"I have terminated {app_name}, sir.")
        else:
            speak(f"I couldn't find any running instances of {app_name}, sir.")
        return True

    if action == "switch_window":
        pyautogui.hotkey("alt", "tab")
        return True

    if action == "search_files":
        query = params.get("query", "")
        if not query:
            return False
        import glob
        search_dirs = [
            os.path.join(os.path.expanduser("~"), "Desktop"),
            os.path.join(os.path.expanduser("~"), "Documents"),
            os.path.join(os.path.expanduser("~"), "Downloads"),
            os.getcwd()
        ]
        results = []
        for s_dir in search_dirs:
            if not os.path.exists(s_dir):
                continue
            for root, dirs, files in os.walk(s_dir):
                for file in files:
                    if query.lower() in file.lower():
                        full_path = os.path.join(root, file)
                        results.append(full_path)
                        if len(results) >= 5:
                            break
                if len(results) >= 5:
                    break
        if results:
            best_match = results[0]
            speak(f"I found some matches, sir. Opening the most relevant one: {os.path.basename(best_match)}.")
            try:
                os.startfile(best_match)
            except Exception as e:
                logger.error(f"Failed to start file: {e}")
                speak("I couldn't open the file, sir. Access was denied.")
        else:
            speak(f"I searched common directories but couldn't find any files matching '{query}', sir.")
        return True

    if action == "control_volume":
        sub_act = params.get("action", "")
        if sub_act == "mute":
            pyautogui.press("volumemute")
            return True
        if sub_act == "unmute":
            pyautogui.press("volumemute")
            return True
        if sub_act == "up":
            for _ in range(5):
                pyautogui.press("volumeup")
            return True
        if sub_act == "down":
            for _ in range(5):
                pyautogui.press("volumedown")
            return True
        if sub_act == "set":
            level = params.get("level", 50)
            for _ in range(50):
                pyautogui.press("volumedown")
            presses = int(level / 2)
            for _ in range(presses):
                pyautogui.press("volumeup")
            speak(f"Volume adjusted to {level} percent, sir.")
            return True

    if action == "control_brightness":
        level = params.get("level")
        sub_act = params.get("action", "")
        target_level = level
        if sub_act == "up":
            target_level = 80
        elif sub_act == "down":
            target_level = 30
        if target_level is not None:
            target_level = max(0, min(100, int(target_level)))
            cmd = f'powershell -Command "Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods | Invoke-CimMethod -MethodName WmiSetBrightness -Arguments @{{ Timeout = 0; Brightness = {target_level} }}"'
            try:
                os.system(cmd)
                speak(f"Brightness adjusted to {target_level} percent, sir.")
            except Exception as e:
                logger.error(f"Failed to set brightness: {e}")
                speak("Failed to adjust display brightness, sir.")
        return True

    if action == "control_wifi":
        sub_act = params.get("action", "")
        admin_state = "enabled" if sub_act == "enable" else "disabled"
        cmd = f'netsh interface set interface name="Wi-Fi" admin={admin_state}'
        try:
            os.system(cmd)
            speak(f"Wi-Fi interface has been {sub_act}d, sir.")
        except Exception as e:
            logger.error(f"Failed to toggle wifi: {e}")
            webbrowser.open("ms-settings:network-wifi")
            speak("I opened the network settings page for you, sir.")
        return True

    if action == "control_bluetooth":
        sub_act = params.get("action", "")
        try:
            webbrowser.open("ms-settings:bluetooth")
            speak(f"I have opened the Bluetooth configuration pane, sir.")
        except Exception as e:
            logger.error(f"Failed to toggle bluetooth: {e}")
        return True

    if action == "control_media":
        sub_act = params.get("action", "")
        if sub_act == "play_pause":
            pyautogui.press("playpause")
        elif sub_act == "next":
            pyautogui.press("nexttrack")
        elif sub_act == "prev":
            pyautogui.press("prevtrack")
        elif sub_act == "stop":
            pyautogui.press("stop")
        return True

    if action == "get_hardware_stats":
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('C:').percent
        net_prev = psutil.net_io_counters()
        time.sleep(0.1)
        net_curr = psutil.net_io_counters()
        sent_kb = (net_curr.bytes_sent - net_prev.bytes_sent) / 1024 / 0.1
        recv_kb = (net_curr.bytes_recv - net_prev.bytes_recv) / 1024 / 0.1
        report = (
            f"Here is your system health report, sir. "
            f"CPU usage is currently at {int(cpu)} percent. "
            f"System memory is utilizing {int(ram)} percent. "
            f"Primary storage disk C is at {int(disk)} percent capacity. "
            f"Network bandwidth shows upload at {sent_kb:.1f} kilobytes per second, "
            f"and download at {recv_kb:.1f} kilobytes per second."
        )
        speak(report)
        return True

    if action == "register_startup":
        enabled = params.get("enabled", True)
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "JarvisCyberInterface"
            cmd = f'"{sys.executable}" -m JARVIS.services.supervisor'
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE) as key:
                if enabled:
                    winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
                    speak("HESA has been registered to run automatically on system boot, sir.")
                else:
                    try:
                        winreg.DeleteValue(key, app_name)
                        speak("HESA has been removed from Windows startup items, sir.")
                    except FileNotFoundError:
                        speak("HESA was not registered as a startup item, sir.")
        except Exception as e:
            logger.error(f"Startup registration error: {e}")
            speak("Failed to modify Windows startup registration, sir.")
        return True

    if action == "run_system_diagnostics":
        try:
            from JARVIS.runtime.diagnostics import SystemDiagnosticsManager
            import json
            mgr = SystemDiagnosticsManager()
            data = mgr.run_health_scan()
            diag_path = os.path.join("logs", "diagnostics_results.json")
            os.makedirs("logs", exist_ok=True)
            with open(diag_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            scores = data["scores"]
            speak(
                f"Diagnostics completed, sir. "
                f"Health score is {scores['health']}. "
                f"Performance score is {scores['performance']}. "
                f"Security score is {scores['security']}. "
                f"Stability score is {scores['stability']}. "
                f"I have updated the diagnostics cockpit."
            )
        except Exception as e:
            logger.error(f"Diagnostics action error: {e}")
            speak("Failed to execute complete diagnostics scan, sir.")
        return True

    if action == "run_safe_repairs":
        try:
            from JARVIS.runtime.diagnostics import SystemDiagnosticsManager
            import json
            mgr = SystemDiagnosticsManager()
            reports = []
            for repair_id in ["clear_temp", "flush_dns", "optimize_memory"]:
                rep = mgr.execute_safe_repair(repair_id)
                reports.append(rep)
            rep_path = os.path.join("logs", "repair_reports.json")
            os.makedirs("logs", exist_ok=True)
            with open(rep_path, "w", encoding="utf-8") as f:
                json.dump(reports, f)
            speak("Safe system repairs complete, sir. DNS flushed, temporary files cleaned, and active memory optimized.")
        except Exception as e:
            logger.error(f"Safe repairs action error: {e}")
            speak("Failed to complete system repairs, sir.")
        return True

    if action == "request_protected_action":
        action_id = params.get("action_id", "")
        explanation = params.get("explanation", "")
        components = params.get("components", "")
        try:
            import json
            req_path = os.path.join("logs", "protected_action_request.json")
            os.makedirs("logs", exist_ok=True)
            with open(req_path, "w", encoding="utf-8") as f:
                json.dump({"action_id": action_id, "explanation": explanation, "components": components}, f)
            speak("This action requires verification, sir. Please review the dashboard prompt.")
        except Exception:
            speak("I was unable to queue the protected action verification request, sir.")
    if action == "talk":
        return True

    return None

