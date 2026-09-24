"""
export_processes_json.py
Builds data/processes.json for the Processes page of the WSU energy dashboard site
(https://jswsu.github.io/wsu-energy-dashboard/processes.html).

Source of truth: the SOP library at C:\\Users\\john.slagboom\\Desktop\\Git\\sops\\ (one folder per
recurring process). This script reads, it never writes there. The sops folder is gitignored and
never published; this JSON is the only thing that reaches the public repo, so it carries:
  process name, cadence, one-line purpose, owner, whether a run.bat exists, LAST VERIFIED date,
  last run date + result word (SUCCESS / FAILED / other), due state.
It never carries dollars, gallons, meter reads, paths on file servers, or SOP steps.

Usage:
  py export_processes_json.py            write data\\processes.json
  py export_processes_json.py --push     also commit + push data\\processes.json to GitHub (main)
Run by: update-data.sh (Mondays), housing-apartment-water-billing\\run.py, update-processes.bat,
and the plan-process-check skill after every logged run.
"""
import json, re, subprocess, sys, datetime as dt
from pathlib import Path

REPO = Path(__file__).resolve().parent
SOPS = REPO / "sops"
OUT = REPO / "data" / "processes.json"
R_SOPS = r"R:\0 - Meter+Billing Process Docs\sops"
TODAY = dt.date.today()

DATE_RE = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")
UNC_RE = re.compile(r"\\\\[^\s,;)]+")            # \\server\share\... paths
DRIVE_RE = re.compile(r"\b[A-Za-z]:\\[^\s,;)]+")   # C:\... or R:\... paths
MONEY_RE = re.compile(r"\$\s?[\d,]+(\.\d+)?")

SPECIAL_TRIGGER = {
    "housing-apartment-water-billing": "housing water bill",
}
CADENCE_WINDOW_DAYS = {"weekly": 10, "monthly": 40, "annual": 400}


def parse_date(s):
    m = DATE_RE.search(s or "")
    if not m:
        return None
    mo, d, y = map(int, m.groups())
    try:
        return dt.date(y, mo, d)
    except ValueError:
        return None


def cadence_class(text):
    t = (text or "").lower()
    if "weekly" in t or "monday" in t or "daily" in t:
        return "weekly"
    if "monthly" in t or "month" in t:
        return "monthly"
    if "annual" in t or "yearly" in t or "fiscal year" in t:
        return "annual"
    return "adhoc"


def clean_sentence(desc):
    """First clause of the INDEX description, paths removed, cut at about 200 characters."""
    d = desc or ""
    d = re.sub(r"\([^)]*\)", "", d)                      # parentheticals usually hold paths and figures
    d = re.sub(r"\s*\)", "", d)                           # a stray close paren left by a nested one
    d = re.split(r";|\. |\|", d)[0]
    d = d.split("\\")[0].rstrip(" ,:")                    # cut at the first backslash: no file or server paths
    d = re.sub(r"\s+(?:at|in|to|under|from|into|on|lives|is)(\s+[A-Za-z])?\s*$", "", d)  # dangling words after the cut
    d = MONEY_RE.sub("[amount]", d)
    d = re.sub(r"\s{2,}", " ", d).strip(" ,:")
    if len(d) > 200:
        d = d[:197].rsplit(" ", 1)[0] + "..."
    return d


def owner_from(desc):
    m = re.search(r"owner\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", desc or "")
    return m.group(1) if m else "Energy Group (John Slagboom)"


def read_index():
    """INDEX.md lines: folder | cadence | what | last verified MM/DD/YYYY"""
    entries = {}
    if not (SOPS / "INDEX.md").exists():
        return entries
    for line in (SOPS / "INDEX.md").read_text(encoding="utf-8", errors="replace").splitlines():
        if " | " not in line or line.startswith(("FORMAT", "#", "Location", "Maintained", "New ", "**", "(")):
            continue
        parts = [p.strip() for p in line.split(" | ")]
        if len(parts) < 3 or " " in parts[0] or not re.match(r"^[a-z0-9][a-z0-9-]+$", parts[0]):
            continue
        folder, cadence, what = parts[0], parts[1], parts[2]
        lv = parse_date(parts[3]) if len(parts) > 3 else None
        entries[folder] = {"cadence": cadence, "what": what, "last_verified": lv}
    return entries


def _last_dated(path):
    """Newest dated line of a log -> (date, result word). Only the date and the word leave the file."""
    if not path or not Path(path).exists():
        return None, None
    lines = [l for l in Path(path).read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
    for line in reversed(lines):
        d = parse_date(line)
        if not d:
            continue
        u = line.upper()
        if "FAILED" in u or "ERROR" in u or re.search(r"EXIT [1-9]", u):
            return d, "FAILED"
        if "SUCCESS" in u or "EXIT 0" in u or " OK" in u or "PASS" in u or u.startswith("RUN ") or "DONE" in u:
            return d, "SUCCESS"
        return d, "LOGGED"
    return None, None


def last_run(folder):
    """Newest run across last-run.log, config.json script_log, status.txt and monitor-log.csv."""
    sources = [folder / "last-run.log", folder / "status.txt", folder / "monitor-log.csv"]
    cfg = folder / "config.json"
    if cfg.exists():
        try:
            sl = json.loads(cfg.read_text(encoding="utf-8")).get("script_log")
            if sl:
                sources.append(Path(sl))
        except Exception:
            pass
    best = (None, None)
    for src in sources:
        d, r = _last_dated(src)
        if d and (best[0] is None or d > best[0]):
            best = (d, r)
    return best


def readme_verified(folder):
    rd = folder / "README.txt"
    if not rd.exists():
        return None
    for line in rd.read_text(encoding="utf-8", errors="replace").splitlines():
        if "LAST VERIFIED" in line.upper():
            return parse_date(line)
    return None


def state_for(cls, run_date, run_result):
    if run_result == "FAILED":
        return "ATTENTION"
    if cls == "adhoc":
        return "AD HOC"
    if run_date is None:
        return "NOT RUN"
    age = (TODAY - run_date).days
    return "DUE" if age > CADENCE_WINDOW_DAYS[cls] else "OK"


def build():
    idx = read_index()
    procs = []
    for folder in sorted(p for p in SOPS.iterdir() if p.is_dir() and not p.name.startswith("_")):
        name = folder.name
        e = idx.get(name, {})
        cadence_text = e.get("cadence", "not recorded in INDEX.md")
        cls = cadence_class(cadence_text)
        run_date, run_result = last_run(folder)
        lv = e.get("last_verified") or readme_verified(folder)
        has_bat = (folder / "run.bat").exists()
        procs.append({
            "id": name,
            "name": name.replace("-", " ").capitalize(),
            "cadence": cadence_text,
            "cadence_class": cls,
            "what": clean_sentence(e.get("what", "")) or "See README.txt in the process folder.",
            "owner": owner_from(e.get("what", "")),
            "run_how": "double-click run.bat" if has_bat else "follow SOP.txt (no script)",
            "claude_trigger": SPECIAL_TRIGGER.get(name, f"plan-process-check recall {name}"),
            "last_verified": lv.strftime("%m/%d/%Y") if lv else None,
            "last_run": run_date.strftime("%m/%d/%Y") if run_date else None,
            "last_result": run_result,
            "state": state_for(cls, run_date, run_result),
            "folder_local": str(SOPS / name),
            "folder_backup": R_SOPS + "\\" + name,
        })
    order = {"ATTENTION": 0, "DUE": 1, "NOT RUN": 2, "OK": 3, "AD HOC": 4}
    procs.sort(key=lambda p: (order[p["state"]], p["name"]))
    return {
        "generated": dt.datetime.now().strftime("%m/%d/%Y %H:%M"),
        "generated_by": "export_processes_json.py (reads the SOP library; never edits it)",
        "library_local": str(SOPS),
        "library_backup": R_SOPS,
        "restore_note": r"R:\0 - Meter+Billing Process Docs\claude-config\RESTORE.txt",
        "windows_days": CADENCE_WINDOW_DAYS,
        "counts": {k: sum(1 for p in procs if p["state"] == k) for k in order},
        "processes": procs,
    }


def push():
    """Publish data/processes.json through push-data.sh (GitHub Contents API, same as the metering data).
    The local git checkout is often behind GitHub because the Monday pipeline pushes through the API,
    so a plain git push would be refused; the API path has no such problem."""
    bash = Path(r"C:\Program Files\Git\bin\bash.exe")
    cmd = [str(bash) if bash.exists() else "bash", str(REPO / "push-data.sh"), "data/processes.json"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180, cwd=str(REPO))
    except Exception as x:
        print("PROBLEM: could not run push-data.sh:", x)
        print("WHAT TO DO: double-click C:\\Users\\john.slagboom\\Desktop\\Git\\update-processes.bat when the network is back.")
        return False
    tail = (r.stdout or "").strip().splitlines()[-3:]
    print("\n".join(tail))
    if r.returncode != 0:
        print("PROBLEM: push-data.sh reported a failure (see lines above).")
        print("WHAT TO DO: check the network and the GitHub token in push-data.sh, then run update-processes.bat again.")
        return False
    return True


if __name__ == "__main__":
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1), encoding="utf-8")
    c = data["counts"]
    print(f"wrote {OUT}: {len(data['processes'])} processes; "
          f"ATTENTION {c['ATTENTION']}, DUE {c['DUE']}, NOT RUN {c['NOT RUN']}, OK {c['OK']}, AD HOC {c['AD HOC']}")
    if "--push" in sys.argv:
        sys.exit(0 if push() else 1)
