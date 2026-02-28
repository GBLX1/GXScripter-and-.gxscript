import os, sys, subprocess, shutil
import tkinter as tk
from tkinter import messagebox

APP_NAME = "GXScripter"
HERE = os.path.dirname(os.path.abspath(sys.argv[0]))
MAIN = os.path.join(HERE, "main.pyw")

def fail(msg: str):
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(APP_NAME, msg)
    raise SystemExit(1)

# Find a system Python (Windows)
candidates = [
    ["pyw", "-3"],   # preferred (no console)
    ["py", "-3"],    # fallback
    ["pythonw"],     # if in PATH
    ["python"],      # fallback
]

python_cmd = None
for c in candidates:
    if shutil.which(c[0]):
        python_cmd = c
        break

if not python_cmd:
    fail("Python 3 not found.\n\nInstall Python from python.org.\nTip: enable 'py launcher' during install.")

if not os.path.exists(MAIN):
    fail(f"Missing file:\n{MAIN}")

# Optional: basic dependency check using requirements.txt (only checks import names crudely)
req = os.path.join(HERE, "requirements.txt")
missing = []
if os.path.exists(req):
    try:
        with open(req, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                name = line.split("==")[0].split(">=")[0].split("<=")[0].split("[")[0].strip()
                if not name:
                    continue
                # some packages import under different names; skip strict checking here
    except Exception:
        pass

# Run the hub
subprocess.Popen(python_cmd + [MAIN], cwd=HERE)