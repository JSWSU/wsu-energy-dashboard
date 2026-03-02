# Production Readiness Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the WSU construction document review pipeline from a prototype into a reliable, multi-user, IT-maintainable production tool across 3 phases.

**Architecture:** Harden the existing Perl server + bash scripts + Python pipeline. No rewrite. Phase 1 adds reliability (timeouts, watchdog, config). Phase 2 adds multi-user support (auth, queue, network). Phase 3 adds IT handoff (Windows Service, admin panel, docs).

**Tech Stack:** Perl 5 (review-server.pl), Python 3 (analyze_sheets.py, synthesize.py, generate_reports.py), Bash (generated scripts), HTML/JS (review-portal.html), Windows/MSYS2

**Design doc:** `docs/plans/2026-02-27-production-readiness-design.md`

---

# PHASE 1: RELIABILITY

---

### Task 1: Configuration file system

**Files:**
- Create: `review-config.json` (default config, committed to repo)
- Modify: `review-server.pl:18-41` (startup section)

**Context:** Currently all values are hardcoded: port (line 18), reviews dir (line 20), upload limits, stall thresholds, parallel discipline count. Moving these to a config file lets the server run on different machines without editing Perl source.

**Step 1: Create the default config file**

```json
{
  "port": 8083,
  "bindAddress": "127.0.0.1",
  "reviewsDir": "./reviews",
  "maxUploadMB": 100,
  "maxParallelDisciplines": 8,
  "disciplineTimeoutSec": 600,
  "bodyReadTimeoutSec": 120,
  "headerReadTimeoutSec": 30,
  "stallThresholds": {
    "phase0FailMin": 30,
    "phase1WarnMin": 45,
    "phase1FailMin": 60,
    "phase2WarnMin": 30,
    "phase2FailMin": 45,
    "phase3WarnMin": 15,
    "phase3FailMin": 30
  },
  "email": {
    "enabled": false,
    "smtpHost": "",
    "smtpPort": 587,
    "smtpUser": "",
    "smtpPass": "",
    "from": ""
  }
}
```

**Step 2: Add config loading to review-server.pl**

Add a `load_config()` function after the `use` statements (line 17). It reads `review-config.json` from `$ROOT`, falls back to defaults for any missing keys. Store in a global `%CFG` hash.

```perl
my %CFG;

sub load_config {
    my $path = "$ROOT/review-config.json";
    my %defaults = (
        port                   => 8083,
        bindAddress            => '127.0.0.1',
        reviewsDir             => './reviews',
        maxUploadMB            => 100,
        maxParallelDisciplines => 8,
        disciplineTimeoutSec   => 600,
        bodyReadTimeoutSec     => 120,
        headerReadTimeoutSec   => 30,
    );
    if (-f $path) {
        open my $fh, '<', $path or do { warn "Cannot read $path: $!\n"; return %defaults; };
        local $/; my $json = <$fh>; close $fh;
        my $cfg = eval { decode_json($json) };
        if ($@ || ref($cfg) ne 'HASH') {
            warn "Invalid config JSON: $@\n";
            return %defaults;
        }
        # Merge: config overrides defaults
        for my $k (keys %defaults) {
            $cfg->{$k} = $defaults{$k} unless defined $cfg->{$k};
        }
        return %$cfg;
    }
    return %defaults;
}

%CFG = load_config();
```

**Step 3: Replace all hardcoded values with config references**

- Line 18: `my $port = $ARGV[0] || 8083;` → `my $port = $ARGV[0] || $CFG{port};`
- Line 20: `my $REVIEWS_DIR = "$ROOT/reviews";` → `my $REVIEWS_DIR = File::Spec->rel2abs($CFG{reviewsDir}, $ROOT);`
- Line 56: `LocalAddr => '0.0.0.0'` → `LocalAddr => $CFG{bindAddress}`
- Line 99: `$timeout ||= 120;` → `$timeout ||= $CFG{bodyReadTimeoutSec};`
- Line 1389: `$sel->can_read(30)` → `$sel->can_read($CFG{headerReadTimeoutSec})`
- Line 1126: `my $MAX_PARALLEL = 8;` → `my $MAX_PARALLEL = $CFG{maxParallelDisciplines};`
- Upload size check: `100 * 1024 * 1024` → `$CFG{maxUploadMB} * 1024 * 1024`
- Stall thresholds in `check_job_status()`: replace hardcoded 45/60/30/15 minute values with `$CFG{stallThresholds}{...}`
- Move email config from separate `email-config.json` into `$CFG{email}` — update `load_email_config()` to read from `%CFG` instead of a separate file

**Step 4: Verify syntax and test**

Run: `perl -c review-server.pl`
Expected: `review-server.pl syntax OK`

Test: Start server without config file (should use defaults). Then create `review-config.json` with a different port, restart, verify it binds to the new port.

**Step 5: Commit**

```bash
git add review-config.json review-server.pl
git commit -m "Add config file system — move hardcoded values to review-config.json"
```

---

### Task 2: Claude CLI timeout wrappers

**Files:**
- Modify: `review-server.pl:1080-1200` (spawn_review — Phase 1 discipline launch section)

**Context:** The generated `run-review.sh` launches Claude CLI without any timeout. A hung API call blocks the discipline forever, and Phase 2 (synthesis) waits for all disciplines. This is the #1 cause of reviews taking 60+ minutes.

**Step 1: Add timeout to Claude CLI invocations in the generated bash script**

Find the section in `spawn_review()` where discipline CLI calls are written to the bash script (the `print $fh` lines that write the Claude CLI command). Wrap with `timeout`:

Before:
```bash
"$CLAUDE_PATH" -p "$PROMPT_${KEY}" --model sonnet ... > stdout.log 2> stderr.log &
```

After:
```bash
timeout $DISCIPLINE_TIMEOUT "$CLAUDE_PATH" -p "$PROMPT_${KEY}" --model sonnet ... > stdout.log 2> stderr.log &
```

Add `DISCIPLINE_TIMEOUT=$CFG{disciplineTimeoutSec}` as a variable near the top of the generated script.

**Step 2: Add timeout detection to the monitoring loop**

In the generated bash script's monitoring/wait loop, check exit code 124 (timeout) for each discipline process. When detected:
- Write a clear message to the discipline's stderr log: `"TIMEOUT: Discipline $KEY exceeded ${DISCIPLINE_TIMEOUT}s limit"`
- Move immediately to retry instead of waiting for the stall detector

**Step 3: Add timeout to Phase 2 synthesis and Phase 3 report generation**

The Claude CLI call for the executive summary (Phase 2b) also has no timeout. Add the same `timeout` wrapper. Use a shorter timeout (300s / 5 min) since synthesis is a smaller task.

**Step 4: Verify the generated script**

Submit a test review, then inspect the generated `reviews/<jobid>/run-review.sh` to verify `timeout` commands are present.

**Step 5: Commit**

```bash
git add review-server.pl
git commit -m "Add timeout wrappers to all Claude CLI invocations

10-min timeout per discipline, 5-min for synthesis. Detects exit
code 124 and moves to retry immediately instead of waiting for the
60-min stall detector."
```

---

### Task 3: Per-phase timing logs

**Files:**
- Modify: `review-server.pl` (spawn_review — generated bash script)
- Modify: `review-server.pl:429-460` (check_job_status — completion handler)

**Context:** When a review takes an hour, there's no way to know which phase was slow. Adding structured timing data per job enables diagnosis.

**Step 1: Add timestamp logging to the generated bash script**

At the start and end of each phase in `run-review.sh`, write to a `timing.log` file:

```bash
echo "phase0_start=$(date +%s)" >> "$OUTDIR/timing.log"
# ... Phase 0 runs ...
echo "phase0_end=$(date +%s)" >> "$OUTDIR/timing.log"
echo "phase0_pages=$PAGE_COUNT" >> "$OUTDIR/timing.log"

echo "phase1_start=$(date +%s)" >> "$OUTDIR/timing.log"
# ... Each discipline logs its own start/end ...
echo "disc_${KEY}_start=$(date +%s)" >> "$OUTDIR/timing.log"
# ... discipline runs ...
echo "disc_${KEY}_end=$(date +%s)" >> "$OUTDIR/timing.log"
echo "disc_${KEY}_retries=$RETRY_COUNT" >> "$OUTDIR/timing.log"
echo "phase1_end=$(date +%s)" >> "$OUTDIR/timing.log"

echo "phase2_start=$(date +%s)" >> "$OUTDIR/timing.log"
# ... synthesis ...
echo "phase2_end=$(date +%s)" >> "$OUTDIR/timing.log"
echo "phase2_findings=$FINDING_COUNT" >> "$OUTDIR/timing.log"
```

**Step 2: Parse timing.log into timing.json on completion**

In the completion handler within `check_job_status()` (around line 429), after detecting the COMPLETE sentinel, read `timing.log` and build a structured `timing.json`:

```perl
sub parse_timing_log {
    my ($job_dir) = @_;
    my $logfile = "$job_dir/output/timing.log";
    return {} unless -f $logfile;
    open my $fh, '<', $logfile or return {};
    my %data;
    while (<$fh>) {
        chomp;
        my ($k, $v) = split /=/, $_, 2;
        $data{$k} = $v if defined $k && defined $v;
    }
    close $fh;
    # Build structured timing hash
    my %timing;
    for my $phase (qw(phase0 phase1 phase2 phase3)) {
        next unless $data{"${phase}_start"};
        $timing{$phase} = {
            startedAt   => $data{"${phase}_start"},
            durationSec => ($data{"${phase}_end"} || time()) - $data{"${phase}_start"},
        };
    }
    # Add per-discipline timing
    for my $k (grep { /^disc_.*_start$/ } keys %data) {
        (my $disc = $k) =~ s/^disc_(.*)_start$/$1/;
        $timing{phase1}{disciplines}{$disc} = {
            durationSec => ($data{"disc_${disc}_end"} || 0) - $data{"disc_${disc}_start"},
            retries     => $data{"disc_${disc}_retries"} || 0,
        };
    }
    $timing{phase2}{findingsCount} = $data{phase2_findings} if $data{phase2_findings};
    $timing{phase0}{pageCount} = $data{phase0_pages} if $data{phase0_pages};
    return \%timing;
}
```

Write the result to `timing.json` and store a summary in `job.json` under a `timing` key.

**Step 3: Add timing.json to deliverables list**

In the deliverables array (line 452), add `timing.json` so it appears in the portal's download links.

**Step 4: Commit**

```bash
git add review-server.pl
git commit -m "Add per-phase timing logs for review duration diagnostics

Each phase logs timestamps to timing.log. On completion, parsed into
structured timing.json with per-discipline duration and retry counts."
```

---

### Task 4: Upload validation (Content-Length + PDF header)

**Files:**
- Modify: `review-server.pl:97-112` (read_exact)
- Modify: `review-server.pl:1505-1511` (PDF write in submit handler)

**Context:** If a client disconnects mid-upload, `read_exact()` returns a partial body silently. The truncated PDF gets saved and analyzed, eventually failing in pdfplumber. We should catch this at upload time.

**Step 1: Return length from read_exact and validate**

Change `read_exact()` to return the buffer and a boolean indicating whether the full length was received:

```perl
sub read_exact {
    my ($sock, $len, $timeout) = @_;
    $timeout ||= $CFG{bodyReadTimeoutSec};
    my $sel = IO::Select->new($sock);
    my $buf = '';
    while (length($buf) < $len) {
        unless ($sel->can_read($timeout)) {
            warn "[TIMEOUT] read_exact timed out after ${timeout}s with " . length($buf) . "/$len bytes\n";
            return ($buf, 0);  # incomplete
        }
        my $n = read($sock, my $chunk, $len - length($buf));
        return ($buf, 0) unless $n;  # EOF — incomplete
        $buf .= $chunk;
    }
    return ($buf, 1);  # complete
}
```

Update the call site in the request handler to check the second return value. If incomplete, send 400 and close.

**Step 2: Add PDF header validation**

After writing the PDF file (line 1510), check the first 5 bytes:

```perl
        # Validate PDF header
        open my $vfh, '<:raw', "$job_dir/input.pdf" or do {
            send_json($c, 500, { error => "Cannot verify PDF" });
            remove_tree($job_dir);
            close $c; next;
        };
        read $vfh, my $magic, 5;
        close $vfh;
        if (($magic || '') ne '%PDF-') {
            send_json($c, 400, { error => 'Uploaded file is not a valid PDF (missing %PDF- header)' });
            remove_tree($job_dir);
            close $c; next;
        }
```

**Step 3: Commit**

```bash
git add review-server.pl
git commit -m "Validate upload completeness and PDF header

Detect partial uploads from client disconnect. Verify %PDF- magic
bytes before spawning analysis."
```

---

### Task 5: Server process management

**Files:**
- Modify: `review-server.pl:55-68` (startup section)
- Modify: `review-server.pl:1383` (main accept loop)

**Context:** The server has no PID file, no signal handlers, and no health check. If it crashes, nothing detects it. If you Ctrl+C it, background processes are orphaned.

**Step 1: Write PID file on startup**

After binding the socket (line 58), write the PID:

```perl
# Write PID file
my $pidfile = "$ROOT/review-server.pid";
open my $pidfh, '>', $pidfile or warn "Cannot write PID file: $!\n";
if ($pidfh) { print $pidfh $$; close $pidfh; }
```

**Step 2: Add signal handlers**

After the PID file, set up SIGTERM/SIGINT handlers:

```perl
my $shutdown = 0;
$SIG{INT} = $SIG{TERM} = sub {
    print "\n[" . localtime() . "] Received shutdown signal. Closing server.\n";
    $shutdown = 1;
};
```

Modify the main accept loop to check `$shutdown`:

```perl
while (!$shutdown && (my $c = $srv->accept)) {
    # ... existing request handling ...
}

# Cleanup on exit
close $srv;
unlink $pidfile if -f $pidfile;
print "[" . localtime() . "] Server shut down cleanly.\n";
```

**Step 3: Add health check endpoint**

In the request handler, before the static file serving section, add:

```perl
    # GET /api/health
    if ($method eq 'GET' && $path eq '/api/health') {
        my $uptime = time() - $^T;  # $^T is script start time
        my ($active, $queued) = (0, 0);
        if (opendir my $dh, $REVIEWS_DIR) {
            while (my $d = readdir $dh) {
                next if $d =~ /^\./;
                my $j = read_job_json($d);
                next unless $j;
                my $st = $j->{status} || '';
                $active++ if $st eq 'Processing' || $st eq 'Analyzing';
                $queued++ if $st eq 'Queued';
            }
            closedir $dh;
        }
        send_json($c, 200, {
            status     => 'ok',
            uptime     => $uptime,
            activeJobs => $active,
            queuedJobs => $queued,
            pid        => $$,
        });
        close $c; next;
    }
```

**Step 4: Track server start time for uptime**

Use Perl's `$^T` (script start time) — no additional variable needed.

**Step 5: Commit**

```bash
git add review-server.pl
git commit -m "Add PID file, signal handlers, and health check endpoint

Server writes review-server.pid on startup, cleans up on SIGTERM/SIGINT.
GET /api/health returns uptime, active/queued job counts."
```

---

### Task 6: Watchdog script

**Files:**
- Create: `review-watchdog.sh`

**Context:** The watchdog checks if the server PID is alive and restarts it if dead. Designed to run from Windows Task Scheduler every 2 minutes.

**Step 1: Write the watchdog script**

```bash
#!/bin/bash
# review-watchdog.sh — Restart review server if it's not running.
# Schedule via Windows Task Scheduler every 2 minutes.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PIDFILE="$SCRIPT_DIR/review-server.pid"
LOGFILE="$SCRIPT_DIR/watchdog.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOGFILE"; }

# Check PID file exists
if [ ! -f "$PIDFILE" ]; then
    log "No PID file found. Starting server."
    cd "$SCRIPT_DIR"
    nohup perl review-server.pl >> server.log 2>&1 &
    log "Server started with PID $!"
    exit 0
fi

PID=$(cat "$PIDFILE")

# Check if process is alive (Windows: tasklist; Unix: kill -0)
if tasklist //FI "PID eq $PID" 2>/dev/null | grep -q "$PID"; then
    # Server is running
    exit 0
fi

# Server is dead — restart
log "Server PID $PID is not running. Restarting."
rm -f "$PIDFILE"
cd "$SCRIPT_DIR"
nohup perl review-server.pl >> server.log 2>&1 &
log "Server restarted with PID $!"
```

**Step 2: Make executable**

Run: `chmod +x review-watchdog.sh`

**Step 3: Test**

1. Start server: `perl review-server.pl &`
2. Verify PID file exists
3. Kill server: `kill <pid>`
4. Run watchdog: `bash review-watchdog.sh`
5. Verify server restarted (new PID file)

**Step 4: Commit**

```bash
git add review-watchdog.sh
git commit -m "Add watchdog script for automatic server restart

Checks PID file, restarts server if process is dead. Designed for
Windows Task Scheduler (every 2 min)."
```

---

### Task 7: Localhost security hardening

**Files:**
- Modify: `review-server.pl:73-77` (make_job_id)
- Modify: `review-server.pl:87` (CORS header)

**Context:** Job IDs are predictable timestamps (20260227-181219), making brute-force enumeration trivial. CORS is `*`, allowing any website to hit the API.

**Step 1: Replace timestamp job IDs with UUIDs**

Replace `make_job_id()`:

```perl
sub make_job_id {
    # UUID v4: 8-4-4-4-12 hex characters
    my @hex = map { sprintf('%04x', int(rand(65536))) } 1..8;
    my $uuid = join('', @hex[0..1]) . '-' . $hex[2] . '-'
             . substr(sprintf('4%03x', int(rand(4096))), 0, 4) . '-'
             . substr(sprintf('%04x', int(rand(16384)) | 0x8000), 0, 4) . '-'
             . join('', @hex[5..7]);
    return $uuid;
}
```

This makes job IDs unguessable. Existing jobs with timestamp IDs continue to work (the ID is just a directory name).

**Step 2: Restrict CORS**

Change line 87 from:
```perl
"Access-Control-Allow-Origin: *\r\n"
```
To:
```perl
"Access-Control-Allow-Origin: http://$CFG{bindAddress}:$CFG{port}\r\n"
```

For localhost, this becomes `http://127.0.0.1:8083`. In Phase 2, it will be the configured server origin.

**Step 3: Commit**

```bash
git add review-server.pl
git commit -m "Harden localhost security: UUID job IDs, restrict CORS

Replace predictable timestamp job IDs with UUID v4. Restrict CORS
to configured server origin instead of wildcard."
```

---

# PHASE 2: MULTI-USER

---

### Task 8: Server-side authentication

**Files:**
- Modify: `review-server.pl` (new auth functions + middleware)
- Modify: `review-portal.html:710-733` (auth gate)
- Modify: `review-config.json` (add auth section)

**Context:** Currently auth is client-side only — the server has no access control on any endpoint. Before binding to the network, every `/api/*` endpoint needs server-side token validation.

**Step 1: Add auth config**

Add to `review-config.json`:
```json
{
  "auth": {
    "password": "Energy@WSU",
    "secret": "CHANGE_ME_RANDOM_STRING",
    "tokenExpiryHours": 24,
    "adminEmails": []
  }
}
```

**Step 2: Add token generation and validation functions**

```perl
use Digest::SHA qw(hmac_sha256_hex);

sub generate_token {
    my ($password) = @_;
    my $expiry = time() + ($CFG{auth}{tokenExpiryHours} || 24) * 3600;
    my $payload = "$password:$expiry";
    my $sig = hmac_sha256_hex($payload, $CFG{auth}{secret});
    return "$expiry:$sig";
}

sub validate_token {
    my ($token) = @_;
    return 0 unless $token && $token =~ /^(\d+):([a-f0-9]+)$/;
    my ($expiry, $sig) = ($1, $2);
    return 0 if time() > $expiry;
    my $expected = hmac_sha256_hex("$CFG{auth}{password}:$expiry", $CFG{auth}{secret});
    return $sig eq $expected;
}
```

**Step 3: Add POST /api/login endpoint**

```perl
    if ($method eq 'POST' && $path eq '/api/login') {
        my $data = eval { decode_json($body) };
        if (!$data || ($data->{password} || '') ne $CFG{auth}{password}) {
            send_json($c, 401, { error => 'Invalid password' });
            close $c; next;
        }
        my $token = generate_token($data->{password});
        send_json($c, 200, { token => $token });
        close $c; next;
    }
```

**Step 4: Add auth middleware to all /api/* endpoints**

Near the top of the request handler, after parsing headers, add:

```perl
    # Auth check for all /api/* endpoints (except login, health, OPTIONS)
    if ($path =~ m{^/api/} && $path ne '/api/login' && $path ne '/api/health' && $method ne 'OPTIONS') {
        my $auth = $headers{authorization} || '';
        my ($token) = $auth =~ /^Bearer\s+(.+)/;
        unless (validate_token($token)) {
            send_json($c, 401, { error => 'Authentication required' });
            close $c; next;
        }
    }
```

**Step 5: Update portal auth gate**

Remove the client-side password check. Instead, POST to `/api/login`:

```javascript
const AUTH_KEY = 'wsuReviewToken';

async function checkAuth() {
  const input = document.getElementById('authPass');
  const btn = document.querySelector('.auth-card button');
  btn.disabled = true;
  try {
    const resp = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: input.value }),
    });
    if (resp.ok) {
      const data = await resp.json();
      localStorage.setItem(AUTH_KEY, data.token);
      document.getElementById('authGate').style.display = 'none';
    } else {
      document.getElementById('authError').style.display = 'block';
      input.value = '';
      input.focus();
      btn.disabled = false;
    }
  } catch (err) {
    document.getElementById('authError').style.display = 'block';
    btn.disabled = false;
  }
}
```

**Step 6: Add Authorization header to all fetch calls**

Create a helper function and replace all `fetch()` calls in the portal:

```javascript
function apiFetch(url, opts = {}) {
  const token = localStorage.getItem(AUTH_KEY);
  if (token) {
    opts.headers = opts.headers || {};
    if (opts.headers instanceof Headers) {
      opts.headers.set('Authorization', 'Bearer ' + token);
    } else {
      opts.headers['Authorization'] = 'Bearer ' + token;
    }
  }
  return fetch(url, opts);
}
```

Replace every `fetch('/api/...'` with `apiFetch('/api/...'`. For FormData POSTs, let the browser set Content-Type (don't override).

**Step 7: Handle 401 responses — redirect to auth gate**

Add a response interceptor: if any `apiFetch` gets 401, clear the stored token and show the auth gate.

**Step 8: Commit**

```bash
git add review-server.pl review-portal.html review-config.json
git commit -m "Add server-side token authentication

POST /api/login validates password, returns HMAC token. All /api/*
endpoints require Bearer token. Portal sends token on every request.
401 response triggers re-authentication."
```

---

### Task 9: Job queue with sequential execution

**Files:**
- Modify: `review-server.pl:1475-1498` (concurrent job guard in submit handler)
- Modify: `review-server.pl:1383` (main accept loop — add idle-time queue processing)
- Modify: `review-portal.html` (queue position display)

**Context:** Currently the server rejects submissions with 409 if any review is running. Multi-user requires queuing. Reviews run sequentially (8 parallel Claude API calls per review = rate limit risk if 2 reviews run simultaneously).

**Step 1: Replace the 409 guard with queue logic**

Change the concurrent job guard to queue instead of reject:

```perl
        # Check for running jobs — if any are active, queue this one
        my $has_active = 0;
        my $queue_position = 0;
        if (opendir my $dh, $REVIEWS_DIR) {
            while (my $dir = readdir $dh) {
                next if $dir =~ /^\./;
                my $existing = read_job_json($dir);
                my $st = $existing->{status} || '';
                $has_active = 1 if $st eq 'Processing' || $st eq 'Analyzing';
                $queue_position++ if $st eq 'Queued';
            }
            closedir $dh;
        }
```

If `$has_active`, set the new job's status to `'Queued'` instead of `'Analyzing'`, and skip `spawn_analysis()`:

```perl
        if ($has_active) {
            $job->{status} = 'Queued';
            $job->{queuePosition} = $queue_position + 1;
            write_job_json($job_id, $job);
            send_json($c, 201, { id => $job_id, status => 'Queued', queuePosition => $queue_position + 1 });
            close $c; next;
        }
        # No active job — start analysis immediately
        $job->{status} = 'Analyzing';
        write_job_json($job_id, $job);
        send_json($c, 201, { id => $job_id, status => 'Analyzing' });
        close $c;
        spawn_analysis($job_id, $job);
        next;
```

**Step 2: Add queue drain logic to the main loop**

Use `IO::Select` with a timeout on the accept loop to periodically check the queue:

```perl
my $accept_sel = IO::Select->new($srv);

while (!$shutdown) {
    # Check for new connections (5-second timeout)
    if ($accept_sel->can_read(5)) {
        my $c = $srv->accept or next;
        binmode $c;
        $c->autoflush(1);
        # ... existing request handling ...
    }
    # During idle time, check if queued jobs should start
    drain_queue();
}
```

```perl
sub drain_queue {
    # Check if any job is currently active
    my @queued;
    if (opendir my $dh, $REVIEWS_DIR) {
        while (my $dir = readdir $dh) {
            next if $dir =~ /^\./;
            my $j = read_job_json($dir);
            next unless $j;
            my $st = $j->{status} || '';
            return if $st eq 'Processing' || $st eq 'Analyzing';  # something is running
            push @queued, { id => $dir, job => $j } if $st eq 'Queued';
        }
        closedir $dh;
    }
    return unless @queued;
    # Sort by submission time, start the oldest
    @queued = sort { ($a->{job}{submittedEpoch} || 0) <=> ($b->{job}{submittedEpoch} || 0) } @queued;
    my $next = $queued[0];
    print "[" . localtime() . "] Starting queued job $next->{id}\n";
    $next->{job}{status} = 'Analyzing';
    $next->{job}{queuePosition} = undef;
    write_job_json($next->{id}, $next->{job});
    spawn_analysis($next->{id}, $next->{job});
}
```

**Step 3: Add Queued status to portal**

Add CSS for `.job-status.queued` (same pattern as analyzing/awaiting). Add "Queued" filter button to queue tab. Show queue position in the status cell.

**Step 4: Update portal pollAnalysis to handle Queued status**

If the job is Queued, show "Your review is queued (position #N). Estimated wait: ~N min."

**Step 5: Commit**

```bash
git add review-server.pl review-portal.html
git commit -m "Add job queue with sequential execution

Jobs are queued when another review is active. Queue drains
automatically during idle time. Portal shows queue position."
```

---

### Task 10: Network binding configuration

**Files:**
- Modify: `review-config.json` (already has `bindAddress`)
- Modify: `review-server.pl:60-68` (startup banner)

**Context:** Phase 1 set `bindAddress` to `127.0.0.1`. For multi-user, change it to `0.0.0.0` in the config. This task just updates the startup banner to show the correct URL and adds documentation.

**Step 1: Update startup banner**

```perl
my $display_addr = $CFG{bindAddress} eq '0.0.0.0' ? '<your-hostname>' : $CFG{bindAddress};
print "WSU Review Portal Server\n";
print "  Listening: $CFG{bindAddress}:$port\n";
print "  Portal:    http://$display_addr:$port/review-portal.html\n";
print "  Health:    http://$display_addr:$port/api/health\n";
print "  Config:    " . ($cfg_loaded ? "$ROOT/review-config.json" : "defaults (no config file)") . "\n\n";
```

**Step 2: Update review-config.json default to 0.0.0.0**

Change `"bindAddress": "127.0.0.1"` to `"bindAddress": "0.0.0.0"` in the committed config file.

**Step 3: Commit**

```bash
git add review-server.pl review-config.json
git commit -m "Update network binding for multi-user access

Bind to 0.0.0.0 by default. Update startup banner to show
listen address and all URLs."
```

---

### Task 11: Email retry queue

**Files:**
- Modify: `review-server.pl:229-317` (email functions)
- Modify: `review-server.pl` (main loop idle processing — add email drain)

**Context:** Emails are sent inline during `check_job_status()`, blocking the request handler. Failures are never retried.

**Step 1: Replace inline email sending with queue file**

In `send_completion_email()`, instead of sending immediately, write a `pending-email.json` file:

```perl
sub queue_completion_email {
    my ($job_id, $job) = @_;
    return if $job->{emailSent};
    my $to = $job->{pmEmail} || '';
    $to =~ s/^\s+|\s+$//g;
    return unless $to =~ /.+\@.+/;
    my $cfg = $CFG{email} || {};
    return unless $cfg->{enabled};

    my $email_file = "$REVIEWS_DIR/$job_id/pending-email.json";
    return if -f $email_file;  # already queued
    open my $fh, '>', $email_file or return;
    print $fh encode_json({
        to       => $to,
        jobId    => $job_id,
        project  => $job->{projectName},
        attempts => 0,
        nextTry  => time(),
    });
    close $fh;
}
```

**Step 2: Add email drain function**

```perl
sub drain_email_queue {
    return unless ($CFG{email} || {})->{enabled};
    if (opendir my $dh, $REVIEWS_DIR) {
        while (my $dir = readdir $dh) {
            next if $dir =~ /^\./;
            my $ef = "$REVIEWS_DIR/$dir/pending-email.json";
            next unless -f $ef;
            open my $fh, '<', $ef or next;
            local $/; my $json = <$fh>; close $fh;
            my $email = eval { decode_json($json) } or next;
            next if time() < ($email->{nextTry} || 0);
            next if ($email->{attempts} || 0) >= 3;

            # Attempt to send
            my $ok = _send_email_now($dir, $email->{to});
            if ($ok) {
                unlink $ef;
                my $job = read_job_json($dir);
                if ($job) {
                    $job->{emailSent} = JSON::PP::true;
                    $job->{emailSentAt} = iso_now();
                    delete $job->{emailError};
                    write_job_json($dir, $job);
                }
            } else {
                $email->{attempts}++;
                # Backoff: 1min, 5min, 15min
                my @delays = (60, 300, 900);
                $email->{nextTry} = time() + ($delays[$email->{attempts} - 1] || 900);
                open my $wfh, '>', $ef or next;
                print $wfh encode_json($email);
                close $wfh;
            }
        }
        closedir $dh;
    }
}
```

**Step 3: Call drain_email_queue from the main loop idle time**

Add alongside `drain_queue()` in the idle processing block.

**Step 4: Replace send_completion_email with queue_completion_email at call sites**

**Step 5: Commit**

```bash
git add review-server.pl
git commit -m "Move email to async retry queue

Completion emails written to pending-email.json instead of sent inline.
Retried up to 3 times with backoff (1m, 5m, 15m) during idle time."
```

---

### Task 12: Phase 2 security (rate limiting, audit log, download auth)

**Files:**
- Modify: `review-server.pl` (add rate limiter, audit logging, download auth check)

**Context:** With the server on the network, we need: rate limiting to prevent API credit abuse, audit logging for accountability, and download authorization so users can only access their own jobs.

**Step 1: Add rate limiter**

Simple in-memory rate limiter using a hash of IP → [timestamps]:

```perl
my %rate_limits;  # ip => { submit => [timestamps], api => [timestamps] }

sub check_rate_limit {
    my ($ip, $bucket, $max, $window_sec) = @_;
    my $now = time();
    $rate_limits{$ip}{$bucket} = [ grep { $_ > $now - $window_sec } @{$rate_limits{$ip}{$bucket} || []} ];
    return 0 if scalar @{$rate_limits{$ip}{$bucket}} >= $max;
    push @{$rate_limits{$ip}{$bucket}}, $now;
    return 1;
}
```

Add checks:
- Submit endpoint: `check_rate_limit($peer_ip, 'submit', 5, 3600)` — 5 submissions/hour
- All API endpoints: `check_rate_limit($peer_ip, 'api', 60, 60)` — 60 requests/minute

Return 429 Too Many Requests if exceeded.

**Step 2: Add audit logging**

Append to `access.log` on every API request:

```perl
sub audit_log {
    my ($ip, $method, $path, $status_code) = @_;
    my $logfile = "$ROOT/access.log";
    if (open my $fh, '>>', $logfile) {
        printf $fh "%s %s %s %s %d\n", iso_now(), $ip, $method, $path, $status_code;
        close $fh;
    }
}
```

Call after every `send_json()` / `send_response()` for API endpoints.

**Step 3: Add download authorization**

In the download and logs endpoints, load the job and check if the requesting user's email (from the token or a header) matches `pmEmail`, OR if the user is in the admin list:

```perl
    # Check ownership (admin bypass)
    my $requester_email = $headers{'x-user-email'} || '';
    my $is_admin = grep { $_ eq $requester_email } @{$CFG{auth}{adminEmails} || []};
    if (!$is_admin && $job->{pmEmail} && lc($requester_email) ne lc($job->{pmEmail})) {
        send_json($c, 403, { error => 'You do not have access to this job' });
        close $c; next;
    }
```

The portal sends `X-User-Email` header alongside the Bearer token. Add this to `apiFetch()`.

**Step 4: Commit**

```bash
git add review-server.pl review-portal.html
git commit -m "Add rate limiting, audit logging, and download authorization

5 submits/hr, 60 API calls/min per IP. All API access logged to
access.log. Downloads restricted to job owner or admin."
```

---

# PHASE 3: IT HANDOFF

---

### Task 13: NSSM Windows Service setup

**Files:**
- Create: `install-service.bat`
- Create: `uninstall-service.bat`

**Context:** NSSM (Non-Sucking Service Manager) wraps any executable as a Windows service. This replaces the Phase 1 watchdog script with proper service management.

**Step 1: Create install-service.bat**

```bat
@echo off
REM Install WSU Review Server as a Windows Service using NSSM
REM Prerequisites: NSSM must be on PATH (download from https://nssm.cc/)

set SERVICE_NAME=WSUReviewServer
set SCRIPT_DIR=%~dp0

echo Installing %SERVICE_NAME%...

nssm install %SERVICE_NAME% "C:\Strawberry\perl\bin\perl.exe" "%SCRIPT_DIR%review-server.pl"
nssm set %SERVICE_NAME% AppDirectory "%SCRIPT_DIR%"
nssm set %SERVICE_NAME% AppStdout "%SCRIPT_DIR%logs\service-stdout.log"
nssm set %SERVICE_NAME% AppStderr "%SCRIPT_DIR%logs\service-stderr.log"
nssm set %SERVICE_NAME% AppStdoutCreationDisposition 4
nssm set %SERVICE_NAME% AppStderrCreationDisposition 4
nssm set %SERVICE_NAME% AppRotateFiles 1
nssm set %SERVICE_NAME% AppRotateSeconds 86400
nssm set %SERVICE_NAME% AppRotateBytes 10485760
nssm set %SERVICE_NAME% AppRestartDelay 5000
nssm set %SERVICE_NAME% Description "WSU Facilities Services - Construction Document Review Server"

if not exist "%SCRIPT_DIR%logs" mkdir "%SCRIPT_DIR%logs"

echo.
echo Service installed. Start with: nssm start %SERVICE_NAME%
echo Configure with: nssm edit %SERVICE_NAME%
```

**Step 2: Create uninstall-service.bat**

```bat
@echo off
set SERVICE_NAME=WSUReviewServer
nssm stop %SERVICE_NAME%
nssm remove %SERVICE_NAME% confirm
echo Service removed.
```

**Step 3: Commit**

```bash
git add install-service.bat uninstall-service.bat
git commit -m "Add NSSM Windows Service install/uninstall scripts

WSUReviewServer service auto-starts, auto-restarts on crash, rotates
logs daily. Replaces manual server startup and watchdog script."
```

---

### Task 14: Admin panel

**Files:**
- Create: `review-admin.html`
- Modify: `review-server.pl` (add admin API endpoints)

**Context:** An admin page for monitoring server health, viewing timing data, and managing jobs. Protected by a separate admin check.

**Step 1: Add admin API endpoints**

```perl
    # GET /api/admin/stats — server statistics (admin only)
    if ($method eq 'GET' && $path eq '/api/admin/stats') {
        # Verify admin
        my $email = $headers{'x-user-email'} || '';
        unless (grep { $_ eq $email } @{$CFG{auth}{adminEmails} || []}) {
            send_json($c, 403, { error => 'Admin access required' });
            close $c; next;
        }
        # Gather stats
        my %stats = (
            uptime       => time() - $^T,
            pid          => $$,
            diskUsage    => 0,
            jobCounts    => { active => 0, queued => 0, complete => 0, failed => 0 },
            recentJobs   => [],
        );
        # ... populate from job directories ...
        send_json($c, 200, \%stats);
        close $c; next;
    }

    # POST /api/admin/force-fail/{id} — force a stuck job to Failed (admin only)
    # POST /api/admin/purge-old — delete jobs older than N days (admin only)
```

**Step 2: Create review-admin.html**

A simple single-file HTML page (same pattern as review-portal.html) with:
- Server status card (uptime, PID, disk usage)
- Job counts by status (active/queued/complete/failed)
- Table of recent jobs with timing data (from timing.json)
- Action buttons: force-fail stuck job, purge old jobs
- Auto-refresh every 30 seconds

Use the same WSU CSS design system (crimson header, card layout, dark mode toggle).

**Step 3: Commit**

```bash
git add review-admin.html review-server.pl
git commit -m "Add admin panel with server stats and job management

Displays uptime, disk usage, job counts, per-job timing data.
Admin actions: force-fail stuck jobs, purge old jobs."
```

---

### Task 15: Log rotation and job cleanup

**Files:**
- Modify: `review-server.pl` (add cleanup to idle processing)
- Modify: `review-config.json` (add cleanup config)

**Context:** Without cleanup, the reviews directory grows unbounded. Old completed jobs should be archived, and server logs should rotate.

**Step 1: Add cleanup config**

```json
{
  "cleanup": {
    "archiveAfterDays": 90,
    "diskWarnMB": 5000
  }
}
```

**Step 2: Add periodic cleanup function**

Run once per hour (track last run time in a variable):

```perl
my $last_cleanup = 0;

sub periodic_cleanup {
    return if time() - $last_cleanup < 3600;  # once per hour
    $last_cleanup = time();

    my $archive_days = $CFG{cleanup}{archiveAfterDays} || 90;
    my $cutoff = time() - ($archive_days * 86400);
    my $archive_dir = "$REVIEWS_DIR/archive";

    if (opendir my $dh, $REVIEWS_DIR) {
        while (my $dir = readdir $dh) {
            next if $dir =~ /^\.|^archive$/;
            my $job = read_job_json($dir);
            next unless $job;
            my $st = $job->{status} || '';
            next unless $st eq 'Complete' || $st eq 'Failed';
            my $completed = $job->{submittedEpoch} || 0;
            next unless $completed < $cutoff;
            # Archive: move directory
            make_path($archive_dir) unless -d $archive_dir;
            rename "$REVIEWS_DIR/$dir", "$archive_dir/$dir";
            print "[CLEANUP] Archived job $dir\n";
        }
        closedir $dh;
    }

    # Disk usage warning
    # (platform-specific: use du on Unix, or count file sizes on Windows)
}
```

**Step 3: Call from main loop idle processing**

Add `periodic_cleanup()` alongside `drain_queue()` and `drain_email_queue()`.

**Step 4: Commit**

```bash
git add review-server.pl review-config.json
git commit -m "Add automatic job archival and disk usage monitoring

Completed/failed jobs archived after 90 days (configurable).
Disk usage checked hourly with configurable warning threshold."
```

---

### Task 16: Deployment documentation

**Files:**
- Create: `docs/DEPLOYMENT.txt`

**Context:** Step-by-step guide for setting up the review server on a fresh Windows machine. Written for WSU IT staff who haven't seen the codebase.

**Step 1: Write DEPLOYMENT.txt**

Cover:
1. Prerequisites (Perl, Python 3, pdfplumber, Claude CLI, NSSM)
2. Installation steps (clone repo, install dependencies, create config)
3. Configuration reference (every field in review-config.json explained)
4. Service installation (install-service.bat)
5. Firewall setup (open port in Windows Firewall)
6. Verification (health check, test submission)
7. Operations runbook (restart service, check logs, clear stuck jobs, rotate API keys, purge old jobs)
8. Troubleshooting (common errors and fixes)

**Step 2: Commit**

```bash
git add docs/DEPLOYMENT.txt
git commit -m "Add deployment documentation for IT handoff

Step-by-step setup guide, config reference, operations runbook,
and troubleshooting guide for WSU IT staff."
```

---

## Task Summary

| # | Phase | Task | Files |
|---|-------|------|-------|
| 1 | 1 | Config file system | review-config.json, review-server.pl |
| 2 | 1 | Claude CLI timeout wrappers | review-server.pl |
| 3 | 1 | Per-phase timing logs | review-server.pl |
| 4 | 1 | Upload validation | review-server.pl |
| 5 | 1 | Server process management | review-server.pl |
| 6 | 1 | Watchdog script | review-watchdog.sh |
| 7 | 1 | Localhost security hardening | review-server.pl |
| 8 | 2 | Server-side authentication | review-server.pl, review-portal.html, review-config.json |
| 9 | 2 | Job queue | review-server.pl, review-portal.html |
| 10 | 2 | Network binding | review-server.pl, review-config.json |
| 11 | 2 | Email retry queue | review-server.pl |
| 12 | 2 | Rate limiting, audit log, download auth | review-server.pl, review-portal.html |
| 13 | 3 | NSSM Windows Service | install-service.bat, uninstall-service.bat |
| 14 | 3 | Admin panel | review-admin.html, review-server.pl |
| 15 | 3 | Log rotation + job cleanup | review-server.pl, review-config.json |
| 16 | 3 | Deployment documentation | docs/DEPLOYMENT.txt |
