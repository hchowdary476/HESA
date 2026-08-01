import sys
import os
import threading
import time

root_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, root_dir)

from JARVIS.gui.main_window import JarvisApp

app = JarvisApp()

def test_clicks():
    time.sleep(2)
    print("Simulating click on 'system' canvas...", flush=True)
    try:
        # Find the system canvas
        system_canvas = None
        for key, (canvas, icon) in app._nav_canvases.items():
            if key == "system":
                system_canvas = canvas
                break
        
        if system_canvas:
            print(f"Found system canvas: {system_canvas}. Generating event.", flush=True)
            # Generate a Button-1 event programmatically!
            system_canvas.event_generate("<Button-1>", x=10, y=10)
        else:
            print("System canvas not found!")
    except Exception as e:
        import traceback; traceback.print_exc()

    time.sleep(2)
    print("Closing app...", flush=True)
    app.after(0, app.destroy)

threading.Thread(target=test_clicks, daemon=True).start()
app.mainloop()
