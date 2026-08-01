import time
import json
import cProfile
import pstats
import io
from JARVIS.gui.ui_smoke import run_ui_smoke

pr = cProfile.Profile()
pr.enable()
t0 = time.time()
try:
    result = run_ui_smoke()
    print(f"Smoke test status: {result['status']}")
except Exception as e:
    print(f"Exception during startup: {e}")
t1 = time.time()
pr.disable()

s = io.StringIO()
ps = pstats.Stats(pr, stream=s).sort_stats('cumtime')
ps.print_stats(50)

with open('startup_profile.txt', 'w') as f:
    f.write(s.getvalue())

print(f'Startup time: {t1-t0}s')

trace_data = {
    "total_startup_seconds": t1-t0,
    "top_functions": []
}

with open("startup_trace.json", "w") as f:
    json.dump(trace_data, f)

print("Profiling complete. See startup_profile.txt")
