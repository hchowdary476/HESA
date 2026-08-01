import os

datasets_dir = r"c:\Users\veera\OneDrive\Desktop\Open.Jarvis-main\logs\datasets"
if os.path.exists(datasets_dir):
    print(f"Contents of {datasets_dir}:")
    for f in os.listdir(datasets_dir):
        fp = os.path.join(datasets_dir, f)
        print(f"  {f}: {os.path.getsize(fp)} bytes")
else:
    print(f"Directory {datasets_dir} does not exist.")
