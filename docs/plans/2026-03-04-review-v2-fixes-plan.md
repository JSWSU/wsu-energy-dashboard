# Review System v2 Fixes — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the failing bash-script pipeline with a Python orchestrator that embeds page text in focused worker prompts, eliminating context overflow failures.

**Architecture:** Python commander (`review_pipeline.py`) reads analysis.json, splits work by individual standards source file, estimates tokens, embeds page text + standards in each worker prompt, launches claude.exe workers, validates/retries output, then runs existing synthesis + report phases. Bug fixes in synthesize.py and generate_reports.py for NA status and NoneType handling.

**Tech Stack:** Python 3.11+, subprocess (claude.exe CLI), json, concurrent.futures, existing PyMuPDF/openpyxl/python-docx.

---

### Task 1: Create review_pipeline.py — Config, Loading, and Token Estimation

**Files:**
- Create: `C:\Users\john.slagboom\Desktop\Git\review_pipeline.py`

**Step 1: Write the Python orchestrator skeleton**

Create `review_pipeline.py` with these functions:

```python
#!/usr/bin/env python3
"""
WSU Design Standards Review — Pipeline Orchestrator (Commander)

Replaces the generated run-review.sh bash script. Deterministic Python
orchestration with focused Claude CLI workers.

Usage:
    python review_pipeline.py <job-dir>
"""

import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_TOKENS_PER_WORKER = 120_000   # Target max (Sonnet has 200K)
CHARS_PER_TOKEN = 4               # Conservative estimate
MAX_CHARS_PER_WORKER = MAX_TOKENS_PER_WORKER * CHARS_PER_TOKEN  # 480KB
WORKER_TIMEOUT = 300              # 5 min (no tool calls = fast)
MAX_CONCURRENT_WORKERS = 8
RETRY_LIMIT = 1

# Discipline group definitions (mirrors review-server.pl @ALL_GROUPS)
DISCIPLINE_GROUPS = [
    {
        'key': 'arch-structure',
        'name': 'Architectural \u2014 Structure & Envelope',
        'divs': ['02', '03', '04', '05', '07', '08'],
        'desc': 'demolition, concrete, masonry, metals, roofing, waterproofing, and openings sheets',
        'supp': [],
    },
    {
        'key': 'arch-finishes',
        'name': 'Architectural \u2014 Finishes & Equipment',
        'divs': ['09', '10', '11', '12', '13', '14'],
        'desc': 'finishes, specialties, equipment, furnishings, special construction, and conveying sheets',
        'supp': [],
    },
    {
        'key': 'fire-protection',
        'name': 'Fire Protection and Security',
        'divs': ['21', '28'],
        'desc': 'fire suppression, fire alarm, and electronic safety sheets',
        'supp': [],
    },
    {
        'key': 'plumbing',
        'name': 'Plumbing',
        'divs': ['22'],
        'desc': 'plumbing plans, fixture schedules, and domestic water sheets',
        'supp': [],
    },
    {
        'key': 'hvac-controls',
        'name': 'HVAC and Building Automation',
        'divs': ['23', '25'],
        'desc': 'mechanical plans, HVAC equipment schedules, piping diagrams, and BAS/controls sequences',
        'supp': [
            'standards/wsu/supplemental/detail-drawings/23-22-00-m1-steam-piping-diagrams.md',
            'standards/wsu/supplemental/detail-drawings/23-22-00-m2-steam-piping-schematic.md',
            'standards/wsu/supplemental/detail-drawings/23-83-13-heating-cable-schematic.md',
            'standards/wsu/supplemental/25-appendix-3-bas-point-naming.md',
            'standards/wsu/supplemental/25-appendix-4-standard-operating-procedures.md',
            'standards/wsu/supplemental/25-appendix-6-product-requirements.md',
            'standards/wsu/supplemental/25-appendix-7-airflow-control.md',
        ],
    },
    {
        'key': 'electrical',
        'name': 'Electrical',
        'divs': ['26'],
        'desc': 'electrical plans, panel schedules, one-line diagrams, lighting plans, and power distribution sheets',
        'supp': [
            'standards/wsu/supplemental/detail-drawings/26-56-00-exterior-lighting.md',
            'standards/wsu/supplemental/detail-drawings/26-56-00-exterior-lighting-pole-base.md',
        ],
    },
    {
        'key': 'communications',
        'name': 'Communications and Technology',
        'divs': ['27'],
        'desc': 'telecommunications, data infrastructure, audio-visual, and technology system sheets',
        'supp': [
            'standards/wsu/supplemental/27-technology-infrastructure-design-guide.md',
        ],
    },
    {
        'key': 'civil-site',
        'name': 'Civil, Site, and Utilities',
        'divs': ['31', '32', '33', '40'],
        'desc': 'civil, earthwork, exterior improvements, utilities, metering, and process integration sheets',
        'supp': [
            'standards/wsu/supplemental/detail-drawings/32-33-13-bike-rack.md',
            'standards/wsu/supplemental/detail-drawings/33-01-33-energy-metering-diagram.md',
            'standards/wsu/supplemental/detail-drawings/33-05-13-standard-manhole.md',
            'standards/wsu/supplemental/detail-drawings/33-41-00-storm-drain-pipe.md',
            'standards/wsu/supplemental/detail-drawings/33-60-00-chilled-water-schematic.md',
            'standards/wsu/supplemental/detail-drawings/33-71-73-electric-meter-diagram.md',
        ],
    },
]


def log(msg, job_dir=None):
    """Print to stdout and append to progress.log if job_dir given."""
    print(msg, flush=True)
    if job_dir:
        with open(os.path.join(job_dir, 'output', 'progress.log'), 'a') as f:
            f.write(msg + '\n')


def load_analysis(job_dir):
    """Load analysis.json from job directory."""
    path = os.path.join(job_dir, 'analysis.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_job(job_dir):
    """Load job.json from job directory."""
    path = os.path.join(job_dir, 'job.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_page_text(job_dir, page_num):
    """Load extracted text for a single page. Returns (page_num, text)."""
    fname = f'page-{page_num:04d}.txt'
    path = os.path.join(job_dir, 'pages', fname)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return (page_num, f.read())
    return (page_num, '')


def get_page_text_for_discipline(job_dir, analysis, disc_key):
    """Get concatenated page text for a discipline's assigned pages."""
    rec = analysis.get('recommended_disciplines', {}).get(disc_key, {})
    pages = rec.get('pages', [])
    sheet_ids = rec.get('sheet_ids', [])

    # Always include page 1 (cover/index) if not already assigned
    if 1 not in pages:
        pages = [1] + sorted(pages)

    texts = []
    for pg in pages:
        _, text = load_page_text(job_dir, pg)
        if text.strip():
            sid = ''
            # Try to match sheet ID from the sheet_ids list
            if sheet_ids and pg - 1 < len(sheet_ids):
                # Approximate — sheet_ids are ordered but may not 1:1 match pages
                pass
            texts.append(f'--- Page {pg} ---\n{text}')

    return '\n\n'.join(texts), pages


def list_standards_source_files(base_dir, group):
    """List individual standards source files for a discipline group.
    Returns list of (relative_path, content) tuples."""
    files = []

    # Division standards
    for div in group['divs']:
        div_dir = os.path.join(base_dir, 'standards', 'wsu', f'division-{div}')
        if os.path.isdir(div_dir):
            for fname in sorted(os.listdir(div_dir)):
                if fname.endswith('.md'):
                    fpath = os.path.join(div_dir, fname)
                    with open(fpath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    files.append((f'division-{div}/{fname}', content))

    # Supplemental files
    for supp_rel in group.get('supp', []):
        fpath = os.path.join(base_dir, supp_rel)
        if os.path.isfile(fpath):
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
            files.append((supp_rel, content))

    return files


def estimate_tokens(text):
    """Estimate token count from character count."""
    return len(text) // CHARS_PER_TOKEN
```

**Step 2: Verify syntax**

Run: `py -c "import ast; ast.parse(open('C:/Users/john.slagboom/Desktop/Git/review_pipeline.py').read()); print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add review_pipeline.py
git commit -m "feat: review_pipeline.py skeleton — config, loading, token estimation"
```

---

### Task 2: Add Worker Planning and Prompt Building

**Files:**
- Modify: `C:\Users\john.slagboom\Desktop\Git\review_pipeline.py`

**Step 1: Add the worker planning function**

Append after `estimate_tokens()`:

```python
def plan_workers(job_dir, job, analysis, base_dir):
    """Plan all workers across all disciplines. Returns list of worker configs."""
    selected = set(job.get('divisions', []))
    workers = []

    for group in DISCIPLINE_GROUPS:
        # Filter to groups that have user-selected divisions
        active_divs = [d for d in group['divs'] if d in selected]
        if not active_divs:
            continue

        # Get page text for this discipline
        page_text, page_nums = get_page_text_for_discipline(job_dir, analysis, group['key'])

        # Get individual standards source files
        standards_files = list_standards_source_files(base_dir, group)

        if not standards_files:
            log(f"  WARNING: No standards files found for {group['name']}", job_dir)
            continue

        # One worker per source file (aggressive splitting)
        for std_relpath, std_content in standards_files:
            prompt_text = build_worker_prompt(
                job=job,
                group=group,
                active_divs=active_divs,
                page_text=page_text,
                standards_text=std_content,
                standards_name=std_relpath,
            )

            total_tokens = estimate_tokens(prompt_text)

            if total_tokens > MAX_TOKENS_PER_WORKER:
                # Split pages into halves and create 2 workers
                mid = len(page_nums) // 2
                for half_idx, half_pages in enumerate([page_nums[:mid], page_nums[mid:]], 1):
                    half_text = '\n\n'.join(
                        f'--- Page {pg} ---\n{load_page_text(job_dir, pg)[1]}'
                        for pg in half_pages
                        if load_page_text(job_dir, pg)[1].strip()
                    )
                    half_prompt = build_worker_prompt(
                        job=job,
                        group=group,
                        active_divs=active_divs,
                        page_text=half_text,
                        standards_text=std_content,
                        standards_name=std_relpath,
                    )
                    worker_key = f"{group['key']}-{Path(std_relpath).stem}-pg{half_idx}"
                    workers.append({
                        'key': worker_key,
                        'discipline': group['key'],
                        'discipline_name': group['name'],
                        'standards_file': std_relpath,
                        'prompt': half_prompt,
                        'tokens_est': estimate_tokens(half_prompt),
                    })
            else:
                worker_key = f"{group['key']}-{Path(std_relpath).stem}"
                workers.append({
                    'key': worker_key,
                    'discipline': group['key'],
                    'discipline_name': group['name'],
                    'standards_file': std_relpath,
                    'prompt': prompt_text,
                    'tokens_est': total_tokens,
                })

    return workers
```

**Step 2: Add the prompt builder function**

Add before `plan_workers()`:

```python
def build_worker_prompt(job, group, active_divs, page_text, standards_text, standards_name):
    """Build a self-contained worker prompt with embedded page text and standards."""
    divs_str = ', '.join(active_divs)
    divs_json = ', '.join(f'"{d}"' for d in active_divs)

    prompt = f"""You are reviewing construction drawings for WSU design standards compliance.
Project: {job['projectName']}
Phase: {job['reviewPhase']}
Construction type: {job['constructionType']}

DISCIPLINE: {group['name']} (Divisions {divs_str})
Standards section: {standards_name}

=== DRAWING PAGES ===
{page_text}

=== WSU DESIGN STANDARDS ({standards_name}) ===
{standards_text}

=== INSTRUCTIONS ===
Review EVERY numbered requirement, clause, and sub-clause in the standards
section above against the drawing pages. For each requirement, assign status:
  [C] Compliant - requirement is met in the drawings
  [D] Deviation - requirement is partially met or met differently
  [O] Omission - requirement is not addressed in the drawings
  [X] Concern - requirement needs clarification or further review
  [NA] Not Applicable - requirement does not apply at this review phase

OUTPUT FORMAT:
Return a single JSON object:
{{
  "discipline": "{group['key']}",
  "standards_section": "{standards_name}",
  "divisions_reviewed": [{divs_json}],
  "summary": {{
    "total_requirements": N,
    "compliant": N,
    "deviations": N,
    "omissions": N,
    "concerns": N,
    "not_applicable": N
  }},
  "requirements": [
    // For COMPLIANT or NA items, use 4-field minimal format:
    {{ "csi_code": "09 21 16", "requirement": "Short description", "status": "C", "drawing_sheet": "A-301" }},

    // For NON-COMPLIANT items (D, O, X), use full format:
    {{
      "division": "09",
      "csi_code": "09 21 16",
      "requirement": "Full requirement text",
      "status": "D",
      "severity": "Critical|Major|Minor",
      "finding_id": "F-{group['key']}-NNN",
      "pdf_reference": "Sheet A-301, Detail 4",
      "standard_reference": "Section 09 21 16.3.B",
      "issue": "Description of the non-compliance",
      "required_action": "What needs to change",
      "drawing_sheet": "A-301",
      "notes": "Additional context"
    }}
  ]
}}

RULES:
- Summary counts MUST match: total = compliant + deviations + omissions + concerns + not_applicable
- Compliant and NA items MUST use 4-field minimal format
- Every non-compliant finding MUST have severity, issue, and required_action
- Properly escape all quotes in JSON strings. Use "in." not raw inch marks.
- Be thorough. Check EVERY requirement. Depth over speed.
"""
    return prompt
```

**Step 3: Verify syntax**

Run: `py -c "import ast; ast.parse(open('C:/Users/john.slagboom/Desktop/Git/review_pipeline.py').read()); print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add review_pipeline.py
git commit -m "feat: add worker planning and prompt building to review_pipeline.py"
```

---

### Task 3: Add Worker Execution, Validation, and Retry

**Files:**
- Modify: `C:\Users\john.slagboom\Desktop\Git\review_pipeline.py`

**Step 1: Add the worker execution function**

Append after `plan_workers()`:

```python
def find_claude_exe():
    """Find the claude.exe CLI path."""
    # Check common locations
    appdata = os.environ.get('APPDATA', '')
    claude_dir = os.path.join(appdata, 'Claude', 'claude-code')
    if os.path.isdir(claude_dir):
        for ver_dir in sorted(os.listdir(claude_dir), reverse=True):
            exe = os.path.join(claude_dir, ver_dir, 'claude.exe')
            if os.path.isfile(exe):
                return exe
    # Fallback: assume it's on PATH
    return 'claude'


def run_worker(worker, output_dir, claude_path):
    """Execute a single worker. Returns (worker_key, success, json_data_or_none)."""
    key = worker['key']
    out_file = os.path.join(output_dir, f'worker-{key}-findings.json')
    stdout_log = os.path.join(output_dir, f'worker-{key}-stdout.log')
    stderr_log = os.path.join(output_dir, f'worker-{key}-stderr.log')

    try:
        result = subprocess.run(
            [claude_path, '-p', worker['prompt'],
             '--model', 'sonnet',
             '--output-format', 'text',
             '--dangerously-skip-permissions'],
            capture_output=True, text=True, timeout=WORKER_TIMEOUT,
            env={**os.environ, 'CLAUDE_CODE_MAX_OUTPUT_TOKENS': '16000'}
        )

        # Save logs
        with open(stdout_log, 'w', encoding='utf-8') as f:
            f.write(result.stdout or '')
        with open(stderr_log, 'w', encoding='utf-8') as f:
            f.write(result.stderr or '')

        # Try to parse JSON from stdout
        raw = result.stdout.strip()
        json_data = extract_json(raw)

        if json_data:
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            return (key, True, json_data)
        else:
            return (key, False, None)

    except subprocess.TimeoutExpired:
        with open(stderr_log, 'w', encoding='utf-8') as f:
            f.write(f'TIMEOUT after {WORKER_TIMEOUT}s\n')
        return (key, False, None)
    except Exception as e:
        with open(stderr_log, 'w', encoding='utf-8') as f:
            f.write(f'ERROR: {e}\n')
        return (key, False, None)


def extract_json(raw):
    """Extract and parse JSON from raw CLI output. Returns parsed dict or None."""
    if not raw:
        return None

    # Try direct parse first
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Find JSON object boundaries
    start = raw.find('{')
    if start < 0:
        return None
    # Find matching closing brace
    depth = 0
    end = -1
    in_string = False
    escape = False
    for i in range(start, len(raw)):
        ch = raw[i]
        if escape:
            escape = False
            continue
        if ch == '\\' and in_string:
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end > start:
        try:
            return json.loads(raw[start:end])
        except json.JSONDecodeError:
            pass

    # Last resort: try repair_json.py approach
    try:
        from repair_json import repair
        obj, err = repair(raw)
        if obj:
            return obj
    except ImportError:
        pass

    return None


def execute_phase1(workers, output_dir, job_dir, claude_path):
    """Execute all workers with parallel batching and retry.
    Returns dict of {discipline_key: [findings_data, ...]}."""
    results = {}  # key -> json_data
    failed = []

    total = len(workers)
    log(f"Phase 1: Launching {total} workers ({MAX_CONCURRENT_WORKERS} concurrent)...", job_dir)

    # First pass
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_WORKERS) as executor:
        futures = {}
        for w in workers:
            future = executor.submit(run_worker, w, output_dir, claude_path)
            futures[future] = w

        for future in as_completed(futures):
            w = futures[future]
            key, success, data = future.result()
            if success:
                results[key] = data
                log(f"  {key}: OK ({w['tokens_est']}t est.)")
            else:
                failed.append(w)
                log(f"  {key}: FAILED ({w['tokens_est']}t est.)")

    log(f"Phase 1 first pass: {len(results)}/{total} succeeded, {len(failed)} failed.", job_dir)

    # Retry pass
    if failed and RETRY_LIMIT > 0:
        log(f"Retrying {len(failed)} failed workers...", job_dir)
        retry_failed = []

        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_WORKERS) as executor:
            futures = {}
            for w in failed:
                future = executor.submit(run_worker, w, output_dir, claude_path)
                futures[future] = w

            for future in as_completed(futures):
                w = futures[future]
                key, success, data = future.result()
                if success:
                    results[key] = data
                    log(f"  Retry {key}: OK")
                else:
                    retry_failed.append(w)
                    log(f"  Retry {key}: FAILED")

        failed = retry_failed
        log(f"After retry: {len(results)}/{total} succeeded, {len(failed)} still failed.", job_dir)

    # Report final failures
    for w in failed:
        log(f"  PERMANENT FAILURE: {w['key']} ({w['discipline_name']} / {w['standards_file']})", job_dir)

    return results, failed


def merge_worker_results(results, output_dir):
    """Merge worker results by discipline into discipline-{key}-findings.json files.
    Returns list of (discipline_key, merged_data) tuples."""
    # Group by discipline
    by_discipline = {}
    for worker_key, data in results.items():
        disc = data.get('discipline', worker_key.split('-')[0])
        by_discipline.setdefault(disc, []).append(data)

    merged = []
    for disc_key, parts in sorted(by_discipline.items()):
        all_reqs = []
        total_summary = {
            'total_requirements': 0, 'compliant': 0, 'deviations': 0,
            'omissions': 0, 'concerns': 0, 'not_applicable': 0,
        }

        for part in parts:
            reqs = part.get('requirements', [])
            all_reqs.extend(reqs)

            summary = part.get('summary', {})
            for k in total_summary:
                total_summary[k] += summary.get(k, 0)

        merged_data = {
            'discipline': disc_key,
            'summary': total_summary,
            'requirements': all_reqs,
        }

        out_path = os.path.join(output_dir, f'discipline-{disc_key}-findings.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, indent=2, ensure_ascii=False)

        merged.append((disc_key, merged_data))
        print(f"  Merged {disc_key}: {len(all_reqs)} requirements from {len(parts)} workers")

    return merged
```

**Step 2: Verify syntax**

Run: `py -c "import ast; ast.parse(open('C:/Users/john.slagboom/Desktop/Git/review_pipeline.py').read()); print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add review_pipeline.py
git commit -m "feat: add worker execution, validation, retry, and merging"
```

---

### Task 4: Add Main Orchestrator and Phase 2-4 Execution

**Files:**
- Modify: `C:\Users\john.slagboom\Desktop\Git\review_pipeline.py`

**Step 1: Add the main orchestrator function**

Append after `merge_worker_results()`:

```python
def find_python():
    """Find Python executable (same logic as the bash script)."""
    candidates = [
        os.path.expandvars(r'%LOCALAPPDATA%\Programs\Python\Python313\python.exe'),
        os.path.expandvars(r'%LOCALAPPDATA%\Programs\Python\Python312\python.exe'),
        os.path.expandvars(r'%LOCALAPPDATA%\Programs\Python\Python311\python.exe'),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    # Fallback: try PATH
    import shutil
    for name in ('python3', 'python', 'py'):
        found = shutil.which(name)
        if found:
            return found
    return sys.executable  # Last resort: this Python


def write_timing(timing_log, key, value):
    """Append a timing entry."""
    with open(timing_log, 'a') as f:
        f.write(f'{key}={value}\n')


def escalate_to_subagent(worker_config, failure_log):
    """Future: Launch a Claude Code session with Task tool to adaptively
    retry a persistently failing worker."""
    raise NotImplementedError("Tier 2 escalation - future feature")


def main():
    if len(sys.argv) < 2:
        print("Usage: python review_pipeline.py <job-dir>", file=sys.stderr)
        sys.exit(1)

    job_dir = os.path.abspath(sys.argv[1])
    output_dir = os.path.join(job_dir, 'output')
    os.makedirs(output_dir, exist_ok=True)
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Write PID
    with open(os.path.join(output_dir, 'pipeline.pid'), 'w') as f:
        f.write(str(os.getpid()))

    timing_log = os.path.join(output_dir, 'timing.log')

    # Load job metadata
    job = load_job(job_dir)
    analysis = load_analysis(job_dir)

    python = find_python()
    claude_path = find_claude_exe()
    log(f"Using Python: {python}")
    log(f"Using Claude: {claude_path}")

    # === PHASE 0: PDF text extraction ===
    write_timing(timing_log, 'phase0_start', int(time.time()))
    manifest = os.path.join(job_dir, 'pages', 'manifest.txt')
    if os.path.exists(manifest):
        log("Phase 0: Skipped (pages already extracted).", job_dir)
    else:
        log("Phase 0: Extracting PDF text...", job_dir)
        extract_script = os.path.join(base_dir, 'extract_pdf.py')
        input_pdf = os.path.join(job_dir, 'input.pdf')
        pages_dir = os.path.join(job_dir, 'pages')
        ret = subprocess.run([python, extract_script, input_pdf, pages_dir])
        if ret.returncode != 0:
            with open(os.path.join(output_dir, 'FAILED'), 'w') as f:
                f.write('extract_pdf.py failed')
            sys.exit(1)
        log("Phase 0 complete.", job_dir)

    write_timing(timing_log, 'phase0_end', int(time.time()))
    pages_dir = os.path.join(job_dir, 'pages')
    page_count = len([f for f in os.listdir(pages_dir) if f.endswith('.txt')]) if os.path.isdir(pages_dir) else 0
    write_timing(timing_log, 'phase0_pages', page_count)

    # === PHASE 1: Discipline reviews ===
    write_timing(timing_log, 'phase1_start', int(time.time()))

    # Plan workers
    workers = plan_workers(job_dir, job, analysis, base_dir)
    log(f"Phase 1: Planned {len(workers)} workers across disciplines.", job_dir)
    for w in workers:
        log(f"  {w['key']}: {w['tokens_est']}t est. ({w['standards_file']})")

    # Execute workers
    results, failed = execute_phase1(workers, output_dir, job_dir, claude_path)

    # Merge by discipline
    log("Merging worker results by discipline...", job_dir)
    merged = merge_worker_results(results, output_dir)

    write_timing(timing_log, 'phase1_end', int(time.time()))
    write_timing(timing_log, 'phase1_workers', len(workers))
    write_timing(timing_log, 'phase1_succeeded', len(results))
    write_timing(timing_log, 'phase1_failed', len(failed))

    if not merged:
        with open(os.path.join(output_dir, 'FAILED'), 'w') as f:
            f.write('No discipline findings produced. All workers failed.')
        sys.exit(1)

    log(f"Phase 1 complete: {len(merged)} disciplines, {len(results)}/{len(workers)} workers.", job_dir)

    # === PHASE 2a: Python synthesis ===
    write_timing(timing_log, 'phase2a_start', int(time.time()))
    log("Phase 2a: Synthesizing (Python)...", job_dir)
    synth_script = os.path.join(base_dir, 'synthesize.py')
    ret = subprocess.run(
        [python, synth_script, output_dir],
        capture_output=True, text=True,
    )
    with open(os.path.join(output_dir, 'synthesis-stdout.log'), 'w') as f:
        f.write(ret.stdout or '')
    with open(os.path.join(output_dir, 'synthesis-stderr.log'), 'w') as f:
        f.write(ret.stderr or '')

    review_data_path = os.path.join(output_dir, 'review-data.json')
    if not os.path.exists(review_data_path):
        with open(os.path.join(output_dir, 'FAILED'), 'w') as f:
            f.write('synthesize.py did not produce review-data.json')
        sys.exit(1)
    log("Phase 2a complete: review-data.json produced.", job_dir)
    write_timing(timing_log, 'phase2a_end', int(time.time()))

    # === PHASE 2b: Executive summary (Haiku) ===
    write_timing(timing_log, 'phase2b_start', int(time.time()))
    log("Phase 2b: Generating executive summary...", job_dir)
    exec_prompt_path = os.path.join(job_dir, 'prompt-exec-summary.txt')
    if os.path.exists(exec_prompt_path):
        with open(exec_prompt_path, 'r') as f:
            exec_prompt = f.read()
        # Run Haiku in the output dir so it can read review-data.json
        ret = subprocess.run(
            [claude_path, '-p', exec_prompt,
             '--model', 'haiku',
             '--allowedTools', 'Read', 'Write',
             '--dangerously-skip-permissions',
             '--output-format', 'text'],
            capture_output=True, text=True, timeout=300,
            cwd=output_dir,
            env={**os.environ, 'CLAUDE_CODE_MAX_OUTPUT_TOKENS': '16000'}
        )
        with open(os.path.join(output_dir, 'executive-summary.txt'), 'w') as f:
            f.write(ret.stdout or '')
        with open(os.path.join(output_dir, 'summary-stderr.log'), 'w') as f:
            f.write(ret.stderr or '')
    log("Phase 2b complete.", job_dir)
    write_timing(timing_log, 'phase2b_end', int(time.time()))

    # === PHASE 3: Report generation ===
    write_timing(timing_log, 'phase3_start', int(time.time()))
    log("Phase 3: Generating reports...", job_dir)
    report_script = os.path.join(base_dir, 'generate_reports.py')
    ret = subprocess.run([python, report_script, review_data_path])
    if ret.returncode != 0:
        log(f"ERROR: generate_reports.py failed (exit code {ret.returncode})", job_dir)
        if not os.path.exists(os.path.join(output_dir, 'FAILED')):
            with open(os.path.join(output_dir, 'FAILED'), 'w') as f:
                f.write(f'generate_reports.py exited with code {ret.returncode}')
        sys.exit(1)
    write_timing(timing_log, 'phase3_end', int(time.time()))

    # === PHASE 4: PDF annotation (non-fatal) ===
    write_timing(timing_log, 'phase4_start', int(time.time()))
    log("Phase 4: Generating annotated PDF...", job_dir)
    annotate_script = os.path.join(base_dir, 'annotate_pdf.py')
    ret = subprocess.run([python, annotate_script, job_dir],
                         capture_output=True, text=True)
    if ret.returncode != 0:
        log(f"WARNING: PDF annotation failed (exit {ret.returncode})", job_dir)
    write_timing(timing_log, 'phase4_end', int(time.time()))

    log("Pipeline complete.", job_dir)


if __name__ == '__main__':
    main()
```

**Step 2: Verify syntax**

Run: `py -c "import ast; ast.parse(open('C:/Users/john.slagboom/Desktop/Git/review_pipeline.py').read()); print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add review_pipeline.py
git commit -m "feat: add main orchestrator with Phase 0-4 execution"
```

---

### Task 5: Fix synthesize.py Bugs

**Files:**
- Modify: `C:\Users\john.slagboom\Desktop\Git\synthesize.py`

**Step 1: Fix NoneType crash at line 621**

Change line 621 from:
```python
f"{(f.get('title','') or f.get('issue',''))[:100]}")
```
To:
```python
f"{(f.get('title') or f.get('issue') or '')[:100]}")
```

**Step 2: Fix None issue propagation at line 384**

Change line 384 from:
```python
'issue': f.get('issue', ''),
```
To:
```python
'issue': f.get('issue') or '',
```

**Step 3: Also fix line 379 (title field) for safety**

Change line 379 from:
```python
'title': f.get('issue', '') or '',
```
To:
```python
'title': f.get('issue') or '',
```

**Step 4: Add NA to status count logic at lines 101-105**

In `merge_split_discipline_parts`, change:
```python
counts = {'C': 0, 'D': 0, 'O': 0, 'X': 0}
```
To:
```python
counts = {'C': 0, 'D': 0, 'O': 0, 'X': 0, 'NA': 0}
```

**Step 5: Add schema aliases for TIDG fields**

In `normalize_item_fields()` at the ALIASES dict (lines 149-158), add to `standard_reference`:
```python
'standard_reference': ['standard_citation', 'standard', 'reference', 'section'],
```
And add to `finding_id`:
```python
'finding_id':         ['id', 'finding_number', 'finding_ref'],
```

**Step 6: Handle NA status in the slim-compliant block**

At line 174, change:
```python
if item.get('status') == 'C':
```
To:
```python
if item.get('status') in ('C', 'NA'):
```

**Step 7: Fix the validation counts around line 687-691**

Find the other `counts = {'C': 0, 'D': 0, 'O': 0, 'X': 0}` dict and add `'NA': 0`.

**Step 8: Verify syntax**

Run: `py -c "import ast; ast.parse(open('C:/Users/john.slagboom/Desktop/Git/synthesize.py').read()); print('OK')"`
Expected: `OK`

**Step 9: Quick unit test**

Run:
```bash
py -c "
from synthesize import normalize_item_fields
# Test NA status handling
item = {'csi_code': '09 21 16', 'requirement': 'Test', 'status': 'NA', 'drawing_sheet': 'A-301'}
normalize_item_fields(item)
assert item.get('severity') is None, 'NA items should not have severity'
assert item.get('division') == '09', 'Should extract division from csi_code'
print('NA test OK')

# Test None issue handling
item2 = {'issue': None, 'status': 'X', 'csi_code': '27 05 00'}
normalize_item_fields(item2)
print('None issue test OK')
print('All tests passed')
"
```
Expected: `All tests passed`

**Step 10: Commit**

```bash
git add synthesize.py
git commit -m "fix: handle NA status, NoneType crash, and TIDG schema aliases in synthesize.py"
```

---

### Task 6: Fix generate_reports.py Validation

**Files:**
- Modify: `C:\Users\john.slagboom\Desktop\Git\generate_reports.py`

**Step 1: Fix the per-discipline validation**

At the validation function (around line 129-133), find:
```python
if row_c + row_d + row_o + row_x != row_total:
```

Add NA counting before this line:
```python
row_na = sum(1 for r in reqs if r.get('status') == 'NA')
```

Change the validation to:
```python
if row_c + row_d + row_o + row_x + row_na != row_total:
    errors.append(
        f"Discipline {d['key']}: C({row_c})+D({row_d})+O({row_o})+X({row_x})+NA({row_na}) "
        f"= {row_c+row_d+row_o+row_x+row_na} != Total({row_total})"
    )
```

**Step 2: Verify syntax**

Run: `py -c "import ast; ast.parse(open('C:/Users/john.slagboom/Desktop/Git/generate_reports.py').read()); print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add generate_reports.py
git commit -m "fix: include NA status in report validation counts"
```

---

### Task 7: Update review-server.pl to Spawn Python

**Files:**
- Modify: `C:\Users\john.slagboom\Desktop\Git\review-server.pl`

**Step 1: Replace the bash script generation**

The existing code at lines 1410-1847 generates `run-review.sh` and launches it. Replace the bash script generation and launch (lines 1410-1847) with a much simpler Python launch:

Keep lines 1130-1237 (discipline group definitions, filtering, building combined standards — the Python orchestrator will read these from the combined/ directory, so the Perl still needs to build them for backward compatibility and for the exec-summary prompt).

Keep the prompt-exec-summary.txt generation (it's separate from the discipline prompts).

Replace the run-review.sh generation (starting at line 1410) and launch.sh generation (ending at line 1847) with:

```perl
    # --- Launch Python pipeline orchestrator ---
    my $pipeline_script = "$ROOT/review_pipeline.py";
    unless (-f $pipeline_script) {
        warn "Cannot find review_pipeline.py at $pipeline_script\n";
        _mark_spawn_failed($job_id, $job, "review_pipeline.py not found");
        return;
    }

    # Find Python (same as used by extract_pdf.py)
    my $python = _find_python();
    unless ($python) {
        _mark_spawn_failed($job_id, $job, "Python not found");
        return;
    }

    # Create launcher script (nohup background)
    my $launcher = "$job_dir/launch.sh";
    open my $lfh, '>', $launcher or do {
        warn "Cannot write launcher: $!\n";
        _mark_spawn_failed($job_id, $job, "Cannot write launcher: $!");
        return;
    };
    (my $job_dir_bash = $job_dir) =~ s{\\}{/}g;
    (my $python_bash = $python) =~ s{\\}{/}g;
    (my $script_bash = $pipeline_script) =~ s{\\}{/}g;
    print $lfh "#!/bin/bash\n";
    print $lfh "nohup \"$python_bash\" \"$script_bash\" \"$job_dir_bash\" > /dev/null 2>&1 &\n";
    close $lfh;
    chmod 0755, $launcher;
    system("bash \"$launcher\"");
```

Also need a `_find_python` helper (if not already present). Check for an existing one first; if not, add:

```perl
sub _find_python {
    my $user = $ENV{USERNAME} || $ENV{USER} || '';
    my @candidates = (
        "/c/Users/$user/AppData/Local/Programs/Python/Python313/python.exe",
        "/c/Users/$user/AppData/Local/Programs/Python/Python312/python.exe",
        "/c/Users/$user/AppData/Local/Programs/Python/Python311/python.exe",
        "/c/Python313/python.exe",
        "/c/Python312/python.exe",
    );
    for my $p (@candidates) {
        return $p if -x $p;
    }
    # Try which
    my $found = `which python3 2>/dev/null` || `which python 2>/dev/null` || `which py 2>/dev/null`;
    chomp $found if $found;
    return $found if $found && -x $found;
    return undef;
}
```

**Step 2: Keep the prompt-exec-summary.txt generation**

The exec summary prompt is still needed. Make sure it's generated BEFORE the pipeline launch. It should already be earlier in the function — verify it exists.

**Step 3: Verify Perl syntax**

Run: `perl -c "C:/Users/john.slagboom/Desktop/Git/review-server.pl"`
Expected: `syntax OK`

**Step 4: Commit**

```bash
git add review-server.pl
git commit -m "refactor: replace bash script generation with Python pipeline spawn"
```

---

### Task 8: Integration Test with Existing Job Data

**Files:**
- No new files. Test against the existing TFREC job.

**Step 1: Test worker planning (dry run)**

Run:
```bash
py -c "
import sys
sys.path.insert(0, 'C:/Users/john.slagboom/Desktop/Git')
from review_pipeline import *

job_dir = 'C:/Users/john.slagboom/Desktop/Git/reviews/4fbcf67d-ffe9-46b4-adfb-60040f183f13'
job = load_job(job_dir)
analysis = load_analysis(job_dir)
base_dir = 'C:/Users/john.slagboom/Desktop/Git'

workers = plan_workers(job_dir, job, analysis, base_dir)
print(f'Planned {len(workers)} workers:')
for w in workers:
    print(f'  {w[\"key\"]}: {w[\"tokens_est\"]}t ({w[\"standards_file\"]})')

# Verify all under token limit
over = [w for w in workers if w['tokens_est'] > MAX_TOKENS_PER_WORKER]
if over:
    print(f'WARNING: {len(over)} workers over token limit!')
else:
    print('All workers under token limit.')
"
```

Expected: ~25-35 workers, all under 120K tokens.

**Step 2: Test single worker (one small discipline)**

Pick the smallest worker and test it live:
```bash
py -c "
import sys, json
sys.path.insert(0, 'C:/Users/john.slagboom/Desktop/Git')
from review_pipeline import *

job_dir = 'C:/Users/john.slagboom/Desktop/Git/reviews/4fbcf67d-ffe9-46b4-adfb-60040f183f13'
job = load_job(job_dir)
analysis = load_analysis(job_dir)
base_dir = 'C:/Users/john.slagboom/Desktop/Git'

workers = plan_workers(job_dir, job, analysis, base_dir)
# Find smallest worker
smallest = min(workers, key=lambda w: w['tokens_est'])
print(f'Testing smallest worker: {smallest[\"key\"]} ({smallest[\"tokens_est\"]}t)')

claude_path = find_claude_exe()
output_dir = job_dir + '/output'
key, success, data = run_worker(smallest, output_dir, claude_path)
print(f'Result: success={success}')
if data:
    reqs = data.get('requirements', [])
    print(f'  Requirements: {len(reqs)}')
    summary = data.get('summary', {})
    print(f'  Summary: {json.dumps(summary)}')
"
```

Expected: success=True, valid JSON with requirements.

**Step 3: Test synthesize.py with bug fixes**

Run against existing review-data.json (or regenerate):
```bash
py -c "
from synthesize import normalize_item_fields
# Test various edge cases
items = [
    {'status': 'C', 'csi_code': '09 21 16', 'requirement': 'Test', 'drawing_sheet': 'A-301'},
    {'status': 'NA', 'csi_code': '27 05 00', 'requirement': 'Future phase', 'drawing_sheet': 'N/A'},
    {'status': 'O', 'issue': None, 'csi_code': '22 00 00', 'requirement': 'Missing'},
    {'status': 'X', 'id': 'F-012', 'standard': 'TIDG', 'section': '2.5', 'requirement': 'Test'},
]
for item in items:
    normalize_item_fields(item)
    print(f'  status={item[\"status\"]}, division={item.get(\"division\")}, finding_id={item.get(\"finding_id\")}')
print('All normalize tests passed')
"
```

Expected: All normalize tests passed.

**Step 4: Commit test results note (no code change)**

No commit needed unless tests reveal issues to fix.

---

### Task 9: Relaunch Server and Run Live Test

**Step 1: Kill old server and relaunch**

```bash
# Kill existing server
kill $(cat C:/Users/john.slagboom/Desktop/Git/review-server.pid 2>/dev/null) 2>/dev/null
sleep 2

# Relaunch
cd "C:/Users/john.slagboom/Desktop/Git"
perl review-server.pl &
sleep 3

# Verify responding
curl -s http://localhost:8083/api/health | head -1
```

Expected: Server responds on port 8083.

**Step 2: Submit the TFREC PDF again through the portal**

Navigate to portal, upload `WSU-TFREC_Design Development_20260123_Drawings.pdf`, confirm disciplines, and monitor through the new pipeline.

**Step 3: Monitor progress**

Check progress.log periodically. The new pipeline should show:
- Worker plan with token estimates
- Workers completing in ~2-5 min each
- No "Prompt is too long" errors
- Phase 2-3-4 completing

**Step 4: Verify deliverables**

Check for:
- `report.docx` — exists and has content
- `report.xlsx` — exists and has content
- `review-markup.pdf` — exists (or annotate warning)

**Step 5: Push and commit if successful**

```bash
git push origin main
```
