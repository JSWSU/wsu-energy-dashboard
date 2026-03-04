# TFREC Live Test Report — Review System v2

**Job:** `4fbcf67d-ffe9-46b4-adfb-60040f183f13`
**Project:** TFREC Design Development Drawings 01.23.2026
**PDF:** 40MB, 75 pages, 8 disciplines (13 scan units after splitting)
**Result:** FAILED at Phase 3 (report generation)

---

## Timeline

| Time | Event |
|------|-------|
| 17:25 | Submitted |
| 17:32 | Analysis complete (8 disciplines, high confidence) |
| 17:33 | User confirmed 23 divisions + Division 40, processing started |
| 17:34 | Phase 1 batch 1 launched (8 of 13 scan units) |
| 17:44 | Batch 1 complete — only 3/8 produced findings |
| 17:44 | Batch 2 launched (5 scan units) |
| 17:54 | Batch 2 complete — 0/5 produced findings |
| 17:54 | Validation: 3/13 valid. Repair fails (all 10 have empty stdout). Retry launched for 10 units. |
| 18:04 | Retry complete — 2/10 succeeded (hvac-controls-part2, communications-part1) |
| 18:05 | **Final: 5 of 13 scan units produced valid findings (38% success rate)** |
| 18:05 | Phase 2a synthesis completed (with crash in stats writing) |
| 18:05 | Phase 2b executive summary generated |
| 18:05 | Phase 3 generate_reports.py FAILED — number validation error |
| ~18:06 | Pipeline exited with error |

**Total Phase 1 wall time:** ~31 minutes (including retry)
**Phases 2-3:** ~1 minute

---

## Issue 1: Context Overflow (ROOT CAUSE — 8 of 13 scan units failed)

### Smoking gun
`hvac-controls-part1-stdout.log` contains: **"Prompt is too long"**

### What happens
Each Claude CLI instance:
1. Receives a ~4KB prompt via `-p` flag
2. Uses Read tool to read all 75 page text files (1.1MB total)
3. Uses Read tool to read the combined standards file (50-150KB)
4. Generates JSON findings and writes via Write tool

The prompt says "Focus on pages relevant to this discipline but **review all pages for context**". Every discipline reads ALL 75 pages + its standards, exceeding the model's context window.

### Successful vs failed

| Unit | Standards | Pages to Read | Result |
|------|-----------|---------------|--------|
| communications-part2 | 125KB | 75 | OK (batch 1, ~8 min) |
| communications-part3 | 136KB | 75 | OK (batch 1, ~9 min) |
| electrical | 102KB | 75 | OK (batch 1, ~10 min) |
| hvac-controls-part2 | 60KB | 75 | OK (retry) |
| communications-part1 | 146KB | 75 | OK (retry) |
| arch-structure-part1 | 146KB | 75 | FAILED x2 |
| arch-structure-part2 | 20KB | 75 | FAILED x2 |
| arch-finishes | 93KB | 75 | FAILED x2 |
| fire-protection | 58KB | 75 | FAILED x2 |
| plumbing | 50KB | 75 | FAILED x2 |
| hvac-controls-part1 | 141KB | 75 | FAILED x2 (confirmed "Prompt is too long") |
| civil-site-part1 | 150KB | 75 | FAILED x2 |
| civil-site-part2 | 139KB | 75 | FAILED x2 |

### Puzzle
Small-standards units (plumbing 50KB, fire-protection 58KB, arch-structure-part2 20KB) also failed. Since ALL units read ALL 75 pages, the page text alone (~1.1MB, ~275K tokens) is probably already at or over the context limit for Sonnet. The successful units may have gotten lucky with file read ordering (partial reads before context filled), or there's another factor like concurrent resource contention affecting which CLIs get API responses before timeout.

### Proposed solutions (to brainstorm)

1. **Feed only assigned pages** — The analysis.json already maps pages to disciplines. Change the prompt from "read all pages for context" to "read ONLY these specific pages". For example, fire-protection might only need 5-10 pages, not 75. This alone could fix the problem.

2. **Embed page text in prompt** — Instead of using Read tool for 75 separate files, concatenate the relevant page text directly into the prompt. Eliminates tool call overhead, gives deterministic context usage, and lets us calculate exact token counts before launch.

3. **Token budget estimation** — Before launching, estimate tokens: `prompt + page_text + standards ≈ (chars / 4)`. Skip/split if over 180K tokens.

4. **Reduce "all pages for context"** — Most disciplines only need their own pages plus maybe a cover sheet. Removing the "all pages" instruction could reduce context by 80-90%.

---

## Issue 2: synthesize.py Crash (NoneType)

### Error
```
File "synthesize.py", line 621, in write_synthesis_stats
    f"{(f.get('title','') or f.get('issue',''))[:100]}")
TypeError: 'NoneType' object is not subscriptable
```

### Cause
In `merge_findings()` line 384: `'issue': f.get('issue', '')` — when the raw item has `issue` key with value `None`, `.get('issue', '')` returns `None` (not `''`), because the key exists.

In `write_synthesis_stats()`: `f.get('title','')` = `''`, `f.get('issue','')` = `None`, then `'' or None` = `None`, then `None[:100]` crashes.

### Fix
```python
# Line 621 — change:
f"{(f.get('title','') or f.get('issue',''))[:100]}"
# To:
f"{(f.get('title') or f.get('issue') or '')[:100]}"
```

Also fix the source in merge_findings line 384:
```python
'issue': f.get('issue') or '',
```

---

## Issue 3: "NA" Status Items (10 items)

### What happened
The communications discipline (TIDG standards) produced 10 items with status "NA" (Not Applicable) — construction/closeout phase requirements like "provide cable test reports" that can't be evaluated at 50% DD.

### Impact
Number validation: C(8)+D(0)+O(61)+X(15) = 84, but Total = 94. The 10 NA items aren't counted.

### Fix options
1. Count NA items in validation (add to expected total)
2. Filter NA items during normalization (drop them or convert to C with a note)
3. Add NA to the prompt's allowed status values (most accurate)
4. Treat NA as Omission at DD phase (if the requirement exists, it should be addressed)

---

## Issue 4: generate_reports.py Validation Failure

### Error
FAILED file: `NUMBER VALIDATION FAILED: Discipline communications: C(8)+D(0)+O(61)+X(15) = 84 != Total(94)`

### Cause
This is a downstream effect of Issue 3. The report generator validates that C+D+O+X = total for each discipline. The 10 NA items break this check.

### Fix
Depends on how we handle Issue 3. Either validate C+D+O+X+NA = total, or ensure NA items are filtered/converted before this point.

---

## Issue 5: Schema Inconsistencies (Minor)

Some TIDG findings used a different field schema:
```json
{"id": "F-012", "standard": "TIDG", "section": "2.5.2.3.1", "requirement": "...", "status": "NA"}
```
vs the expected:
```json
{"finding_id": "F-comm1-001", "csi_code": "27 05 00", "standard_reference": "27 05 00, Part 1.1", ...}
```

The `normalize_item_fields()` ALIASES dict doesn't cover `standard` → `standard_reference` or `section`. The TIDG items use `id` → `finding_id` (this IS covered), and `standard` → not mapped.

### Fix
Add ALIASES: `'standard_reference': [..., 'standard', 'section']`

---

## What Worked Well

1. **Standards splitting** — Communications correctly split into 3 parts (part1: 146KB, part2: 125KB, part3: 136KB), all 3 succeeded eventually
2. **Retry mechanism** — Recovered 2 of 10 failed units (communications-part1, hvac-controls-part2)
3. **Partial results** — Pipeline continued with 5/13 units, synthesis produced 182 requirements
4. **Executive summary** — Correctly noted the incomplete review and missing disciplines
5. **Merged discipline parts** — Communications 3 parts correctly merged to 94 requirements
6. **Phase 2b (Haiku summary)** — Completed in 39 seconds

---

## Priority Fix Order (for tomorrow)

### P0 — Must fix before next test
1. **Feed only assigned pages per discipline** (Issue 1) — Biggest impact. Change prompt to only Read the pages listed in PAGE HINTS, not all 75.
2. **Fix NoneType crash in synthesize.py** (Issue 2) — 1-line fix
3. **Handle NA status in validation** (Issues 3+4) — Either filter or count NA items

### P1 — Should fix
4. **Token budget check** — Calculate expected context before launch, warn/skip if over limit
5. **Schema alias coverage** — Add missing TIDG field mappings
6. **Embed page text option** — Concatenate relevant pages into prompt instead of Read tool calls

### P2 — Nice to have
7. **Reduce batch concurrency** — Consider 4-5 per batch instead of 8
8. **Better error capture** — If CLI exits with "Prompt is too long", capture it to stderr too
9. **API migration** — Would give precise token counting and better error handling

---

## Raw Data Available

- Job dir: `C:\Users\john.slagboom\Desktop\Git\reviews\4fbcf67d-ffe9-46b4-adfb-60040f183f13\`
- All stdout/stderr logs in `output/`
- review-data.json (259KB, 182 requirements from 3 disciplines)
- executive-summary.txt (correctly identifies incomplete review)
- 5 discipline findings files + 2 merged files
