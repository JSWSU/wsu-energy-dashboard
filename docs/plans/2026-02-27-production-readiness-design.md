# WSU Construction Document Review System — Production Readiness Design

**Goal:** Transform the review pipeline prototype into a reliable, multi-user, IT-maintainable production tool through three phased milestones.

**Approach:** Harden the existing Perl server + bash scripts + Python pipeline architecture. No rewrite. Each phase builds on the previous one.

**Users:** 5-10 internal WSU Facilities Services staff, phased rollout.

---

## Current State

The pipeline works end-to-end but has reliability problems that prevent hands-off operation:

- **Server:** Single-threaded Perl HTTP server on port 8083 (localhost only)
- **Reviews:** Claude CLI invocations in generated bash scripts, 8 parallel discipline scans
- **Storage:** Flat files in `reviews/` directory, job state in `job.json`
- **Auth:** Client-side password gate only, no server-side access control
- **Process management:** Manual start/stop, no watchdog, no crash recovery

**Key pain points:**
- Reviews advertised at 15-20 min but take 60+ min (hung Claude CLI calls with no timeout)
- Server crashes/hangs require manual restart
- Jobs fail silently — no clear error messages, stall detection takes up to 60 min
- Constant babysitting required

---

## Phase 1: Reliability — "Start a review, walk away"

### 1A. Timeout wrappers on Claude CLI calls

**Problem:** A hung Claude API call blocks the discipline indefinitely. Phase 2 waits for all disciplines, so one hung call blocks the entire review until the 60-min auto-fail kills everything.

**Solution:** Wrap every Claude CLI invocation in the generated bash scripts with `timeout`:

```bash
timeout 600 "$CLAUDE_PATH" -p "$PROMPT" --model sonnet \
  --allowedTools Read Write \
  --dangerously-skip-permissions \
  --output-format text \
  > "$OUTDIR/${key}-stdout.log" 2> "$OUTDIR/${key}-stderr.log" &
```

- 600 seconds (10 min) per discipline
- Exit code 124 = timeout — retry immediately instead of waiting
- Add timeout detection to the monitoring loop in `run-review.sh`
- Reduces worst-case review time from 60 min to ~25 min (10 min timeout + 3 retries × 10 min, but retries overlap with other disciplines)

### 1B. Server process management

**PID file:** Write `review-server.pid` on startup, delete on exit.

**Signal handlers:** Trap SIGTERM/SIGINT — close listening socket, log shutdown, exit cleanly. Prevents orphaned background processes when the server is stopped.

**Health check endpoint:** `GET /api/health` returns:
```json
{"status": "ok", "uptime": 3600, "activeJobs": 1, "queuedJobs": 0}
```

**Watchdog script:** `review-watchdog.sh` checks if the PID is alive and restarts the server if dead. Runs from Windows Task Scheduler every 2 minutes.

### 1C. Upload validation

**Partial upload protection:** Validate `Content-Length` matches actual bytes received in `read_exact()`. If they differ, reject with 400 instead of processing a truncated PDF.

**PDF header check:** After writing the file, verify the first 5 bytes are `%PDF-`. Catches obviously corrupt uploads before spawning analysis.

### 1D. Configuration file

Move all hardcoded values to `review-config.json`:

```json
{
  "port": 8083,
  "reviewsDir": "./reviews",
  "maxUploadMB": 100,
  "maxParallelDisciplines": 8,
  "disciplineTimeoutSec": 600,
  "stallThresholds": {
    "phase0FailMin": 30,
    "phase1WarnMin": 45,
    "phase1FailMin": 60,
    "phase2WarnMin": 30,
    "phase2FailMin": 45,
    "phase3WarnMin": 15,
    "phase3FailMin": 30
  }
}
```

Server reads config on startup, falls back to current defaults if file missing. No Perl source edits needed for deployment on a different machine.

### 1E. Per-phase timing logs

Write `timing.json` per job for post-hoc diagnostics:

```json
{
  "phase0": {"startedAt": "...", "durationSec": 45, "pageCount": 58},
  "phase1": {
    "arch-structure": {"startedAt": "...", "durationSec": 180, "retries": 0},
    "electrical": {"startedAt": "...", "durationSec": 240, "retries": 1, "timedOut": true}
  },
  "phase2": {"durationSec": 30, "findingsCount": 47},
  "phase3": {"durationSec": 15},
  "totalDurationSec": 620
}
```

Generated bash scripts log timestamps at each phase boundary. A small post-processing step in the completion handler reads the logs and writes `timing.json`.

### 1F. Phase 1 security (localhost hardening)

- Restrict CORS from `*` to `http://localhost:8083`
- Use UUIDs for job IDs instead of predictable timestamps
- Store config secrets outside the web-served directory

---

## Phase 2: Multi-User — "Others can submit reviews without my help"

Assumes Phase 1 is complete.

### 2A. Server-side authentication

**Token-based auth:** Every `/api/*` request must include `Authorization: Bearer <token>`. The portal obtains a token by POSTing the shared password to `POST /api/login`. Token is a HMAC of the password + server secret + expiry timestamp, valid for 24 hours.

**Flow:**
1. User enters password in auth gate
2. Portal sends `POST /api/login {password: "..."}`
3. Server validates password (from config), returns `{token: "...", expiresAt: "..."}`
4. Portal stores token in localStorage, sends it on all subsequent requests
5. Server validates token on every `/api/*` endpoint (except `/api/login` and `/api/health`)

**Job ownership:** Each job records `pmEmail`. API responses filter to show only the authenticated user's jobs. Admin emails (configurable list in `review-config.json`) see all jobs.

### 2B. Job queue (sequential execution)

**Problem:** Currently the server returns 409 if a review is already running. Multi-user requires queuing.

**Solution:**
- Remove the single-job guard from the submit endpoint
- Add `queuePosition` field to job.json
- Server processes jobs sequentially — when current review completes, start the next queued job
- Queue check runs in the main loop's idle timeout (between accepts, using IO::Select)
- Portal shows queue position: "Your review is #3 in queue"

**Why sequential:** Each review runs 8 parallel Claude API calls. Two simultaneous reviews = 16 calls = guaranteed rate limiting. Sequential with a visible queue is more reliable and cost-predictable.

### 2C. Network accessibility

**Phase 2 default:** Bind to `0.0.0.0:8083`, open Windows Firewall port. Users access via `http://your-machine:8083/review-portal.html`.

**Config option:**
```json
{
  "bindAddress": "0.0.0.0",
  "port": 8083
}
```

### 2D. Email retry queue

**Problem:** Email is sent inline during `check_job_status()`, blocking the request handler. Failures are logged to stderr only, never retried.

**Solution:**
- On job completion, write `pending-email.json` in the job directory
- Periodic check (every 60 seconds in main loop idle time) scans for pending emails
- Retry up to 3 times with backoff (1 min, 5 min, 15 min)
- Record attempt count and last error in the email file
- Portal shows email status in job details

### 2E. Phase 2 security (network hardening)

- Rate limiting: max 5 submissions/hour/IP, max 60 API requests/min/IP
- Download authorization: verify requesting user owns the job
- Audit log: append-only `access.log` with timestamp, IP, endpoint, authenticated user
- Restrict CORS to the configured server origin

---

## Phase 3: IT Handoff — "Something IT can maintain"

Assumes Phases 1-2 are complete.

### 3A. Windows Service via NSSM

Use NSSM (Non-Sucking Service Manager) to run the Perl server as a Windows service:
- Auto-starts on boot
- Auto-restarts on crash (built-in restart policy)
- Runs under a service account
- Logs stdout/stderr to rotating log files
- Replaces the Phase 1 watchdog script

### 3B. Deployment documentation

- `DEPLOYMENT.txt` — step-by-step setup on a fresh Windows machine
- `review-config.json` field reference
- SMTP setup guide for WSU mail
- Runbook: restart service, check logs, clear stuck jobs, rotate API keys

### 3C. Admin panel

`/admin` page (behind separate admin password):
- Server uptime, memory, disk space
- Active/queued/completed/failed job counts
- Per-job timing data (from Phase 1E)
- One-click actions: restart stalled job, force-fail stuck job, purge old jobs
- Claude API usage summary (total tokens this month, cost estimate)

### 3D. Log rotation and job cleanup

- Rotate server logs daily (keep 30 days)
- Auto-archive completed jobs older than 90 days
- Disk usage warnings at configurable threshold

### 3E. Phase 3 security (production hardening)

- HTTPS via reverse proxy (nginx/caddy)
- File permissions: reviews directory owner-only
- Config file permissions: 600
- Optional: WSU SSO (CAS/Shibboleth) if IT requires it

---

## What's explicitly out of scope

- **Python rewrite of the server** — revisit in Phase 3 if IT prefers Python
- **Cloud deployment** — overkill for 5-10 users
- **PDF encryption at rest** — file permissions + auth are sufficient
- **Individual user accounts with database** — shared password + email ownership is enough
- **WSU SSO in Phase 1/2** — prove value first, integrate later

---

## Phase summary

| Phase | Goal | Key Deliverables | Prerequisite |
|-------|------|-----------------|--------------|
| **1** | Hands-off reliability | CLI timeouts, watchdog, config file, upload validation, timing logs, localhost security | None |
| **2** | Multi-user ready | Server-side auth, job queue, network binding, email retry, network security | Phase 1 |
| **3** | IT handoff | Windows Service, deployment docs, admin panel, log rotation, HTTPS | Phase 2 |
