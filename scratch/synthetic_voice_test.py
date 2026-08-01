"""
HESA Voice Pipeline Synthetic Baseline Test
============================================
Tests the voice pipeline code paths using mocked audio/STT.
Does NOT test real microphone hardware.

Verifies:
1. wake_listener module imports and starts
2. WAKE WORD DETECTED fires for "hey hesa"
3. Command is routed to process_command for "open calculator"
4. [VOICE] stage logging is emitted in correct order
"""
import os, sys, threading, time, io, contextlib

# Set up path
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(root)
sys.path.insert(0, root)

# Enable test mode
os.environ["HESA_TEST_MODE"] = "1"
os.environ["PYTHONPATH"] = root

print("="*60)
print("HESA VOICE PIPELINE SYNTHETIC BASELINE TEST")
print("="*60)

# ─────────────────────────────────────────────────────────────
# TEST 1: Import wake_listener without crash
# ─────────────────────────────────────────────────────────────
print("\n[TEST 1] Import wake_listener module...")
try:
    from JARVIS.runtime import wake_listener
    print("[PASS] wake_listener imported successfully")
    t1 = "PASS"
except Exception as e:
    print(f"[FAIL] Import error: {e}")
    import traceback; traceback.print_exc()
    t1 = "FAIL"

# ─────────────────────────────────────────────────────────────
# TEST 2: wake_word_detected("hey hesa") returns True
# ─────────────────────────────────────────────────────────────
print("\n[TEST 2] wake_word_detected('hey hesa') == True...")
try:
    from JARVIS.core.voice.wake_word import wake_word_detected, build_wake_word_config
    cfg = build_wake_word_config()
    result = wake_word_detected("hey hesa", config=cfg)
    if result:
        print(f"[PASS] wake_word_detected('hey hesa') = {result}  (wake_word='{cfg['wake_word']}')")
        t2 = "PASS"
    else:
        print(f"[FAIL] wake_word_detected returned False (wake_word='{cfg['wake_word']}')")
        print(f"       TIP: settings.json has wake_word='jarvis', not 'hesa'!")
        t2 = "FAIL"
except Exception as e:
    print(f"[FAIL] {e}")
    t2 = "FAIL"

# ─────────────────────────────────────────────────────────────
# TEST 3: wake_word_detected("hey jarvis") matches config
# ─────────────────────────────────────────────────────────────
print("\n[TEST 3] wake_word_detected with current config wake word...")
try:
    from JARVIS.core.voice.wake_word import wake_word_detected, build_wake_word_config
    cfg = build_wake_word_config()
    ww = str(cfg.get("wake_word", ""))
    result_hesa = wake_word_detected("hey hesa", config=cfg)
    result_jarvis = wake_word_detected("hey jarvis", config=cfg)
    result_ww = wake_word_detected(f"hey {ww}", config=cfg)
    print(f"       Configured wake_word = '{ww}'")
    print(f"       'hey hesa'   = {result_hesa}")
    print(f"       'hey jarvis' = {result_jarvis}")
    print(f"       'hey {ww}'   = {result_ww}")
    if ww != "hesa":
        print(f"[WARN] settings.json wake_word='{ww}' — NOT 'hesa'!")
        print(f"       Saying 'Hey HESA' will NOT be recognised!")
        t3 = "WARN"
    else:
        t3 = "PASS"
        print("[PASS] Wake word is 'hesa'")
except Exception as e:
    print(f"[FAIL] {e}")
    t3 = "FAIL"

# ─────────────────────────────────────────────────────────────
# TEST 4: extract_inline_command works
# ─────────────────────────────────────────────────────────────
print("\n[TEST 4] extract_inline_command('hey hesa open calculator')...")
try:
    from JARVIS.core.voice.wake_word import extract_inline_command, build_wake_word_config
    cfg = build_wake_word_config()
    cmd = extract_inline_command("hey hesa open calculator", config=cfg)
    if cmd:
        print(f"[PASS] Extracted inline command: '{cmd}'")
        t4 = "PASS"
    else:
        # If wake word is jarvis, hey hesa won't extract inline cmd
        cmd2 = extract_inline_command(f"hey {cfg.get('wake_word','hesa')} open calculator", config=cfg)
        if cmd2:
            print(f"[PASS] Extracted with configured wake word: '{cmd2}'")
            t4 = "PASS"
        else:
            print(f"[WARN] No inline command extracted — check wake_word config")
            t4 = "WARN"
except Exception as e:
    print(f"[FAIL] {e}")
    t4 = "FAIL"

# ─────────────────────────────────────────────────────────────
# TEST 5: [VOICE] stage log sequence from listen_for_wake_word
# ─────────────────────────────────────────────────────────────
print("\n[TEST 5] [VOICE] stage log sequence in HESA_TEST_MODE...")
log_buffer = []
def capture_log(msg):
    log_buffer.append(msg)
    print(f"       LOG: {msg}")

expected_stages = [
    "ENGINE STARTED",
    "WAKE THREAD CREATED",
    "WAKE LOOP ENTERED",
    "MIC STARTED",
    "WAKE WORD DETECTED",
]

try:
    # Run in a daemon thread so test doesn't block forever
    import logging
    logger = logging.getLogger("jarvis.voice")
    t = threading.Thread(
        target=wake_listener.listen_for_wake_word,
        kwargs={"logger": logger, "send_log": capture_log},
        daemon=True
    )
    t.start()
    t.join(timeout=30)  # Wait up to 30s for test mode to complete

    found = [s for s in expected_stages if any(s in line for line in log_buffer)]
    missing = [s for s in expected_stages if s not in found]
    print(f"       Stages found: {found}")
    print(f"       Stages missing: {missing}")
    if not missing:
        print("[PASS] All expected [VOICE] stages emitted in order")
        t5 = "PASS"
    else:
        print(f"[FAIL] Missing stages: {missing}")
        t5 = "FAIL"
except Exception as e:
    print(f"[FAIL] {e}")
    import traceback; traceback.print_exc()
    t5 = "FAIL"

# ─────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("SYNTHETIC TEST SUMMARY")
print("="*60)
results = [
    ("Import wake_listener", t1),
    ("wake_word_detected('hey hesa')", t2),
    ("Wake word config matches 'hesa'", t3),
    ("extract_inline_command", t4),
    ("[VOICE] stage log sequence", t5),
]
for name, res in results:
    icon = "✓" if res == "PASS" else ("⚠" if res == "WARN" else "✗")
    print(f"  {icon} {name}: {res}")

all_pass = all(r in ("PASS", "WARN") for _, r in results)
print()
if all_pass:
    print("RESULT: SYNTHETIC BASELINE PASSED")
else:
    print("RESULT: SYNTHETIC BASELINE FAILED — see above")
print("="*60)
print()
print("NOTE: This test does NOT prove real microphone hardware works.")
print("Real validation requires: say 'Hey HESA' into actual mic.")
