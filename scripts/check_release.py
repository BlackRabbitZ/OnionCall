from __future__ import annotations

import pathlib
import subprocess
import sys

root = pathlib.Path(__file__).resolve().parents[1]
checks = [
    [sys.executable, "-m", "compileall", "-q", "onioncall", "scripts", "tests"],
    [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
]
for check in checks:
    subprocess.run(check, cwd=root, check=True)
print("Release checks: OK")
