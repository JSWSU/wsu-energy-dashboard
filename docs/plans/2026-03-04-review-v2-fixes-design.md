# Review System v2 Fixes — Design Document

**Date:** 2026-03-04
**Status:** Approved
**Triggered by:** TFREC live test failure (8/13 scan units failed, context overflow)
**Test report:** `docs/2026-03-03-tfrec-live-test-report.md`

---

## Problem Statement

The v2 live test on 2026-03-03 failed with a 62% scan unit failure rate. Root cause: every Claude CLI worker reads ALL 75 pages (1.1MB) plus its standards (50-150KB), exceeding Sonnet's context window. One worker explicitly logged "Prompt is too long". Additional bugs in synthesize.py and generate_reports.py prevented report generation from the partial results that did succeed.

## Design Goals

1. **Reliability first** — Every worker must fit within context limits. Zero "Prompt is too long" failures.
2. **Deterministic orchestration** — Python code handles all chunking, retries, and monitoring. AI only does review work.
3. **Future subagent hook** — Design allows adding Task tool subagent escalation for persistent failures later.

---

## Architecture

Replace the generated bash script (`run-review.sh`) with a Python orchestrator (`review_pipeline.py`). The Perl server spawns Python instead of bash.

```
Perl Server (review-server.pl)
  └── review_pipeline.py (Commander — Python, deterministic)
        ├── Phase 0: PDF extraction (existing extract_pdf.py, unchanged)
        ├── Phase 1: Discipline reviews
        │   ├── Plan workers: read analysis.json, estimate tokens, split by source file
        │   ├── Build prompts with embedded page text + standards text
        │   ├── Launch workers: claude.exe -p <prompt> --output-format json
        │   ├── Validate output JSON, repair if needed, retry once
        │   └── Merge worker results per discipline
        ├── Phase 2a: Synthesis (existing synthesize.py, with bug fixes)
        ├── Phase 2b: Executive summary (claude.exe with Haiku, existing pattern)
        ├── Phase 3: Reports (existing generate_reports.py, with bug fixes)
        └── Phase 4: PDF annotation (existing annotate_pdf.py, non-fatal)
```

---

## Worker Chunking Strategy

### Always split: one worker per standards source file

Each worker reviews ONE standards source file against the discipline's assigned pages. No combining.

**Input per worker:**
- One standards source file (10-40KB typically)
- Only the pages assigned to this discipline (from analysis.json page assignments)
- Both embedded directly in the prompt (no Read tool)

**Token estimation:**
```
tokens ≈ len(prompt_template + page_text + standards_text) / 4
```

**Split rules:**
- Always split by source file (one worker per source file)
- If a single worker still exceeds 120K tokens (requires ~480KB of text), split the pages into halves
- Token safety margin: 120K target max (Sonnet has 200K context, reserves 80K for system prompt + output)

**Estimated counts for TFREC-sized projects (75 pages, 8 disciplines):**
- ~25-35 workers total
- Each worker: 40-100K tokens
- 8 concurrent workers, ~4-5 batches, Phase 1 in ~12-15 min

### Worker merging

After all workers for a discipline complete, Python merges results into one `discipline-{key}-findings.json`. This replaces the current `merge_split_discipline_parts()` logic in synthesize.py — the merge now happens in the pipeline orchestrator before synthesis.

---

## Prompt Structure

Workers receive a self-contained prompt with all context embedded. No tool access needed.

```
You are reviewing construction drawings for WSU design standards compliance.
Project: {project_name}
Phase: {review_phase}
Construction type: {construction_type}

DISCIPLINE: {discipline_name}
Standards section: {standards_section_name}

=== DRAWING PAGES ===
--- Page {n}: {sheet_id} ({sheet_title}) ---
{page_text}

--- Page {m}: {sheet_id} ({sheet_title}) ---
{page_text}
...

=== WSU DESIGN STANDARDS ===
{standards_file_content}

=== INSTRUCTIONS ===
Review EVERY numbered requirement, clause, and sub-clause in the standards
above against the drawing pages. For each requirement, assign one status:
  [C] Compliant — requirement is met in the drawings
  [D] Deviation — requirement is partially met or met differently
  [O] Omission — requirement is not addressed in the drawings
  [X] Concern — requirement needs clarification or further review
  [NA] Not Applicable — requirement does not apply at this review phase

OUTPUT FORMAT:
Return a JSON object:
{
  "discipline": "{discipline_key}",
  "standards_section": "{section_name}",
  "summary": {
    "total_requirements": N,
    "compliant": N,
    "deviations": N,
    "omissions": N,
    "concerns": N,
    "not_applicable": N
  },
  "requirements": [
    // For COMPLIANT or NA items, use 4-field minimal format:
    { "csi_code": "09 21 16", "requirement": "Short description", "status": "C", "drawing_sheet": "A-301" },

    // For NON-COMPLIANT items (D, O, X), use full format:
    {
      "division": "09",
      "csi_code": "09 21 16",
      "requirement": "Full requirement text",
      "status": "O",
      "severity": "Critical|Major|Minor",
      "finding_id": "F-{discipline}-{section}-NNN",
      "pdf_reference": "Sheet A-301, Detail 4",
      "standard_reference": "Section 09 21 16.3.B",
      "issue": "Description of the non-compliance",
      "required_action": "What needs to change",
      "drawing_sheet": "A-301",
      "notes": "Additional context"
    }
  ]
}

RULES:
- Summary counts MUST match: total = compliant + deviations + omissions + concerns + not_applicable
- Compliant and NA items MUST use 4-field minimal format
- Every non-compliant finding MUST have severity, issue, and required_action
- Properly escape all quotes in JSON strings (use "in." not raw inch marks)
```

**Key differences from v1/v2 prompts:**
- Page text embedded (no Read tool needed)
- Standards text embedded (no Read tool needed)
- No `--allowedTools` flag — worker outputs JSON directly
- `--output-format json` captures clean JSON from stdout
- NA status explicitly allowed
- Timeout reduced to 300s (no tool calls = faster)

---

## CLI Invocation

```python
result = subprocess.run(
    [claude_path, '-p', prompt,
     '--model', 'sonnet',
     '--output-format', 'json',
     '--dangerously-skip-permissions'],
    capture_output=True, text=True, timeout=300,
    env={**os.environ, 'CLAUDE_CODE_MAX_OUTPUT_TOKENS': '16000'}
)
```

Python captures stdout (JSON output) and saves to file. No Write tool needed.

---

## Retry Strategy

### Tier 1: Deterministic retry (implemented now)

1. Worker exits → check `result.returncode` and `result.stdout`
2. If stdout has content but invalid JSON → run `repair_json.py`
3. If still no valid JSON → retry once with same prompt
4. If retry also fails → mark worker as failed, continue with partial results
5. Log all failures with stdout/stderr content for debugging

### Tier 2: Task tool subagent escalation (future hook)

Function signature designed in but not implemented:
```python
def escalate_to_subagent(worker_config, failure_log):
    """Future: Launch a Claude Code session with Task tool to adaptively
    retry a persistently failing worker. The subagent can reason about
    the failure and try different approaches (smaller context, different
    prompt structure, etc.)."""
    raise NotImplementedError("Tier 2 escalation - future feature")
```

---

## Perl Server Changes

The Perl server currently generates a ~500-line bash script via heredoc. This gets replaced with:

```perl
# Instead of generating run-review.sh:
my $cmd = qq{"$python" "$base_dir/review_pipeline.py" "$job_dir" 2>&1};
```

The Perl server still handles:
- Job queue management
- Progress polling (reads progress.log written by Python)
- Status updates to job.json
- Email notifications

The Python orchestrator handles:
- All Phase 0-4 execution
- Writing progress.log for the Perl server to poll
- Writing timing.log
- Writing FAILED file on error

---

## Bug Fixes (included in this change)

### synthesize.py

1. **Line 621 — NoneType crash:**
   ```python
   # Before:
   f"{(f.get('title','') or f.get('issue',''))[:100]}"
   # After:
   f"{(f.get('title') or f.get('issue') or '')[:100]}"
   ```

2. **Line 384 — None issue propagation:**
   ```python
   # Before:
   'issue': f.get('issue', ''),
   # After:
   'issue': f.get('issue') or '',
   ```

3. **NA status handling:**
   - Add `'NA'` to recognized status set throughout
   - Count NA in summary stats
   - Treat NA items like compliant for output formatting (4-field minimal)

4. **Schema aliases — add missing mappings:**
   ```python
   'standard_reference': [..., 'standard', 'section'],
   'finding_id': ['id', 'finding_number', 'finding_ref'],
   ```

### generate_reports.py

5. **Validation fix:**
   - Change validation to: `C + D + O + X + NA = total`
   - Add NA count to severity summary display

---

## File Changes

| File | Change | Est. Lines |
|------|--------|-----------|
| `review_pipeline.py` | **NEW** — Python commander/orchestrator | ~350 |
| `review-server.pl` | **MODIFY** — Replace bash heredoc with Python spawn | -200, +30 |
| `synthesize.py` | **MODIFY** — Fix NoneType, NA status, aliases | ~15 |
| `generate_reports.py` | **MODIFY** — Fix validation for NA status | ~10 |
| `review-portal.html` | No changes | 0 |
| `annotate_pdf.py` | No changes | 0 |

---

## Estimated Performance

| Phase | v2 (failed test) | v2-fixed (estimated) |
|-------|------------------|---------------------|
| Phase 0 | 0s (skipped) | 0s (skipped) |
| Phase 1 | 31 min (38% success) | 12-15 min (target 100%) |
| Phase 2a | 1s | 1s |
| Phase 2b | 39s | 39s |
| Phase 3 | FAILED | ~5s |
| Phase 4 | Not reached | ~5-10 min |
| **Total** | **FAILED** | **~18-26 min** |

---

## Future: Tier 2 Subagent Escalation (not in scope)

When implemented, persistent failures would trigger a Claude Code session with Task tool access. This session ("squad leader") would:
1. Read the failed worker's config, prompt, and any partial output
2. Reason about why it failed
3. Use Task tool to spawn a subagent with a modified approach
4. Report results back to the Python commander via a JSON file

This is designed-in (function signatures, config structures) but not built in this iteration.
