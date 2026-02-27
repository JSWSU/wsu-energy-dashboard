# Pipeline Reliability & Performance Improvements

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the 5 reliability and performance issues identified during live monitoring of job 20260226-114855, reducing failure rate and total run time.

**Architecture:** All changes are in `review-server.pl` (the Perl script that generates bash run scripts). The generated bash scripts invoke Claude CLI for discipline scanning. Fixes target the script generation code — not the generated scripts themselves. One fix is in `synthesize.py` for encoding.

**Tech Stack:** Perl 5, Bash, Claude CLI, Python 3

**Observed Issues (from monitoring job 20260226-114855):**

| # | Issue | Impact | Root Cause |
|---|-------|--------|------------|
| 1 | Plumbing hit 32K output token limit | Discipline failure, requires retry | `CLAUDE_CODE_MAX_OUTPUT_TOKENS` not set |
| 2 | 3/8 disciplines failed initial launch ("Prompt is too long") | 80 min of sequential retries | 8 simultaneous API calls cause rate limiting |
| 3 | Sequential retries took 80 min for 4 disciplines | 3x longer total run time | Retries run one-at-a-time |
| 4 | JSON sanitizer regex has structural corruption risk | Could delete valid JSON, forcing unnecessary retry | Regex `(\d)"([,}])` matches JSON structural quotes |
| 5 | UTF-8 encoding mangled (§ → Â§, em-dash garbled) | Cosmetic corruption in reports | Missing encoding declaration on file I/O |

**Not bugs (already handled):**
- Summary key schema inconsistency (`total` vs `total_requirements`) — `synthesize.py` recomputes summaries from actual statuses (line 569), ignoring Claude's summary block entirely
- Bracketed status values (`[C]` vs `C`) — `normalize_item_fields()` (line 87) strips brackets

---

### Task 1: Set CLAUDE_CODE_MAX_OUTPUT_TOKENS

Plumbing produced 93 requirements — the JSON response exceeded Claude CLI's default 32K output token limit. Setting a higher limit prevents this failure class entirely.

**Files:**
- Modify: `review-server.pl:823` (after the `CLAUDE_CODE_GIT_BASH_PATH` export)

**Step 1: Add the environment variable export**

After line 823 (`export CLAUDE_CODE_GIT_BASH_PATH`), within the same `if` block's closing `fi` (line 824), add a new export after the `fi`:

```perl
    # Line 824 currently: print $fh "fi\n\n";
    # Add AFTER that line:
    print $fh "export CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000\n\n";
```

This inserts `export CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000` into the generated bash script, right after the Git Bash path setup and before `cd "$ROOT"`. It applies to all Claude CLI invocations (Phase 1 initial, Phase 1 retry, and Phase 2b exec summary).

**Step 2: Verify the generated script**

Submit a test job via the portal, then immediately check the generated script:

```bash
JOB=$(ls -td reviews/*/  | head -1)
grep "MAX_OUTPUT" "$JOB/run-review.sh"
```

Expected output: `export CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000`

**Step 3: Commit**

```bash
git add review-server.pl
git commit -m "Set CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000 to prevent token limit failures

Plumbing discipline (93 requirements) hit the default 32K output token
limit. 128K allows up to ~4x larger JSON responses without truncation."
```

---

### Task 2: Stagger Parallel Launches

All 8 Claude CLI instances launch simultaneously, overwhelming the API and causing "Prompt is too long" errors on 3/8 disciplines. Adding a 3-second stagger between launches spreads the API load.

**Files:**
- Modify: `review-server.pl:935-936` (inside the per-discipline launch loop)

**Step 1: Add sleep between launches**

Currently lines 935-936 launch each discipline and immediately continue to the next:

```perl
            print $fh "  2> \"$stderr\" &\n";
            print $fh "WAVE_PIDS=\"\$WAVE_PIDS \$!\"\n\n";
```

Add a 3-second stagger after each launch (except the last in a wave). The loop variable `$grp` iterates over `@$wave`. We need to know if this is the last discipline in the wave.

Replace lines 920-937 with:

```perl
        my $wave_size = scalar @$wave;
        my $grp_idx = 0;
        for my $grp (@$wave) {
            my $pfile   = "$job_dir/prompt-$grp->{key}.txt";
            my $stdout  = "$output_dir/$grp->{key}-stdout.log";
            my $stderr  = "$output_dir/$grp->{key}-stderr.log";

            (my $var_key = uc($grp->{key})) =~ s/-/_/g;  # bash-safe var name
            print $fh "# Discipline: $grp->{name}\n";
            print $fh "echo \"  Launching: $grp->{name}...\"\n";
            print $fh "PROMPT_${var_key}=\$(cat \"$pfile\")\n";
            print $fh "\"$CLAUDE_PATH\" -p \"\$PROMPT_${var_key}\" \\\n";
            print $fh "  --model sonnet \\\n";
            print $fh "  --allowedTools Read Write \\\n";
            print $fh "  --dangerously-skip-permissions \\\n";
            print $fh "  --output-format text \\\n";
            print $fh "  > \"$stdout\" \\\n";
            print $fh "  2> \"$stderr\" &\n";
            print $fh "WAVE_PIDS=\"\$WAVE_PIDS \$!\"\n";
            $grp_idx++;
            # Stagger launches to avoid API rate limiting
            if ($grp_idx < $wave_size) {
                print $fh "sleep 3\n";
            }
            print $fh "\n";
        }
```

**Step 2: Verify the generated script**

Submit a test job, then check:

```bash
JOB=$(ls -td reviews/*/  | head -1)
grep -c "sleep 3" "$JOB/run-review.sh"
```

Expected: `7` (one sleep between each of the 8 launches, except after the last)

**Step 3: Commit**

```bash
git add review-server.pl
git commit -m "Add 3-second stagger between parallel discipline launches

8 simultaneous Claude CLI launches caused 'Prompt is too long' API errors
on 3/8 disciplines. Staggering by 3s spreads the load across ~24 seconds
while keeping all disciplines running in parallel."
```

---

### Task 3: Parallelize Retry Attempts

When 4 disciplines need retrying, the current sequential approach takes ~80 minutes (4 x ~20 min each). Running retries in parallel reduces this to ~20 minutes.

**Files:**
- Modify: `review-server.pl:994-1032` (the retry loop section)

**Step 1: Replace sequential retry loop with parallel retry**

Replace lines 994-1032 with a parallel retry approach. Each retry attempt launches all missing disciplines simultaneously (like Phase 1), waits, validates, and repeats up to 3 times.

Replace the entire block from line 994 (`print $fh "if [ -n \"\$MISSING\" ]; then\n";`) through line 1032 (`print $fh "fi\n\n";`) with:

```perl
    print $fh "if [ -n \"\$MISSING\" ]; then\n";
    print $fh "  echo \"Retrying failed disciplines:\$MISSING\" >> \"$output_dir/progress.log\"\n";
    print $fh "  for attempt in 1 2 3; do\n";
    print $fh "    [ -z \"\$MISSING\" ] && break\n";
    print $fh "    echo \"  Retry attempt \$attempt/3 for:\$MISSING\"\n";
    print $fh "    echo \"  Retry attempt \$attempt/3 for:\$MISSING\" >> \"$output_dir/progress.log\"\n";
    print $fh "    [ \"\$attempt\" -gt 1 ] && sleep 10\n";
    print $fh "    WAVE_PIDS=\"\"\n";
    # Launch all missing disciplines in parallel
    print $fh "    for key in \$MISSING; do\n";
    print $fh "      PROMPT_VAR=\$(cat \"$job_dir/prompt-\${key}.txt\")\n";
    print $fh "      \"$CLAUDE_PATH\" -p \"\$PROMPT_VAR\" \\\n";
    print $fh "        --model sonnet \\\n";
    print $fh "        --allowedTools Read Write \\\n";
    print $fh "        --dangerously-skip-permissions \\\n";
    print $fh "        --output-format text \\\n";
    print $fh "        > \"$output_dir/\${key}-retry-stdout.log\" \\\n";
    print $fh "        2> \"$output_dir/\${key}-retry-stderr.log\" &\n";
    print $fh "      WAVE_PIDS=\"\$WAVE_PIDS \$!\"\n";
    print $fh "      sleep 3\n";
    print $fh "    done\n";
    print $fh "    wait\n";
    print $fh "    cleanup_wave\n";
    # Check which succeeded
    print $fh "    STILL_MISSING=\"\"\n";
    print $fh "    for key in \$MISSING; do\n";
    print $fh "      jf=\"$output_dir/discipline-\${key}-findings.json\"\n";
    print $fh "      if [ -f \"\$jf\" ]; then\n";
    print $fh "        if \"\$PYTHON\" -c \"import json,sys; json.load(open(sys.argv[1]))\" \"\$jf\" 2>/dev/null; then\n";
    print $fh "          FOUND=\$((FOUND + 1))\n";
    print $fh "          echo \"  Retry \$attempt succeeded for \$key\" >> \"$output_dir/progress.log\"\n";
    print $fh "          echo \"  Retry \$attempt succeeded for \$key\"\n";
    print $fh "        else\n";
    print $fh "          echo \"  Retry \$attempt: invalid JSON for \$key\"\n";
    print $fh "          rm \"\$jf\"\n";
    print $fh "          STILL_MISSING=\"\$STILL_MISSING \$key\"\n";
    print $fh "        fi\n";
    print $fh "      else\n";
    print $fh "        echo \"  Retry \$attempt: no output for \$key\"\n";
    print $fh "        STILL_MISSING=\"\$STILL_MISSING \$key\"\n";
    print $fh "      fi\n";
    print $fh "    done\n";
    print $fh "    MISSING=\"\$STILL_MISSING\"\n";
    print $fh "  done\n";
    # Report any still-missing after all retries
    print $fh "  if [ -n \"\$MISSING\" ]; then\n";
    print $fh "    for key in \$MISSING; do\n";
    print $fh "      echo \"  FAILED: \$key after 3 retries\" >> \"$output_dir/progress.log\"\n";
    print $fh "    done\n";
    print $fh "  fi\n";
    print $fh "fi\n\n";
```

**Step 2: Verify the generated script**

Submit a test job, then check the retry section:

```bash
JOB=$(ls -td reviews/*/  | head -1)
grep -A5 "Retry attempt" "$JOB/run-review.sh" | head -20
```

Expected: Retries should show parallel launch pattern (background `&` and `wait`)

**Step 3: Commit**

```bash
git add review-server.pl
git commit -m "Parallelize retry attempts for failed disciplines

Sequential retries of 4 disciplines took ~80 minutes. Parallel retries
with 3-second stagger reduce this to ~20 minutes per attempt. Each retry
round launches all missing disciplines simultaneously, waits, then checks
which succeeded before the next round."
```

---

### Task 4: Safer JSON Sanitizer

The current regex `re.sub(r'(\d)"([,}])', r'\1 in."\2', fixed)` could theoretically match JSON structural boundaries. While the `json.loads(fixed)` guard prevents writing syntactically invalid output, we should (a) back up before repair and (b) tighten the regex.

**Files:**
- Modify: `review-server.pl:957-971` (the sanitizer Python heredoc)

**Step 1: Replace the sanitizer heredoc**

Replace lines 957-971 (from `print $fh "  \"\$PYTHON\" - \"\$jf\" <<'PYEOF'\n";` through `print $fh "PYEOF\n";`) with:

```perl
    print $fh "  \"\$PYTHON\" - \"\$jf\" <<'PYEOF'\n";
    print $fh 'import re, json, sys, shutil' . "\n";
    print $fh 'src = sys.argv[1]' . "\n";
    print $fh 'bak = src + ".bak"' . "\n";
    print $fh 'shutil.copy2(src, bak)' . "\n";
    print $fh 'with open(src, "r", encoding="utf-8") as f:' . "\n";
    print $fh '    text = f.read()' . "\n";
    print $fh '# Fix unescaped inch marks inside JSON string values.' . "\n";
    print $fh '# Only match: digit + " + space + word-char (e.g. 24" wide -> 24 in. wide)' . "\n";
    print $fh 'fixed = re.sub(r\'(\d)"(\s+\w)\', r\'\\1 in.\\2\', text)' . "\n";
    print $fh '# Fix fraction inch marks: digit/digit + " (e.g. 3/4" -> 3/4 in.)' . "\n";
    print $fh 'fixed = re.sub(r\'(\d/\d+)"\', r\'\\1 in.\', fixed)' . "\n";
    print $fh '# Fix foot-inch: digit\'-digit" (e.g. 5\'-0" -> 5 ft-0 in.)' . "\n";
    print $fh 'fixed = re.sub(r"(\\d+)\'-(\\d+)\"", r"\\1 ft-\\2 in.", fixed)' . "\n";
    print $fh 'try:' . "\n";
    print $fh '    json.loads(fixed)' . "\n";
    print $fh '    with open(src, "w", encoding="utf-8") as f:' . "\n";
    print $fh '        f.write(fixed)' . "\n";
    print $fh '    print("  Repaired successfully")' . "\n";
    print $fh '    import os; os.remove(bak)' . "\n";
    print $fh 'except json.JSONDecodeError as e:' . "\n";
    print $fh '    shutil.move(bak, src)  # restore original' . "\n";
    print $fh '    print(f"  Could not auto-repair: {e}", file=sys.stderr)' . "\n";
    print $fh "PYEOF\n";
```

Key changes:
- **Backup before repair** — copies file to `.bak`, restores on failure
- **Tighter regex 1** — `(\d)"(\s+\w)` requires space THEN word-char after the inch mark (avoids matching `"value": "24"\n}`)
- **New regex 2** — `(\d/\d+)"` targets fraction measurements like `3/4"`
- **New regex 3** — `(\d+)'-(\d+)"` targets foot-inch like `5'-0"`
- **Removed dangerous regex** — `(\d)"([,}])` no longer used
- **UTF-8 encoding** — explicit `encoding="utf-8"` on file open

**Step 2: Verify**

Create a test JSON file with known measurement patterns:

```bash
cat > /tmp/test-sanitize.json <<'EOF'
{"req": "Pipe must be 3/4" copper", "size": "24" minimum", "height": "5'-0" from floor", "count": 24}
EOF
python -c "
import re, json
text = open('/tmp/test-sanitize.json').read()
fixed = re.sub(r'(\d)\"(\s+\w)', r'\1 in.\2', text)
fixed = re.sub(r'(\d/\d+)\"', r'\1 in.', fixed)
fixed = re.sub(r\"(\d+)'-(\d+)\\\"\", r'\1 ft-\2 in.', fixed)
try:
    json.loads(fixed)
    print('PASS:', fixed)
except: print('FAIL:', fixed)
"
```

Expected: Valid JSON with measurements converted.

**Step 3: Commit**

```bash
git add review-server.pl
git commit -m "Safer JSON sanitizer: backup, tighter regex, UTF-8 encoding

- Back up .json to .bak before attempting repair; restore on failure
- Replace broad (\d)\"([,}]) regex with targeted fraction/foot-inch patterns
- Add explicit UTF-8 encoding on file I/O
- Prevents theoretical corruption of valid JSON structural quotes"
```

---

### Task 5: Fix UTF-8 Encoding in Synthesize

The `§` symbol in standard references (e.g., `WSU 23 00 00 §1.01.E`) appears as `Â§` in the final output — a classic double-encoded UTF-8 artifact. The fix is to ensure consistent UTF-8 handling in `synthesize.py` file reads.

**Files:**
- Modify: `synthesize.py` — the `load_discipline()` function's `open()` call

**Step 1: Find the file open call in load_discipline**

In `synthesize.py`, the `load_discipline()` function opens JSON files. Add explicit `encoding='utf-8'` to the open call.

Find the line (around line 120-140) that reads:
```python
with open(filepath) as f:
```

Replace with:
```python
with open(filepath, encoding='utf-8') as f:
```

Also find any other `open()` calls in the file (for writing `review-data.json`, `synthesis-stats.txt`, etc.) and add `encoding='utf-8'` to each.

**Step 2: Add encoding normalization for double-encoded UTF-8**

Add a helper function after `normalize_item_fields()` (after line 92):

```python
def fix_double_encoding(text):
    """Fix double-encoded UTF-8 (e.g., Â§ -> §, â€" -> —)."""
    if not isinstance(text, str):
        return text
    try:
        # Detect double-encoding: encode as latin-1 then decode as UTF-8
        return text.encode('latin-1').decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text  # not double-encoded, return as-is
```

Then in `normalize_item_fields()`, apply it to text fields. After the bracketed status normalization (line 90), add:

```python
    # Fix double-encoded UTF-8 in text fields
    for field in ('issue', 'required_action', 'standard_reference', 'requirement', 'notes'):
        val = item.get(field)
        if val:
            item[field] = fix_double_encoding(val)
```

**Step 3: Verify**

```bash
python -c "
def fix_double_encoding(text):
    try: return text.encode('latin-1').decode('utf-8')
    except: return text
print(repr(fix_double_encoding('WSU 23 00 00 Â§1.01.E')))
print(repr(fix_double_encoding('Architectural â€" Finishes')))
print(repr(fix_double_encoding('Normal ASCII text')))
"
```

Expected:
```
'WSU 23 00 00 §1.01.E'
'Architectural — Finishes'
'Normal ASCII text'
```

**Step 4: Commit**

```bash
git add synthesize.py
git commit -m "Fix double-encoded UTF-8 in synthesis output (Â§ -> §)

Claude CLI outputs UTF-8 text that gets double-encoded when read without
explicit encoding. Add encoding='utf-8' to all file I/O and a
fix_double_encoding() helper that detects and repairs Â§ -> § and
â€" -> — in standard references and discipline names."
```

---

### Task 6: Final Verification

Run a complete end-to-end test to confirm all fixes work together.

**Step 1: Restart the server**

```bash
# Kill existing server
tasklist | grep -i perl | awk '{print $2}' | xargs -I{} taskkill //PID {} //F
# Start fresh
cd /c/Users/john.slagboom/Desktop/Git/.claude/worktrees/objective-noether
perl review-server.pl
```

**Step 2: Submit a test review via the portal**

Use the same TFREC DD drawings PDF. Select all 8 discipline groups.

**Step 3: Verification checklist**

While the job runs, verify these in the generated `run-review.sh`:

- [ ] `export CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000` appears before Phase 1
- [ ] `sleep 3` appears between discipline launches (7 occurrences)
- [ ] Retry section uses `&` (parallel) not sequential
- [ ] Sanitizer has `shutil.copy2` backup and tighter regex
- [ ] No `(\d)"([,}])` regex pattern in sanitizer

After job completes, verify:

- [ ] All 8 discipline JSONs produced
- [ ] No "exceeded the 32000 output token maximum" in any stdout log
- [ ] `§` symbols render correctly in synthesis-stats.txt
- [ ] No `Â§` or `â€"` in review-data.json
- [ ] Total run time reduced (target: under 60 min if all disciplines succeed on first try)

**Step 4: Final commit (if any adjustments needed)**

```bash
git add -A
git commit -m "Adjust [specific fix] after end-to-end verification"
```
