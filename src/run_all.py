#!/usr/bin/env python
from pathlib import Path
import subprocess, sys

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

def run(cmd):
    print(">", " ".join(cmd))
    subprocess.check_call(cmd, cwd=str(ROOT))

if __name__ == "__main__":
    run([PY, "src/make_dataset.py", "--outdir", "."])
    run([PY, "src/process_data.py", "--outdir", "."])
    run([PY, "src/make_figures.py", "--outdir", "."])
