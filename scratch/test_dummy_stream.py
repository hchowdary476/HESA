import sys

class DummyStream:
    def __init__(self):
        self.encoding = "utf-8"
        self.errors = "replace"
    def write(self, s):
        pass
    def flush(self):
        pass
    def isatty(self):
        return False
    def reconfigure(self, *args, **kwargs):
        pass

# Simulate pythonw.exe environment where stdout/stderr are None
sys.stdout = None
sys.stderr = None

# Apply fix
if sys.stdout is None:
    sys.stdout = DummyStream()
if sys.stderr is None:
    sys.stderr = DummyStream()

# Verify that prints, flushes, and writes no longer crash
try:
    print("Testing stdout print...")
    sys.stdout.flush()
    sys.stderr.write("Testing stderr write...\n")
    sys.stderr.flush()
    print("Success: No crashes occurred!")
except Exception as e:
    print(f"Failed: {e}", file=sys.__stdout__) # use system original stdout if possible
