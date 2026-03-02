# Review Pipeline Optimization Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Cut review pipeline runtime from ~84 min to ~36 min, eliminate dropped disciplines from JSON errors, add performance tracking, and document production migration for IT handoff.

**Architecture:** Seven changes across the pipeline: a new Phase 0 PDF pre-extraction step eliminates redundant pdfplumber parsing; the wave limit increases to 8 (all parallel); JSON sanitization and retry logic prevent dropped disciplines; duration/size tracking feeds future optimization; progress reporting gives real-time discipline-level visibility; and a production migration guide documents the path from Perl prototype to deployable web service.

**Tech Stack:** Perl (server/watcher), Bash (pipeline script), Python (synthesis/reports), JavaScript (portal UI). No new dependencies.

---

## Context for the Implementer

### File Locations (main repo = worktree)

| File | Role | Lines |
|------|------|-------|
| `review-server.pl` | HTTP server, `spawn_review()` generates `run-review.sh` | ~1310 |
| `review-watcher.pl` | Background poller, updates `job.json` progress/status | ~900 |
| `review-portal.html` | Frontend, job queue, progress tracker | ~1114 |
| `synthesize.py` | Phase 2a: merges discipline JSONs → `review-data.json` | ~569 |
| `generate_reports.py` | Phase 3: produces `.docx`, `.xlsx`, `.txt` reports | ~1000 |

### Pipeline Flow (current)

```
Submit → Phase 1 (3 waves × 3 CLI) → Phase 2a (Python) → Phase 2b (Haiku) → Phase 3 (Python) → Complete
         ~83 min                       ~20 sec              ~17 sec            ~1 sec
```

### Pipeline Flow (after optimization)

```
Submit → Phase 0 (PDF extract) → Phase 1 (1 wave × 8 CLI) → Phase 2a → 2b → 3 → Complete
         ~30 sec                  ~36 min                     ~20 sec   ~17s  ~1s
```

### No Smartsheet

The review pipeline has NO Smartsheet integration. The watcher polls the local filesystem only. Smartsheet is only used in the water conservation dashboard — completely separate.

### IT Handoff Context

This tool is being prototyped for eventual handoff to WSU IT for integration as a password-protected page on a public website. All changes should be documented, modular, and avoid tight coupling to the current Windows/Perl environment.

---

## Task 1: PDF Pre-Extraction (Phase 0)

**Why:** Each of the 8 Claude CLI processes independently spawns pdfplumber to parse the same 40MB PDF, using 1-2GB RAM each. Extracting once drops total memory from ~5GB to ~500MB and eliminates startup overhead.

**Files:**
- Create: `extract_pdf.py`
- Modify: `review-server.pl:668-739` (prompt generation)
- Modify: `review-server.pl:886-950` (Phase 1 script generation)

### Step 1: Create `extract_pdf.py`

This script extracts text from the PDF once, producing one text file per page. The Claude CLI will read these text files instead of the raw PDF.

```python
#!/usr/bin/env python3
"""Extract text from PDF pages for review pipeline.

Produces one .txt file per page in the output directory.
Usage: python extract_pdf.py <input.pdf> <output_dir>
"""
import sys
import os

def extract_pages(pdf_path, output_dir):
    """Extract text from each page of the PDF."""
    try:
        import pdfplumber
    except ImportError:
        print("ERROR: pdfplumber not installed. Run: pip install pdfplumber", file=sys.stderr)
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    page_count = 0

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ''
            # Also extract tables as structured text
            tables = page.extract_tables() or []
            table_text = ''
            for table in tables:
                for row in table:
                    cells = [str(c or '') for c in row]
                    table_text += ' | '.join(cells) + '\n'

            page_file = os.path.join(output_dir, f'page-{i+1:04d}.txt')
            with open(page_file, 'w', encoding='utf-8') as f:
                f.write(f'--- PAGE {i+1} ---\n')
                f.write(text)
                if table_text:
                    f.write('\n\n--- TABLES ---\n')
                    f.write(table_text)

            page_count += 1

    # Write manifest
    manifest_file = os.path.join(output_dir, 'manifest.txt')
    with open(manifest_file, 'w', encoding='utf-8') as f:
        f.write(f'Pages: {page_count}\n')
        f.write(f'Source: {os.path.basename(pdf_path)}\n')
        for i in range(page_count):
            f.write(f'page-{i+1:04d}.txt\n')

    print(f'Extracted {page_count} pages to {output_dir}')
    return page_count

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f'Usage: {sys.argv[0]} <input.pdf> <output_dir>', file=sys.stderr)
        sys.exit(1)
    extract_pages(sys.argv[1], sys.argv[2])
```

### Step 2: Add Phase 0 to `run-review.sh` generation

In `review-server.pl` `spawn_review()`, add Phase 0 between Python discovery (line ~59) and Phase 1 (line ~62). Find the line:

```perl
    # === PHASE 1: Batched discipline scans
```

Insert before it:

```perl
    # === PHASE 0: Extract PDF text (one-time, saves 7 redundant pdfplumber parses) ===
    print $fh "echo \"Phase 0: Extracting PDF text...\" >> \"$progress_log\"\n";
    print $fh "\"\$PYTHON\" \"$ROOT/extract_pdf.py\" \"$job_dir/input.pdf\" \"$job_dir/pages\"\n";
    print $fh "EXTRACT_EXIT=\$?\n";
    print $fh "if [ \"\$EXTRACT_EXIT\" -ne 0 ]; then\n";
    print $fh "  echo \"ERROR: PDF text extraction failed (exit \$EXTRACT_EXIT)\" > \"$output_dir/FAILED\"\n";
    print $fh "  exit 1\n";
    print $fh "fi\n";
    print $fh "echo \"Phase 0 complete.\" >> \"$progress_log\"\n\n";
```

### Step 3: Update discipline prompts to read page text files instead of PDF

In `spawn_review()`, find the prompt template (lines 668-739) where it says:

```perl
    print $pf "1. Read the PDF at $job_rel/input.pdf.\n";
    print $pf "   Focus on sheets relevant to this discipline but review the full drawing set for context.\n";
```

Replace with:

```perl
    print $pf "1. Read the extracted page text files in $job_rel/pages/.\n";
    print $pf "   Start by reading $job_rel/pages/manifest.txt for the page list.\n";
    print $pf "   Focus on pages relevant to this discipline but review all pages for context.\n";
    print $pf "   These are pre-extracted text from the construction drawings PDF.\n";
```

### Step 4: Verify and commit

```bash
# Test extract_pdf.py standalone
python extract_pdf.py "reviews/20260225-171936/input.pdf" /tmp/test-pages
ls /tmp/test-pages | head -10
cat /tmp/test-pages/manifest.txt

git add extract_pdf.py
git add review-server.pl
git commit -m "Add Phase 0: one-time PDF text extraction before discipline scans"
```

---

## Task 2: Remove Wave Limit (All 8 Parallel)

**Why:** Waves serialize disciplines unnecessarily. With 32GB RAM and API-bound workloads, all 8 can run simultaneously. Reduces Phase 1 from ~83 min to ~36 min.

**Files:**
- Modify: `review-server.pl:861-883` (wave generation logic)

### Step 1: Change MAX_PARALLEL from 3 to 8

In `spawn_review()`, find the wave chunking logic around line 861:

```perl
    my $MAX_PARALLEL = 3;
```

Change to:

```perl
    my $MAX_PARALLEL = 8;  # all disciplines run simultaneously (API-bound, not CPU-bound)
```

### Step 2: Remove wave priority sorting

The `%wave_priority` hash and sorting logic (lines 861-883) was designed to interleave slow/fast disciplines across waves. With a single wave this is unnecessary. However, **leave it in place** — it's harmless and if we ever need to reduce parallelism again, it'll still work.

### Step 3: Update progress detail text

In `review-server.pl`, find where `progressDetail` is set for Phase 1 scanning. In `check_job_status()` (review-watcher.pl or review-server.pl), the detail says `"Scanning 8 disciplines in waves..."`. Update to:

```perl
    $job->{progressDetail} = "Scanning: $done of $expected disciplines complete";
```

This replaces the static message with a live counter. Find the section in the watcher/server where `progressDetail` is set during Phase 1 and update it.

### Step 4: Commit

```bash
git add review-server.pl
git commit -m "Increase max parallel disciplines from 3 to 8 for ~2x speedup"
```

---

## Task 3: Duration and File Size Tracking

**Why:** Correlating job duration with PDF size and prompt size helps identify optimization targets. The user wants this data visible in the queue.

**Files:**
- Modify: `review-server.pl:1144-1156` (job.json creation)
- Modify: `review-server.pl:319-554` (job completion in check_job_status)
- Modify: `review-portal.html` (queue table display)

### Step 1: Add `pdfSizeBytes` to job.json at creation time

In `spawn_review()`, after saving the PDF to disk (line ~1140), add the file size to the job hash. Find:

```perl
        my $job = {
            id               => $job_id,
```

Add `pdfSizeBytes` to the hash:

```perl
        my $pdf_size = -s "$job_dir/input.pdf";
        my $job = {
            id               => $job_id,
            pdfSizeBytes     => $pdf_size,
```

### Step 2: Add `durationSeconds` on job completion

In `check_job_status()` (in `review-server.pl`), when the job completes (COMPLETE sentinel found), calculate and store the duration. Find where `status` is set to `'Complete'` and add:

```perl
        $job->{durationSeconds} = time() - ($job->{submittedEpoch} || time());
```

Do the same for Failed jobs so we know how long it ran before failing.

### Step 3: Display duration and file size in the portal queue

In `review-portal.html`, in the job queue rendering function, add duration and file size to completed/failed jobs. Find where the status badge and tracker are rendered for completed jobs. After the tracker, add:

```javascript
// Duration display for completed/failed jobs
if (j.durationSeconds) {
    const dur = fmtElapsed(j.durationSeconds);
    html += `<div style="font-size:.75rem;color:var(--text-light);margin-top:.25rem">`;
    html += `Duration: ${dur}`;
    if (j.pdfSizeBytes) {
        const mb = (j.pdfSizeBytes / 1048576).toFixed(1);
        html += ` &middot; PDF: ${mb} MB`;
    }
    html += `</div>`;
}
```

### Step 4: Commit

```bash
git add review-server.pl review-portal.html
git commit -m "Track and display job duration and PDF file size"
```

---

## Task 4: JSON Output Sanitization

**Why:** Claude sometimes produces unescaped double quotes in measurement strings like `5'-0"`. This broke `arch-finishes` in the last run, dropping an entire discipline from the final reports.

**Files:**
- Modify: `review-server.pl:886-950` (Phase 1 post-processing in run-review.sh)

### Step 1: Add JSON repair function to run-review.sh

In `spawn_review()`, after Phase 1 completes and before the validation check, add a sanitization step. Find the line that generates:

```perl
    print $fh "echo \"Phase 1 complete ($n_groups disciplines in $n_waves waves).\" >> \"$progress_log\"\n\n";
```

Insert after it:

```perl
    # JSON sanitization: fix unescaped quotes in measurement strings
    print $fh "# --- Post-process: fix common JSON errors ---\n";
    print $fh "for jf in \"$output_dir\"/discipline-*-findings.json; do\n";
    print $fh "  [ -f \"\$jf\" ] || continue\n";
    print $fh "  # Test if JSON is valid\n";
    print $fh "  \"\$PYTHON\" -c \"import json,sys; json.load(open(sys.argv[1]))\" \"\$jf\" 2>/dev/null && continue\n";
    print $fh "  echo \"Repairing malformed JSON: \$(basename \$jf)\"\n";
    print $fh "  \"\$PYTHON\" -c \"\n";
    print $fh "import re, sys\n";
    print $fh "with open(sys.argv[1], 'r') as f: text = f.read()\n";
    print $fh "# Fix unescaped quotes inside JSON string values (measurement notations)\n";
    print $fh "# Match pattern: content between field quotes that contains unescaped internal quotes\n";
    print $fh "def fix_quotes(text):\n";
    print $fh "    # Replace inch marks inside JSON strings: digits followed by unescaped quote\n";
    print $fh "    # e.g. 5'-0\\\" or 3/4\\\" — the double-quote is an inch mark, not a JSON delimiter\n";
    print $fh "    result = re.sub(r'(\\\\d)\\\"(\\\\s)', r'\\\\1 in.\\\\2', text)\n";
    print $fh "    return result\n";
    print $fh "fixed = fix_quotes(text)\n";
    print $fh "import json\n";
    print $fh "try:\n";
    print $fh "    json.loads(fixed)\n";
    print $fh "    with open(sys.argv[1], 'w') as f: f.write(fixed)\n";
    print $fh "    print('  Repaired successfully')\n";
    print $fh "except json.JSONDecodeError as e:\n";
    print $fh "    print(f'  Could not auto-repair: {e}', file=sys.stderr)\n";
    print $fh "\" \"\$jf\"\n";
    print $fh "done\n\n";
```

### Step 2: Add JSON escaping reminder to discipline prompts

In `spawn_review()`, in the prompt template (lines 668-739), add to the OUTPUT FORMAT section after the schema. Find:

```perl
    print $pf "CRITICAL: Use exactly this filename.";
```

Add after the existing instructions:

```perl
    print $pf "CRITICAL: Properly escape all double quotes inside JSON string values.\n";
    print $pf "   Architectural measurements must NOT contain unescaped quotes.\n";
    print $pf "   WRONG: \"5'-0\" from wall\"   CORRECT: \"5 ft-0 in. from wall\"\n";
    print $pf "   WRONG: \"3/4\" pipe\"         CORRECT: \"3/4 in. pipe\"\n";
```

### Step 3: Commit

```bash
git add review-server.pl
git commit -m "Add JSON sanitization for unescaped measurement quotes in discipline output"
```

---

## Task 5: Retry Failed Disciplines

**Why:** When a discipline produces invalid JSON (even after sanitization), the pipeline should retry it once rather than silently losing that discipline's data.

**Files:**
- Modify: `review-server.pl:886-1000` (Phase 1 validation in run-review.sh generation)

### Step 1: Add retry loop after Phase 1 validation

In `spawn_review()`, find the Phase 1 validation that counts findings files (after the sanitization step from Task 4). The current code looks like:

```perl
    print $fh "FOUND=0\n";
    print $fh "for f in \"$output_dir\"/discipline-*-findings.json; do\n";
    print $fh "  [ -f \"\$f\" ] && FOUND=\$((FOUND + 1))\n";
    print $fh "done\n";
```

Replace the validation section with a retry loop:

```perl
    # Validate Phase 1 output and retry failed disciplines
    print $fh "FOUND=0\n";
    print $fh "MISSING=\"\"\n";
    print $fh "for key in $discipline_keys_str; do\n";
    print $fh "  if [ -f \"$output_dir/discipline-\${key}-findings.json\" ]; then\n";
    print $fh "    # Verify JSON is parseable\n";
    print $fh "    if \"\$PYTHON\" -c \"import json,sys; json.load(open(sys.argv[1]))\" \"$output_dir/discipline-\${key}-findings.json\" 2>/dev/null; then\n";
    print $fh "      FOUND=\$((FOUND + 1))\n";
    print $fh "    else\n";
    print $fh "      echo \"Invalid JSON for \$key — will retry\"\n";
    print $fh "      rm \"$output_dir/discipline-\${key}-findings.json\"\n";
    print $fh "      MISSING=\"\$MISSING \$key\"\n";
    print $fh "    fi\n";
    print $fh "  else\n";
    print $fh "    MISSING=\"\$MISSING \$key\"\n";
    print $fh "  fi\n";
    print $fh "done\n\n";

    print $fh "if [ -n \"\$MISSING\" ]; then\n";
    print $fh "  echo \"Retrying failed disciplines:\$MISSING\" >> \"$progress_log\"\n";
    print $fh "  for key in \$MISSING; do\n";
    print $fh "    echo \"  Retrying: \$key...\"\n";
    print $fh "    PROMPT_VAR=\$(cat \"$job_dir/prompt-\${key}.txt\")\n";
    print $fh "    \"$claude_path\" -p \"\$PROMPT_VAR\" \\\n";
    print $fh "      --model sonnet \\\n";
    print $fh "      --allowedTools Read Write \\\n";
    print $fh "      --dangerously-skip-permissions \\\n";
    print $fh "      --output-format text \\\n";
    print $fh "      > \"$output_dir/\${key}-retry-stdout.log\" \\\n";
    print $fh "      2> \"$output_dir/\${key}-retry-stderr.log\"\n";
    print $fh "    # Run sanitization on retry output\n";
    print $fh "    if [ -f \"$output_dir/discipline-\${key}-findings.json\" ]; then\n";
    print $fh "      if \"\$PYTHON\" -c \"import json,sys; json.load(open(sys.argv[1]))\" \"$output_dir/discipline-\${key}-findings.json\" 2>/dev/null; then\n";
    print $fh "        FOUND=\$((FOUND + 1))\n";
    print $fh "        echo \"  Retry succeeded for \$key\"\n";
    print $fh "      else\n";
    print $fh "        echo \"  Retry still produced invalid JSON for \$key\"\n";
    print $fh "      fi\n";
    print $fh "    else\n";
    print $fh "      echo \"  Retry produced no output for \$key\"\n";
    print $fh "    fi\n";
    print $fh "  done\n";
    print $fh "fi\n\n";
```

Note: The implementer needs to build `$discipline_keys_str` as a space-separated string of discipline keys (e.g., `"fire-protection plumbing communications electrical arch-finishes civil-site hvac-controls arch-structure"`). This should be constructed alongside the existing `@groups` iteration in `spawn_review()`.

Also note: `$claude_path` needs to reference the same Claude CLI path used in Phase 1. This is already stored — find it near line 73 of the generated script (e.g., `"C:/Users/john.slagboom/AppData/Roaming/Claude/claude-code/2.1.51/claude.exe"`). Store it in a bash variable at the top of the script so the retry can reuse it.

### Step 2: Update failure threshold

Change the existing failure check from "0 files = fail" to "fewer than half = fail":

```perl
    print $fh "echo \"Phase 1 produced \$FOUND of $n_groups findings files.\"\n";
    print $fh "if [ \"\$FOUND\" -lt 1 ]; then\n";
```

Keep as-is. Even with retries, if zero disciplines produce valid JSON, the pipeline should still fail.

### Step 3: Commit

```bash
git add review-server.pl
git commit -m "Retry disciplines that produce invalid JSON before moving to synthesis"
```

---

## Task 6: Progress Reporting Improvements

**Why:** The API showed "7% / Scanning 8 disciplines in waves..." for the entire 84-minute run. Individual discipline completions should update in real-time.

**Files:**
- Modify: `review-server.pl` (check_job_status function)
- Modify: `review-portal.html` (discipline detail rendering)

### Step 1: Improve discipline completion detection in check_job_status

In `review-server.pl`, find `check_job_status()`. The existing discipline status tracking detects `discipline-*-findings.json` files. It needs to update progress percentage based on how many disciplines have completed. Find the section where `disciplineStatus` is updated and progress percentage is calculated during Phase 1.

Update the progress calculation so that during Phase 1:

```perl
    # Phase 1 progress: 7% base + (done/expected * 5%)
    # Each completed discipline adds to progress
    my $done = 0;
    for my $ds (@{$job->{disciplineStatus} || []}) {
        $done++ if ($ds->{status} || '') eq 'complete';
    }
    if ($done > 0 && $pct < 15) {
        $pct = 7 + int(($done / $expected) * 5);
        $job->{progressDetail} = "Scanning: $done of $expected disciplines complete";
    }
```

### Step 2: Add wave timing to the discipline detail display

In `review-portal.html`, the `buildDiscDetail()` function shows per-discipline status with timestamps. This already works — just verify that the completedAt timestamps propagate correctly now that all 8 run in parallel.

No code change needed here if `check_job_status` correctly detects per-discipline completion.

### Step 3: Commit

```bash
git add review-server.pl review-portal.html
git commit -m "Update progress percentage as disciplines complete during Phase 1"
```

---

## Task 7: Production Migration Guide

**Why:** This tool will be handed off to WSU IT for integration as a password-protected page on a public website. The IT team needs a clear migration path from the current Perl prototype to a production deployment.

**Files:**
- Create: `docs/PRODUCTION-MIGRATION.txt`

### Step 1: Write the migration guide

```
WSU COMPLIANCE REVIEW TOOL — PRODUCTION MIGRATION GUIDE
=========================================================

PURPOSE
-------
This document maps the current prototype architecture to a
production-ready deployment for WSU IT integration as a
password-protected page on a public website.

CURRENT PROTOTYPE ARCHITECTURE
-------------------------------
Component             Technology       Purpose
Server                Perl (HTTP)      Serves frontend + API routes
Frontend              Single HTML      Job submission + queue + results
Pipeline Script       Bash             Orchestrates 3-phase review
Phase 1 (Scanning)    Claude CLI       8 parallel discipline scans via Sonnet
Phase 2a (Synthesis)  Python           Deterministic JSON merge (zero tokens)
Phase 2b (Summary)    Claude CLI       Executive summary via Haiku
Phase 3 (Reports)     Python           .docx + .xlsx + .txt generation
Watcher               Perl             Polls filesystem for job updates
PDF Extraction        Python           Pre-extracts text (pdfplumber)

PRODUCTION TARGET ARCHITECTURE
------------------------------
Component             Technology              Migration Path
Web Server            nginx + Node.js/Django   Replace Perl HTTP server
Frontend              Same HTML (or React)     Minimal changes needed
Authentication        WSU SSO / OAuth          Replace hardcoded password
Database              PostgreSQL               Replace job.json files
Job Queue             Redis + Celery (or BullMQ) Replace bash script orchestration
API Integration       Anthropic HTTP API       Replace Claude CLI with direct API calls
File Storage          S3-compatible or NFS     Replace local filesystem
PDF Extraction        Same Python script       No change needed
Synthesis             Same Python script       No change needed
Report Generation     Same Python script       No change needed

MIGRATION STEPS (RECOMMENDED ORDER)
------------------------------------

Step 1: Replace Claude CLI with Direct API Calls
  WHY:  Eliminates CLI installation requirement, removes pdfplumber
        subprocess spawning, enables streaming progress.
  HOW:  Use Anthropic's HTTP API (or Python SDK) directly.
        Send PDF content as base64 in the API request.
        Each discipline scan = one API call to claude-sonnet.
        Executive summary = one API call to claude-haiku.
  NOTE: The discipline prompts (prompt-*.txt) transfer directly
        as the "user" message in the API call. No rewriting needed.

Step 2: Replace Perl Server with Standard Web Framework
  WHY:  IT teams are more familiar with Node.js/Django/Flask.
  HOW:  Port the API routes from review-server.pl:
        - POST /api/submit (multipart upload)
        - GET  /api/jobs (job listing)
        - GET  /api/jobs/:id/download/:file (file download)
        - DELETE /api/jobs/:id (cleanup)
        The route logic is straightforward HTTP CRUD.
  NOTE: The frontend HTML can be served as a static file
        by nginx. Only the API needs a backend framework.

Step 3: Add Proper Authentication
  WHY:  Hardcoded password is not production-ready.
  HOW:  Integrate WSU's existing SSO/CAS system or OAuth.
        The frontend auth gate (id="authGate") can be replaced
        with a server-side session check.

Step 4: Replace Filesystem with Database + Object Storage
  WHY:  job.json files don't scale; file locks are fragile.
  HOW:  PostgreSQL table for job metadata (replaces job.json).
        S3-compatible storage for PDFs and output files.
        The synthesize.py and generate_reports.py scripts
        read/write local files — wrap them with download-from-S3
        and upload-to-S3 steps.

Step 5: Replace Bash Orchestration with Job Queue
  WHY:  Bash scripts can't retry, scale, or distribute.
  HOW:  Celery (Python) or BullMQ (Node.js) for job management.
        Each discipline scan = one queued task.
        Phase transitions = task chaining/workflow.
        Built-in retry, timeout, and progress reporting.

COMPONENTS THAT TRANSFER DIRECTLY
----------------------------------
These require zero or minimal changes for production:

1. Discipline Prompts (prompt-*.txt templates)
   The prompt text is the core IP. It transfers directly as
   API request content regardless of infrastructure.

2. synthesize.py
   Pure Python, reads JSON files, writes JSON file. No network
   dependencies. Just needs input/output paths configured.

3. generate_reports.py
   Pure Python, reads review-data.json, writes .docx/.xlsx/.txt.
   Uses openpyxl and python-docx (standard libraries).

4. extract_pdf.py
   Pure Python, reads PDF, writes text files. Uses pdfplumber.

5. Frontend HTML/CSS/JS
   The review-portal.html is self-contained. The API endpoints
   it calls (/api/submit, /api/jobs, etc.) have the same
   interface regardless of backend technology.

6. WSU Design Standards Skills
   The compliance standards are stored as Claude Code skills
   (wsu-div-* files). These transfer as prompt content for
   the API calls. They are the institutional knowledge base.

SECURITY CONSIDERATIONS
------------------------
- PDF uploads must be size-limited (current: 100MB max)
- API rate limiting on /api/submit (one concurrent job)
- Output files should be access-controlled per user/session
- Claude API key must be server-side only (never in frontend)
- Sanitize all user inputs (project name, email, etc.)
- The current XSS escaping in review-portal.html should be
  preserved in any frontend rewrite

RESOURCE REQUIREMENTS (PRODUCTION)
-----------------------------------
- 2-4 CPU cores (Python + API calls are I/O bound)
- 4GB RAM minimum (PDF extraction peak)
- 10GB disk for active jobs (cleaned up after download)
- Anthropic API key with sufficient token budget
- Estimated cost per review: ~$2-5 in API tokens (8 Sonnet
  calls + 1 Haiku call, ~50K input tokens each)
```

### Step 2: Commit

```bash
git add docs/PRODUCTION-MIGRATION.txt
git commit -m "Add production migration guide for IT handoff"
```

---

## Verification

After all tasks are implemented, run a full review to verify:

1. Phase 0 extracts PDF pages to `pages/` directory
2. All 8 disciplines launch simultaneously (1 wave)
3. Duration and PDF size appear in the job queue after completion
4. If any discipline produces bad JSON, sanitization repairs it
5. If sanitization fails, the discipline is retried once
6. Progress percentage updates as disciplines complete (not stuck at 7%)
7. `docs/PRODUCTION-MIGRATION.txt` exists and is comprehensive

**Test command:**
```bash
curl -s -X POST http://127.0.0.1:8083/api/submit \
  -F "projectName=Optimization Test" \
  -F "divisions=02,03,21,22,26,27,28,32,33,40" \
  -F "reviewPhase=50% DD" \
  -F "constructionType=New Construction" \
  -F "pmEmail=john.slagboom@wsu.edu" \
  -F "pdf=@path/to/test.pdf"
```

Monitor with:
```bash
watch -n 10 'curl -s http://127.0.0.1:8083/api/jobs | python -m json.tool | head -30'
```
