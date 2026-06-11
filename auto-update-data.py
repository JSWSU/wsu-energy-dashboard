r"""Fully automated water/metering dashboard data update.

Runs the whole monthly pipeline with no human steps:
  1. Authenticates to SkySpark (SCRAM, Project Haystack auth spec)
  2. Runs task_exportToIO(<rolling 3-month window>) via the eval API
  3. Downloads the 7 JSON exports from the project io/ folder
  4. Stages them in data\new\ and runs update-data.sh
     (merge, two outlier passes, known-bad-row fix, push, clean staging)
  5. Alerts by opening a GitHub issue (which emails John) on failure
     or when the published data goes stale (> STALE_DAYS old)

Credentials: C:\Users\john.slagboom\Desktop\Git\skyspark-auth.json (untracked;
see skyspark-auth.json.example). GitHub PAT is read from push-data.sh.

Modes:
  py auto-update-data.py              full run (same as --scheduled)
  py auto-update-data.py --check      verify auth + eval + file download only
  py auto-update-data.py --dry-run    no network; show window, config, paths
  py auto-update-data.py --test-alert open a test GitHub issue (verify alerting)
  py auto-update-data.py 2026-03-01..2026-05-31   full run, explicit window

Scheduled by the Windows task "WSU Dashboard Data Auto-Update" (Mon 07:10).
Exit codes: 0 ok or not-configured (quiet for the scheduler), 1 failure.
"""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import subprocess
import sys
import urllib.request
import urllib.error
from datetime import date, datetime, timedelta
from pathlib import Path

REPO = Path(r"C:\Users\john.slagboom\Desktop\Git")
AUTH_FILE = REPO / "skyspark-auth.json"
PUSH_SCRIPT = REPO / "push-data.sh"
STAGING = REPO / "data" / "new"
LOG_FILE = REPO / "logs" / "auto-update-data.log"
BASH = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Git" / "usr" / "bin" / "bash.exe"

GH_REPO = "jswsu/wsu-energy-dashboard"
EXPORT_FILES = ["electric.json", "condensate.json", "domestic_water.json",
                "irrigation.json", "chw.json", "sites.json", "connectors.json"]
FILE_URL_PATTERNS = [
    "{base}/api/{proj}/file/io/{name}",
    "{base}/proj/{proj}/file/io/{name}",
    "{base}/api/{proj}/io/{name}",
]
STALE_DAYS = 50
TIMEOUT = 120


def log(msg):
    line = f"{datetime.now().strftime('%m/%d/%Y %H:%M:%S')}  {msg}"
    print(line)
    LOG_FILE.parent.mkdir(exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def b64url(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def b64url_decode(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def parse_params(s):
    # "handshakeToken=xxx, hash=SHA-256, data=yyy" -> dict (no scheme prefix)
    params = {}
    for part in s.split(","):
        if "=" in part:
            k, _, v = part.strip().partition("=")
            params[k.strip()] = v.strip()
    return params


def parse_auth_header(value):
    # "SCRAM handshakeToken=xxx, data=yyy" -> (scheme, dict)
    scheme, _, rest = value.partition(" ")
    return scheme.lower(), parse_params(rest)


def http(url, method="GET", headers=None, body=None, timeout=None):
    req = urllib.request.Request(url, data=body, method=method)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout or TIMEOUT)
        return resp.status, resp.headers, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()


def scram_login(base, proj, user, password):
    """Project Haystack SCRAM (SHA-256). Returns auth header dict."""
    about = f"{base}/api/{proj}/about"
    status, hdrs, _ = http(about, headers={
        "Authorization": "HELLO username=" + b64url(user.encode())})
    if status != 401:
        raise RuntimeError(f"HELLO expected 401, got {status}")
    scheme, p = parse_auth_header(hdrs.get("WWW-Authenticate", ""))
    if scheme != "scram":
        raise RuntimeError(f"server offered '{scheme}', not scram")
    hs_token = p["handshakeToken"]

    cnonce = b64url(secrets.token_bytes(16))
    bare = f"n={user},r={cnonce}"
    status, hdrs, _ = http(about, headers={
        "Authorization": f"SCRAM handshakeToken={hs_token}, data=" + b64url(("n,," + bare).encode())})
    if status != 401:
        raise RuntimeError(f"client-first expected 401, got {status}")
    scheme, p = parse_auth_header(hdrs.get("WWW-Authenticate", ""))
    hs_token = p["handshakeToken"]
    server_first = b64url_decode(p["data"]).decode()
    sp = dict(kv.split("=", 1) for kv in server_first.split(","))
    snonce, salt_b64, iters = sp["r"], sp["s"], int(sp["i"])
    if not snonce.startswith(cnonce):
        raise RuntimeError("server nonce does not extend client nonce")

    salted = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                 base64.b64decode(salt_b64), iters)
    client_key = hmac.new(salted, b"Client Key", hashlib.sha256).digest()
    stored_key = hashlib.sha256(client_key).digest()
    cbind = "c=" + base64.b64encode(b"n,,").decode() + ",r=" + snonce
    auth_msg = ",".join([bare, server_first, cbind]).encode()
    sig = hmac.new(stored_key, auth_msg, hashlib.sha256).digest()
    proof = bytes(a ^ b for a, b in zip(client_key, sig))
    final = cbind + ",p=" + base64.b64encode(proof).decode()

    status, hdrs, body = http(about, headers={
        "Authorization": f"SCRAM handshakeToken={hs_token}, data=" + b64url(final.encode())})
    if status != 200:
        raise RuntimeError(f"client-final expected 200, got {status}: {body[:200]!r}")
    p = parse_params(hdrs.get("Authentication-Info", ""))
    token = p.get("authToken")
    if not token:
        raise RuntimeError("no authToken in Authentication-Info")
    return {"Authorization": f"BEARER authToken={token}"}


def sky_eval(base, proj, auth, expr, timeout=None):
    body = f'ver:"3.0"\nexpr\n"{expr}"\n'.encode()
    status, _, resp = http(f"{base}/api/{proj}/eval", method="POST",
                           headers={**auth, "Content-Type": "text/zinc; charset=utf-8",
                                    "Accept": "text/zinc"},
                           body=body, timeout=timeout)
    text = resp.decode("utf-8", "replace")
    if status != 200:
        raise RuntimeError(f"eval HTTP {status}: {text[:300]}")
    first = text.splitlines()[0] if text else ""
    # the bare 'err' marker tag in the grid meta line marks an error grid
    if first.startswith("ver") and re.search(r"\serr(\s|$)", first):
        raise RuntimeError(f"eval error grid: {text[:300]}")
    return text


def download_exports(base, proj, auth):
    """Returns {name: bytes}. Discovers the working file URL pattern."""
    out, pattern = {}, None
    for name in EXPORT_FILES:
        candidates = [pattern] if pattern else FILE_URL_PATTERNS
        got = None
        for pat in candidates:
            url = pat.format(base=base, proj=proj, name=name)
            status, _, body = http(url, headers=auth)
            if status == 200 and body.lstrip()[:1] == b"{":
                try:
                    if "rows" in json.loads(body):
                        got, pattern = body, pat
                        break
                except (ValueError, TypeError):
                    continue
        if got is None:
            raise RuntimeError(f"could not download {name} from io/ (tried "
                               f"{len(candidates)} URL pattern(s))")
        out[name] = got
    log(f"downloaded {len(out)} files via pattern {pattern}")
    return out


def rolling_window(today=None):
    """First day of (current month - 3) .. last day of previous month."""
    today = today or date.today()
    first_this = today.replace(day=1)
    end = first_this - timedelta(days=1)
    y, m = first_this.year, first_this.month - 3
    while m < 1:
        m += 12
        y -= 1
    return f"{y:04d}-{m:02d}-01..{end:%Y-%m-%d}"


def read_pat():
    m = re.search(r'^PAT="([^"]+)"', PUSH_SCRIPT.read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else None


def github_alert(title, body_text):
    """Open a GitHub issue (deduped by exact open-issue title). Never raises."""
    try:
        pat = read_pat()
        if not pat:
            log("ALERT-SKIP: no PAT found in push-data.sh")
            return
        hdrs = {"Authorization": f"Bearer {pat}", "User-Agent": "wsu-auto-update",
                "Accept": "application/vnd.github+json"}
        status, _, body = http(f"https://api.github.com/repos/{GH_REPO}/issues?state=open&per_page=100",
                               headers=hdrs)
        if status == 200 and any(i.get("title") == title for i in json.loads(body)):
            log(f"ALERT-DEDUP: open issue already exists: {title}")
            return
        payload = json.dumps({"title": title, "body": body_text}).encode()
        status, _, body = http(f"https://api.github.com/repos/{GH_REPO}/issues",
                               method="POST", headers=hdrs, body=payload)
        if status == 201:
            log(f"ALERT: opened GitHub issue: {title}")
        else:
            log(f"ALERT-FAIL: HTTP {status} {body[:200]!r}")
    except Exception as e:  # alerting must never crash the pipeline
        log(f"ALERT-FAIL: {e}")


def latest_end_date():
    path = REPO / "data" / "domestic_water.json"
    rows = json.loads(path.read_text(encoding="utf-8"))["rows"]
    best = None
    for r in rows:
        ed = r.get("endDate")
        if ed:
            d = datetime.strptime(ed, "%m-%d-%Y").date()
            best = d if best is None or d > best else best
    return best


def load_config():
    if not AUTH_FILE.exists():
        return None
    cfg = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
    if not cfg.get("username") or not cfg.get("password"):
        return None
    cfg.setdefault("base_url", "https://skyspark.fais.wsu.edu")
    cfg.setdefault("project", "wsumeters")
    cfg["base_url"] = cfg["base_url"].rstrip("/")
    return cfg


def run_pipeline():
    env = dict(os.environ)
    env["PATH"] = str(BASH.parent) + os.pathsep + env.get("PATH", "")
    proc = subprocess.run([str(BASH), "update-data.sh"], cwd=str(REPO),
                          capture_output=True, encoding="utf-8", errors="replace",
                          env=env, timeout=1800)
    for line in (proc.stdout + proc.stderr).splitlines():
        log("  | " + line)
    return proc.returncode


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    args = sys.argv[1:]
    mode = "run"
    window = None
    for a in args:
        if a == "--check":
            mode = "check"
        elif a == "--dry-run":
            mode = "dry"
        elif a == "--test-alert":
            mode = "test-alert"
        elif a == "--scheduled":
            pass
        elif re.fullmatch(r"\d{4}-\d{2}-\d{2}\.\.\d{4}-\d{2}-\d{2}", a):
            window = a
        else:
            print(__doc__)
            return 2
    window = window or rolling_window()

    if mode == "test-alert":
        github_alert(
            f"[auto-update] alert channel test {datetime.now():%m/%d/%Y %H:%M}",
            "Test issue from auto-update-data.py --test-alert. Safe to close.")
        return 0

    if mode == "dry":
        print(f"window      : {window}")
        print(f"auth file   : {AUTH_FILE} ({'present' if AUTH_FILE.exists() else 'MISSING'})")
        print(f"configured  : {bool(load_config())}")
        print(f"bash        : {BASH} ({'ok' if BASH.exists() else 'MISSING'})")
        print(f"staging     : {STAGING} ({'ok' if STAGING.is_dir() else 'MISSING'})")
        print(f"PAT in push-data.sh: {'found' if read_pat() else 'MISSING'}")
        d = latest_end_date()
        if d is None:
            print("latest endDate in published data: none found")
        else:
            print(f"latest endDate in published data: {d:%m/%d/%Y} ({(date.today() - d).days} days old)")
        return 0

    cfg = load_config()
    if not cfg:
        log("not configured: fill in skyspark-auth.json (see skyspark-auth.json.example); exiting quietly")
        return 0

    try:
        log(f"=== auto-update start (mode={mode}, window={window}) ===")
        auth = scram_login(cfg["base_url"], cfg["project"], cfg["username"], cfg["password"])
        log("SkySpark auth OK")

        if mode == "check":
            sky_eval(cfg["base_url"], cfg["project"], auth, "about()")
            log("eval OK")
            download_exports(cfg["base_url"], cfg["project"], auth)
            log("CHECK PASSED: auth, eval, and io/ download all work")
            return 0

        sky_eval(cfg["base_url"], cfg["project"], auth, f"task_exportToIO({window})",
                 timeout=600)
        log(f"export task OK for {window}")
        files = download_exports(cfg["base_url"], cfg["project"], auth)
        STAGING.mkdir(parents=True, exist_ok=True)
        for name, blob in files.items():
            (STAGING / name).write_bytes(blob)
        log(f"staged {len(files)} files in data\\new\\")

        rc = run_pipeline()
        if rc != 0:
            raise RuntimeError(f"update-data.sh exited {rc} (staging kept if push failed)")
        log("pipeline OK")

        d = latest_end_date()
        if d is None:
            log("WARNING: no endDate found in published data; skipping staleness check")
            log("=== auto-update done ===")
            return 0
        age = (date.today() - d).days
        log(f"latest endDate now {d:%m/%d/%Y} ({age} days old)")
        if age > STALE_DAYS:
            github_alert(
                f"[auto-update] water data stale: latest endDate {d:%m/%d/%Y}",
                f"The auto-update ran successfully on {date.today():%m/%d/%Y} with window {window}, "
                f"but the newest endDate in data/domestic_water.json is still {d:%m/%d/%Y} "
                f"({age} days old). Likely cause: the months in the export window have no "
                f"readings in SkySpark yet (manual reads CSV not imported). "
                f"Check with Li / the EnergyMeter.accdb export, then re-run: bash update-data.sh")
        log("=== auto-update done ===")
        return 0
    except Exception as e:
        log(f"FAILED: {e}")
        github_alert(
            f"[auto-update] water dashboard data update failed {date.today():%m/%d/%Y}",
            f"auto-update-data.py failed.\n\nWindow: {window}\nError: {e}\n\n"
            f"Log: C:\\Users\\john.slagboom\\Desktop\\Git\\logs\\auto-update-data.log\n"
            f"Manual fallback: see the How to Use tab on the dashboard or "
            f"docs/WATER-CONSERVATION-OPERATIONS.txt")
        return 1


if __name__ == "__main__":
    sys.exit(main())
