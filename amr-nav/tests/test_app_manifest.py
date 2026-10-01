"""Fails when amr-nav/app-manifest.json is stale. The Android app downloads exactly the files it lists and checks each
size and SHA-256, so a stale list makes the app refuse the new version. Fix: py amr-nav\\tests\\make_app_manifest.py,
then commit app-manifest.json. test_app.py runs this file too, so any workflow that runs the browser test sees it.
Same rules as the generator and the app (it imports the generator): the files git tracks except tests/,
app-manifest.json and dot files; hashes of the bytes GitHub Pages serves (a text file's CRLF line ends count as LF).
No server needed. Run: py amr-nav\\tests\\test_app_manifest.py"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import make_app_manifest as mam  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(detail)[:300] if detail else ""))


man = json.load(open(os.path.join(APP, "app-manifest.json"), encoding="utf-8"))
idx = open(os.path.join(APP, "index.html"), encoding="utf-8").read()
sw = open(os.path.join(APP, "sw.js"), encoding="utf-8").read()
v = re.search(r"APP_VERSION = '([^']+)'", idx).group(1)
swv = re.search(r"const VERSION = 'amr-nav-([^']+)'", sw).group(1)
check("sw.js VERSION is amr-nav- plus APP_VERSION", swv == v, [swv, v])
try:
    now = mam.build(APP)
    check("every file under amr-nav is tracked by git (tests/ aside) and has a name the app can serve", True)
except (OSError, ValueError) as e:
    now = None
    check("every file under amr-nav is tracked by git (tests/ aside) and has a name the app can serve", False, e)
if now:
    head = [man.get("format"), man.get("version"), man.get("minBridge")]
    check("format, version and minBridge match index.html", head == [now["format"], now["version"], now["minBridge"]], [head, now["version"], now["minBridge"]])
    paths, want = [f["path"] for f in man.get("files", [])], [f["path"] for f in now["files"]]
    check("the list holds exactly the app's files", paths == want,
          {"missing": sorted(set(want) - set(paths))[:5], "extra": sorted(set(paths) - set(want))[:5]})
    stale = [f["path"] for f in man.get("files", []) if f not in now["files"]]
    check("every size and SHA-256 matches the bytes the site serves", not stale, stale[:5])
check("index.html is listed", "index.html" in [f["path"] for f in man.get("files", [])])
eol = subprocess.run(["git", "-C", APP, "ls-files", "--eol", "--", "."], capture_output=True, text=True).stdout
check("no file is stored in git with CRLF line ends (the hashes count LF)", "i/crlf" not in eol and "i/mixed" not in eol)
if not all(results):
    print("FIX: py " + os.path.join(HERE, "make_app_manifest.py") + "   (git add a new file first)")
print("SUMMARY", sum(results), "of", len(results), "passed")
sys.exit(0 if all(results) else 1)
