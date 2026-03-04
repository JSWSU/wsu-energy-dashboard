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
        'name': 'Architectural — Structure & Envelope',
        'divs': ['02', '03', '04', '05', '07', '08'],
        'desc': 'demolition, concrete, masonry, metals, roofing, waterproofing, and openings sheets',
        'supp': [],
    },
    {
        'key': 'arch-finishes',
        'name': 'Architectural — Finishes & Equipment',
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


def estimate_tokens(text):
    """Estimate token count from character count."""
    return len(text) // CHARS_PER_TOKEN
