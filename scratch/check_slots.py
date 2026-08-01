import inspect
import sys
import os

root_dir = r"c:\Users\veera\OneDrive\Desktop\Open.Jarvis-main"
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Import qml_bridge
from JARVIS.gui.qml_bridge import JarvisBridge

bridge = JarvisBridge()

slots_to_check = [
    "clearAgentLog",
    "getAgentLog",
    "getDatasetStats",
    "getPlaygroundResponse",
    "previewDataset",
    "runAgentTask",
    "setAgentsEnabled",
    "startMLTraining",
    "switchActiveModel"
]

print("Checking slots in JarvisBridge:")
for slot in slots_to_check:
    has_attr = hasattr(bridge, slot)
    is_callable = callable(getattr(bridge, slot, None)) if has_attr else False
    print(f"  {slot}: {'EXISTS' if has_attr and is_callable else 'MISSING'}")
