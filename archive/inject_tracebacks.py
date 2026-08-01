import re
import sys

def inject_tracebacks(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Find `except Exception:\n    pass` and `except Exception as e:\n    pass`
    # We will just replace `except Exception:` followed by `pass` with traceback
    
    # Simple regex to replace `except Exception:\n<whitespace>pass`
    # Also `except:\n<whitespace>pass`
    
    modified_content = re.sub(
        r'(except Exception:|except:)(\s+)pass',
        r'\1\2import traceback; traceback.print_exc()',
        content
    )
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(modified_content)

    print(f"Injected tracebacks into {filepath}")

if __name__ == "__main__":
    inject_tracebacks("JARVIS/ui/arayuz.py")
