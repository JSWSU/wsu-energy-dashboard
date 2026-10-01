"""Write app-manifest.json for the AMR Route Guide web app: the files (size and SHA-256) the Android app downloads when a
new web version is pushed to GitHub main. The app reads it from
https://jswsu.github.io/wsu-energy-dashboard/amr-nav/app-manifest.json.
Run after every change in amr-nav, before the commit (test_app.py and test_app_manifest.py fail when it is stale):
    py amr-nav\\tests\\make_app_manifest.py            (from the repository root; or give the amr-nav folder)
Rules:
  * the files git tracks under the folder, except tests/, app-manifest.json itself and names that start with a dot. A new
    file must be added to git first (git add). An untracked or ignored file there stops the run, so a local file can
    never reach the public list. A folder outside git (an archive copy) lists every file on disk by the same rules;
  * paths with "/" separators, sorted; each path made of letters, digits, ".", "-", "_" (what the app serves);
  * the hash is of the bytes GitHub Pages serves: with core.autocrlf=true (this PC) git stores a text file (no NUL byte in
    its first 8000 bytes) with LF line ends while the working copy has CRLF, so CRLF counts as LF here;
  * version = APP_VERSION and minBridge = MIN_BRIDGE, both read from index.html.
Exit 0: written (prints the version and the file count). Exit 2: a rule is broken; nothing written."""
import hashlib
import json
import os
import re
import subprocess
import sys

FORMAT = "amr-app-manifest-1"
SAFE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._-]*(/[A-Za-z0-9_][A-Za-z0-9._-]*)*")
VERSION = re.compile(r"APP_VERSION = '(\d{4}\.\d{2}\.\d{2}-\d{1,4})'")
MIN_BRIDGE = re.compile(r"const MIN_BRIDGE = (\d+);")
HERE = os.path.dirname(os.path.abspath(__file__))


def served_bytes(path):
    """The bytes GitHub Pages serves for this file (a text file's CRLF line ends become LF)."""
    with open(path, "rb") as f:
        data = f.read()
    if b"\r" not in data or b"\0" in data[:8000]:
        return data
    return data.replace(b"\r\n", b"\n")


def kept(rel):
    """True for a path the app gets: not under tests/, not app-manifest.json, no part that starts with a dot."""
    parts = rel.split("/")
    return parts[0] != "tests" and rel != "app-manifest.json" and not any(p.startswith(".") for p in parts)


def git_files(folder, *args):
    """git ls-files for the folder (paths relative to it), or None when the folder is not in a git work tree."""
    r = subprocess.run(["git", "-C", folder, "ls-files", "-z", *args, "--", "."], capture_output=True)
    if r.returncode != 0:
        return None
    return [p for p in r.stdout.decode("utf-8").split("\0") if p]


def listing(folder):
    """The app's files under folder, sorted. In a git work tree: the tracked files, and a ValueError when an untracked or
    ignored file sits there outside tests/. Outside git (an archive copy): every file on disk."""
    tracked = git_files(folder)
    if tracked:
        others = sorted(p for p in (git_files(folder, "--others") or []) if kept(p))
        if others:
            raise ValueError("files that git does not track (git add them, or remove them): " + ", ".join(others[:5]))
        return sorted(p for p in tracked if kept(p) and os.path.isfile(os.path.join(folder, *p.split("/"))))
    out = []
    for root, dirs, files in os.walk(folder):
        rel_root = os.path.relpath(root, folder).replace("\\", "/")
        dirs[:] = sorted(x for x in dirs if not x.startswith(".") and not (rel_root == "." and x == "tests"))
        for name in files:
            rel = name if rel_root == "." else rel_root + "/" + name
            if kept(rel):
                out.append(rel)
    return sorted(out)


def build(folder):
    with open(os.path.join(folder, "index.html"), encoding="utf-8") as f:
        idx = f.read()
    v, mb = VERSION.search(idx), MIN_BRIDGE.search(idx)
    if not v:
        raise ValueError("index.html has no APP_VERSION = 'YYYY.MM.DD-N'")
    if not mb:
        raise ValueError("index.html has no const MIN_BRIDGE = N;")
    files = []
    for rel in listing(folder):
        if len(rel) > 200 or not SAFE.fullmatch(rel):
            raise ValueError("a file name the app cannot serve: " + rel)
        data = served_bytes(os.path.join(folder, *rel.split("/")))
        files.append({"path": rel, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    lower = [f["path"].lower() for f in files]
    if len(set(lower)) != len(lower):
        raise ValueError("two files differ only in upper and lower case")
    if "index.html" not in [f["path"] for f in files]:
        raise ValueError("no index.html")
    return {"format": FORMAT, "version": v.group(1), "minBridge": int(mb.group(1)), "files": files}


def text(man):
    """The file text: one file per line, LF line ends, a newline at the end (the same bytes for the same input)."""
    lines = ["{", ' "format": "%s",' % man["format"], ' "version": "%s",' % man["version"], ' "minBridge": %d,' % man["minBridge"], ' "files": [']
    for i, f in enumerate(man["files"]):
        lines.append("  " + json.dumps(f, separators=(", ", ": ")) + ("," if i < len(man["files"]) - 1 else ""))
    lines += [" ]", "}"]
    return "\n".join(lines) + "\n"


def main(argv):
    if len(argv) > 1:
        print(__doc__)
        return 2
    folder = os.path.abspath(argv[0]) if argv else os.path.dirname(HERE)
    try:
        man = build(folder)
    except (OSError, ValueError) as e:
        print("NOT WRITTEN: " + str(e))
        return 2
    with open(os.path.join(folder, "app-manifest.json"), "w", encoding="utf-8", newline="\n") as f:
        f.write(text(man))
    print("app-manifest.json written: version %s, minBridge %d, %d files, %d bytes"
          % (man["version"], man["minBridge"], len(man["files"]), sum(f["size"] for f in man["files"])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
