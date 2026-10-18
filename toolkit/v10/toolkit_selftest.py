#!/usr/bin/env python3
"""toolkit_selftest.py -- runs every toolkit self-test and the replay gate (spec Stage 0 and Stage 5b).
Output goes to stdout; the orchestrator saves it as final/script_selftest.txt. Exit 0 only if everything passes."""
import os, sys, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
steps = [["checks.py", "toolkit"], ["checks.py", "selftest"], ["frozen_arith.py", "selftest"],
         ["frozen_arith.py", "--spec", "v9", "selftest"], ["frozen_arith.py", "--spec", "v8", "selftest"], ["frozen_arith.py", "--spec", "v7.1", "selftest"],
         ["frozen_arith.py", "--spec", "v7", "selftest"], ["stage1.py", "selftest"], ["extract.py", "selftest"],
         ["build.py", "selftest"], ["publish.py", "selftest"], ["bridge.py", "selftest"], ["replay.py", "gate"]]
ok = True
for st in steps:
    r = subprocess.run([sys.executable] + st, cwd=HERE, capture_output=True, text=True)
    print(f"===== {' '.join(st)}  (exit {r.returncode})")
    print(r.stdout.strip())
    if r.stderr.strip():
        print(r.stderr.strip())
    ok &= r.returncode == 0
print("TOOLKIT SELF-TEST " + ("PASSED" if ok else "FAILED"))
sys.exit(0 if ok else 1)
