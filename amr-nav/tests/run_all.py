"""Run every AMR Route Guide browser test script in this folder (test_*.py), one after another, and print one summary.
Serve the repository root first: py -m http.server PORT --bind 127.0.0.1, and set AMR_TEST_PORT=PORT (default 41999).
Run: py amr-nav\\tests\\run_all.py        Exit 0 only when every script passes."""
import glob
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ENV = {k: v for k, v in os.environ.items() if k != "AMR_TEST_CASE"}   # every case runs here, whatever one run set
bad = []
for s in sorted(glob.glob(os.path.join(HERE, "test_*.py"))):
    t0 = time.time()
    r = subprocess.run([sys.executable, s], capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV)
    print(f"{os.path.basename(s)}: exit {r.returncode} in {time.time() - t0:.0f} s")
    for ln in [x for x in r.stdout.splitlines() if x.startswith(("SUMMARY", "FAIL"))][-15:]:
        print("   " + ln)
    if r.returncode != 0:
        bad.append(os.path.basename(s))
        if r.stderr.strip():
            print("   stderr: " + r.stderr.strip().splitlines()[-1])
print("RUN_ALL " + ("OK" if not bad else "FAILED: " + ", ".join(bad)))
sys.exit(1 if bad else 0)
