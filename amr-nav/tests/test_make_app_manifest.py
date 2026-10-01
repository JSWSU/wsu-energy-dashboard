"""Offline checks of make_app_manifest.py (temp folders only; one is a new git repository). No server needed.
Run: py amr-nav\\tests\\test_make_app_manifest.py"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_app_manifest as mam  # noqa: E402

results = []


def eq(name, got, want):
    ok = got == want
    results.append(ok)
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f" | got {got!r}, want {want!r}"))


def put(root, rel, data):
    p = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data)


def fill(d):
    put(d, "index.html", b"<script>\r\nconst APP_VERSION = '2026.10.02-1';\r\nconst MIN_BRIDGE = 2;\r\n</script>\r\n")
    put(d, "route.json", b'{"legs":[1]}')
    put(d, "icons/icon.png", b"\x89PNG\r\n\x1a\n\x00\x00\r\n")
    put(d, "vendor/leaflet/leaflet.css", b"a{}\r\nb{}\r\n")
    put(d, "tests/test_app.py", b"print(1)\r\n")
    put(d, ".hidden", b"x")
    put(d, "app-manifest.json", b"old")


d = tempfile.mkdtemp(prefix="amr-man-")
try:
    fill(d)
    man = mam.build(d)
    paths = [f["path"] for f in man["files"]]
    eq("format, version and minBridge from index.html", [man["format"], man["version"], man["minBridge"]], ["amr-app-manifest-1", "2026.10.02-1", 2])
    eq("a folder outside git: every file but tests/, dot files and app-manifest.json, sorted", paths, ["icons/icon.png", "index.html", "route.json", "vendor/leaflet/leaflet.css"])
    css = next(f for f in man["files"] if f["path"] == "vendor/leaflet/leaflet.css")
    eq("a text file is hashed with LF line ends (what GitHub Pages serves)", [css["size"], css["sha256"]], [8, hashlib.sha256(b"a{}\nb{}\n").hexdigest()])
    png = next(f for f in man["files"] if f["path"] == "icons/icon.png")
    eq("a binary file is hashed as it is", png["sha256"], hashlib.sha256(b"\x89PNG\r\n\x1a\n\x00\x00\r\n").hexdigest())
    eq("served_bytes leaves a file with no CR alone", mam.served_bytes(os.path.join(d, "route.json")), b'{"legs":[1]}')
    rc = mam.main([d])
    raw = open(os.path.join(d, "app-manifest.json"), "rb").read()
    eq("main writes the file (exit 0)", rc, 0)
    eq("the file is JSON with the same content", json.loads(raw.decode("utf-8")), man)
    eq("the file has LF line ends and one file per line", (b"\r" not in raw, raw.count(b'"path"'), raw.endswith(b"}\n")), (True, 4, True))
    mam.main([d])
    eq("the same input gives the same bytes", open(os.path.join(d, "app-manifest.json"), "rb").read(), raw)
    put(d, "bad name.js", b"x")
    eq("a file name the app cannot serve: exit 2, nothing written", (mam.main([d]), open(os.path.join(d, "app-manifest.json"), "rb").read() == raw), (2, True))
    os.remove(os.path.join(d, "bad name.js"))
    put(d, "index.html", b"<script>const APP_VERSION = '2026.10.02-1';</script>")
    eq("no MIN_BRIDGE in index.html: exit 2", mam.main([d]), 2)
    put(d, "index.html", b"<script>const MIN_BRIDGE = 1;</script>")
    eq("no APP_VERSION in index.html: exit 2", mam.main([d]), 2)
finally:
    shutil.rmtree(d, ignore_errors=True)

g = tempfile.mkdtemp(prefix="amr-man-git-")
try:
    a = os.path.join(g, "amr-nav")
    fill(a)
    subprocess.run(["git", "-C", g, "init", "-q"], capture_output=True)
    subprocess.run(["git", "-C", g, "add", "amr-nav"], capture_output=True)
    eq("a git work tree: the tracked files, minus tests/, dot files and app-manifest.json", mam.listing(a),
       ["icons/icon.png", "index.html", "route.json", "vendor/leaflet/leaflet.css"])
    put(a, "tests/scratch.py", b"x")
    eq("git: an untracked file under tests/ does not matter (exit 0)", mam.main([a]), 0)
    raw = open(os.path.join(a, "app-manifest.json"), "rb").read()
    put(a, "extra.js", b"x")
    eq("git: an untracked file stops the run (exit 2) and nothing is written",
       (mam.main([a]), open(os.path.join(a, "app-manifest.json"), "rb").read() == raw), (2, True))
    os.remove(os.path.join(a, "extra.js"))
    put(g, ".gitignore", b"local.txt\n")
    put(a, "local.txt", b"x")
    eq("git: an ignored file stops the run too (exit 2)", mam.main([a]), 2)
finally:
    shutil.rmtree(g, ignore_errors=True)
print("SUMMARY", sum(results), "of", len(results), "passed")
sys.exit(0 if all(results) else 1)
