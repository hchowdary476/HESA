import subprocess
import sys
import os

python_exe = r"C:\Users\veera\OneDrive\Desktop\Open.Jarvis-main\.venv\Scripts\python.exe"
main_script = r"C:\Users\veera\OneDrive\Desktop\Open.Jarvis-main\jarvis.py"

env = os.environ.copy()
env["PYTHONPATH"] = r"C:\Users\veera\OneDrive\Desktop\Open.Jarvis-main" + os.pathsep + env.get("PYTHONPATH", "")

print("Spawning subprocess...")
process = subprocess.Popen(
    [python_exe, main_script],
    cwd=r"C:\Users\veera\OneDrive\Desktop\Open.Jarvis-main",
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

print("Waiting for subprocess...")
stdout, stderr = process.communicate()

print("Subprocess exited with code:", process.returncode)
print("STDOUT:")
print(stdout)
print("STDERR:")
print(stderr)
