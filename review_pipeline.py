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


def estimate_tokens(text):
    """Estimate token count from character count."""
    return len(text) // CHARS_PER_TOKEN
