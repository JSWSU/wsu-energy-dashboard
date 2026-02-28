#!/usr/bin/env python3
"""
WSU Design Standards Compliance Review — Synthesis (Phase 2 replacement)
Merges per-discipline findings JSON files into a single review-data.json.

Replaces the Claude CLI Phase 2 call with deterministic Python logic.
Reads job.json from parent directory for project metadata.
Reads all discipline-*-findings.json from output_dir.

Usage: python synthesize.py <output_dir>

Outputs (written to output_dir):
  - review-data.json     Merged + renumbered review data
  - synthesis-stats.txt  Human-readable summary for Claude exec summary prompt
"""

import glob
import json
import os
import re
import sys
from datetime import date

# ---------------------------------------------------------------------------
# Constants (mirror review-server.pl @ALL_GROUPS)
# ---------------------------------------------------------------------------
DISCIPLINE_META = {
    'arch-structure':  'Architectural — Structure & Envelope',
    'arch-finishes':   'Architectural — Finishes & Equipment',
    'fire-protection': 'Fire Protection and Security',
    'plumbing':        'Plumbing',
    'hvac-controls':   'HVAC and Building Automation',
    'electrical':      'Electrical',
    'communications':  'Communications and Technology',
    'civil-site':      'Civil, Site, and Utilities',
}

SEVERITY_NORMALIZE = {
    'low': 'Minor', 'minor': 'Minor',
    'medium': 'Major', 'moderate': 'Major', 'major': 'Major',
    'high': 'Critical', 'critical': 'Critical',
    'n/a': None, 'na': None, 'not applicable': None, 'none': None,
}

SEVERITY_ORDER = {'Critical': 0, 'Major': 1, 'Minor': 2}

# ---------------------------------------------------------------------------
# Discovery & loading
# ---------------------------------------------------------------------------
def discover_discipline_files(output_dir):
    """Glob for discipline-*-findings.json, return sorted list of paths."""
    pattern = os.path.join(output_dir, 'discipline-*-findings.json')
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"ERROR: No discipline findings files found in {output_dir}", file=sys.stderr)
    return files


def extract_discipline_key(filepath):
    """Extract discipline key from filename: discipline-{key}-findings.json"""
    basename = os.path.basename(filepath)
    m = re.match(r'^discipline-(.+)-findings\.json$', basename)
    return m.group(1) if m else None


def normalize_item_fields(item):
    """Map variant field names to canonical schema. Handles all known Claude output variants."""
    # Field name aliases: canonical_name -> [alternate names]
    ALIASES = {
        'issue':              ['description', 'issue_description', 'finding_description'],
        'required_action':    ['recommendation', 'action', 'corrective_action', 'action_required'],
        'standard_reference': ['standard_citation', 'standard', 'reference'],
        'finding_id':         ['id', 'finding_number'],
        'requirement':        ['requirement_text', 'req_text', 'title'],
        'pdf_reference':      ['drawing_reference', 'page_reference', 'sheet_reference'],
        'drawing_sheet':      ['sheet', 'drawing'],
        'notes':              ['note', 'comment', 'remarks'],
    }

    for canonical, alts in ALIASES.items():
        if canonical not in item or item[canonical] is None:
            for alt in alts:
                if alt in item and item[alt] is not None:
                    item[canonical] = item[alt]
                    break

    # Normalize bracketed status: "[X]" -> "X", "[O]" -> "O"
    st = item.get('status', '')
    if isinstance(st, str) and st.startswith('[') and st.endswith(']'):
        item['status'] = st[1:-1]

    # Fix double-encoded UTF-8 in text fields
    for field in ('issue', 'required_action', 'standard_reference', 'requirement', 'notes'):
        val = item.get(field)
        if val:
            item[field] = fix_double_encoding(val)

    return item


def fix_double_encoding(text):
    """Fix double-encoded UTF-8 (e.g., Â§ -> §, â€" -> —)."""
    if not isinstance(text, str):
        return text
    try:
        # Detect double-encoding: encode as latin-1 then decode as UTF-8
        return text.encode('latin-1').decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text  # not double-encoded, return as-is


def normalize_discipline_data(data):
    """Normalize top-level structure: accept 'findings' as alias for 'requirements'."""
    # If 'requirements' is missing/empty but 'findings' has items, use 'findings'
    reqs = data.get('requirements', [])
    findings = data.get('findings', [])

    if not reqs and findings:
        data['requirements'] = findings
        print(f"      (mapped 'findings' -> 'requirements': {len(findings)} items)")

    # Normalize divisions_reviewed aliases
    if 'divisions_reviewed' not in data:
        for alt in ('csi_divisions_reviewed', 'divisions', 'divs'):
            if alt in data and data[alt]:
                data['divisions_reviewed'] = data[alt]
                break

    # Normalize each requirement item's field names
    for item in data.get('requirements', []):
        normalize_item_fields(item)

    return data


def load_discipline(filepath):
    """Read + parse one discipline JSON file. Returns (key, data) or (None, None)."""
    key = extract_discipline_key(filepath)
    if not key:
        print(f"WARNING: Cannot extract discipline key from {filepath}", file=sys.stderr)
        return None, None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"ERROR: Cannot read {filepath}: {e}", file=sys.stderr)
        return None, None

    # Normalize schema variants before returning
    normalize_discipline_data(data)

    return key, data


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------
def extract_division_from_ref(standard_reference):
    """Extract 2-digit division from standard_reference like '07 31 00' or '07 40 00 - Metal Roofing'."""
    if not standard_reference:
        return None
    m = re.match(r'(\d{2})\s', standard_reference)
    return m.group(1) if m else None


def extract_csi_code_from_ref(standard_reference):
    """Extract CSI code like '07 31 00' from standard_reference."""
    if not standard_reference:
        return None
    m = re.search(r'(\d{2}\s\d{2}\s\d{2})', standard_reference)
    return m.group(1) if m else None


def normalize_divisions_reviewed(raw_divs):
    """Normalize divisions_reviewed to 2-digit strings: '21' stays, '02 40 00 - ...' becomes '02'."""
    result = set()
    for d in (raw_divs or []):
        d_str = str(d).strip()
        m = re.match(r'^(\d{2})', d_str)
        if m:
            result.add(m.group(1))
    return sorted(result)


def normalize_severity(raw_severity):
    """Normalize severity string. Returns 'Critical', 'Major', 'Minor', or None."""
    if not raw_severity or raw_severity == 'null':
        return None
    key = raw_severity.lower().strip()
    if key in SEVERITY_NORMALIZE:
        return SEVERITY_NORMALIZE[key]  # may be None for 'n/a'
    # If already correct case
    if raw_severity in SEVERITY_ORDER:
        return raw_severity
    print(f"WARNING: Unknown severity '{raw_severity}', defaulting to Minor", file=sys.stderr)
    return 'Minor'


def normalize_requirement(req, discipline_key):
    """Fill missing division/csi_code from standard_reference, normalize severity."""
    std_ref = req.get('standard_reference', '') or ''

    # Fill missing division
    if not req.get('division'):
        div = extract_division_from_ref(std_ref)
        if div:
            req['division'] = div

    # Fill missing csi_code
    if not req.get('csi_code'):
        csi = extract_csi_code_from_ref(std_ref)
        if csi:
            req['csi_code'] = csi

    # Normalize severity
    raw_sev = req.get('severity')
    if raw_sev:
        req['severity'] = normalize_severity(raw_sev)
    else:
        req['severity'] = None

    # Ensure required fields exist
    req.setdefault('division', '')
    req.setdefault('csi_code', '')
    req.setdefault('requirement', std_ref or '')
    req.setdefault('status', 'C')
    req.setdefault('finding_id', None)
    req.setdefault('pdf_reference', '')
    req.setdefault('standard_reference', '')
    req.setdefault('issue', None)
    req.setdefault('required_action', None)
    req.setdefault('drawing_sheet', None)
    req.setdefault('notes', '')

    return req


# ---------------------------------------------------------------------------
# Merging
# ---------------------------------------------------------------------------
def merge_findings(all_disciplines):
    """
    Collect non-compliant requirements as findings, sort by severity desc then
    division asc, renumber F-001..., build id_map for updating references.

    Returns (findings_list, requirements_list, id_map, variances_list)
    """
    raw_findings = []
    all_requirements = []

    for disc_key, disc_data in all_disciplines:
        reqs = disc_data.get('requirements', [])
        for req in reqs:
            normalize_requirement(req, disc_key)
            req['_discipline'] = disc_key

            # Collect non-compliant as findings
            if req.get('status') in ('D', 'O', 'X'):
                raw_findings.append(req)

            all_requirements.append(req)

    # Sort findings: severity desc (Critical first), then division asc
    def sort_key(f):
        sev = SEVERITY_ORDER.get(f.get('severity', ''), 99)
        div = f.get('division', '99')
        return (sev, div)

    raw_findings.sort(key=sort_key)

    # Renumber F-001, F-002, ...
    id_map = {}  # old finding_id -> new F-number
    findings = []
    for i, f in enumerate(raw_findings, 1):
        new_id = f'F-{i:03d}'
        old_id = f.get('finding_id', '')
        if old_id:
            id_map[old_id] = new_id

        finding = {
            'id': new_id,
            'discipline': f['_discipline'],
            'division': f.get('division', ''),
            'csi_code': f.get('csi_code', ''),
            'title': f.get('issue', '') or '',
            'severity': f.get('severity') or 'Minor',
            'status': f.get('status', 'D'),
            'pdf_reference': f.get('pdf_reference', ''),
            'standard_reference': f.get('standard_reference', ''),
            'issue': f.get('issue', ''),
            'required_action': f.get('required_action', ''),
        }
        findings.append(finding)

    # Update requirement finding_refs
    update_requirement_refs(all_requirements, id_map)

    # Build clean requirements list (without internal _discipline key)
    requirements = []
    for req in all_requirements:
        requirements.append({
            'division': req.get('division', ''),
            'csi_code': req.get('csi_code', ''),
            'requirement': req.get('requirement', ''),
            'status': req.get('status', 'C'),
            'finding_ref': req.get('_new_finding_ref'),
            'drawing_sheet': req.get('drawing_sheet'),
            'notes': req.get('notes', ''),
        })

    # Build variances from all [D] Deviation findings
    variances = build_variances(findings)

    return findings, requirements, id_map, variances


def update_requirement_refs(requirements, id_map):
    """Update old finding_id references to new F-numbers."""
    for req in requirements:
        old_id = req.get('finding_id')
        if old_id and old_id in id_map:
            req['_new_finding_ref'] = id_map[old_id]
        elif req.get('status') in ('D', 'O', 'X') and old_id:
            # Finding existed but wasn't mapped (shouldn't happen normally)
            req['_new_finding_ref'] = old_id
        else:
            req['_new_finding_ref'] = None


def build_variances(findings):
    """All [D] Deviation findings become variance candidates."""
    variances = []
    v_num = 0
    for f in findings:
        if f.get('status') == 'D':
            v_num += 1
            variances.append({
                'id': f'V-{v_num:02d}',
                'finding_ref': f['id'],
                'division': f.get('division', ''),
                'csi_code': f.get('csi_code', ''),
                'description': f.get('issue', ''),
                'justification': '',
                'approval_status': 'Pending',
            })
    return variances


# ---------------------------------------------------------------------------
# Narratives
# ---------------------------------------------------------------------------
def build_narratives(all_disciplines, findings):
    """Build template narratives. Exec summary = PLACEHOLDER for Claude."""
    # Collect drawing sheets mentioned
    sheets = set()
    for _, disc_data in all_disciplines:
        # Check for drawings_reviewed field
        for dr in disc_data.get('drawings_reviewed', []):
            sheets.add(str(dr))
        # Also scan requirements for drawing_sheet
        for req in disc_data.get('requirements', []):
            ds = req.get('drawing_sheet')
            if ds and ds != 'N/A':
                sheets.add(str(ds))

    # Collect N/A determinations
    na_notes = []
    for disc_key, disc_data in all_disciplines:
        disc_name = DISCIPLINE_META.get(disc_key, disc_key)
        for req in disc_data.get('requirements', []):
            notes = req.get('notes', '') or ''
            if 'not applicable' in notes.lower() or 'n/a' in notes.lower():
                na_notes.append(f"- {disc_name}: {notes[:200]}")

    drawing_inventory = 'Sheets reviewed:\n' + '\n'.join(f'  - {s}' for s in sorted(sheets)) if sheets else 'See PDF drawing set.'
    applicability = '\n'.join(na_notes[:20]) if na_notes else 'All selected divisions were reviewed against applicable standards.'
    methodology = (
        'Automated review performed against current WSU Facilities Services Design and '
        'Construction Standards (June 2025 edition). Each discipline group was reviewed '
        'independently, then findings were merged, renumbered, and cross-validated. '
        'The review covers drawing-visible requirements only; specifications were not available.'
    )
    limitations = (
        'This review is based on the construction drawing set only. Project specifications, '
        'submittals, and shop drawings were not available for review. Some requirements '
        'that are specification-dependent are flagged as omissions where drawing evidence is absent.'
    )

    return {
        'executive_summary': 'PLACEHOLDER',
        'methodology': methodology,
        'drawing_inventory': drawing_inventory,
        'applicability_notes': applicability,
        'limitations': limitations,
    }


# ---------------------------------------------------------------------------
# Validation (mirrors generate_reports.py lines 101-151)
# ---------------------------------------------------------------------------
def validate_output(data):
    """Same validation checks as generate_reports.py. Returns list of errors."""
    errors = []
    findings = data.get('findings', [])
    disciplines = data.get('disciplines', [])
    requirements = data.get('requirements', [])

    # Count findings by severity
    sev_counts = {'Critical': 0, 'Major': 0, 'Minor': 0}
    for f in findings:
        s = f.get('severity', '')
        if s in sev_counts:
            sev_counts[s] += 1
        elif s:
            errors.append(f"Finding {f.get('id','?')}: unknown severity '{s}'")
        else:
            errors.append(f"Finding {f.get('id','?')}: missing severity")

    # Count non-compliant from discipline summaries
    disc_nc = 0
    disc_total_req = 0
    for d in disciplines:
        s = d.get('summary', {})
        row_d = s.get('deviations', 0)
        row_o = s.get('omissions', 0)
        row_x = s.get('concerns', 0)
        row_c = s.get('compliant', 0)
        row_total = s.get('total_requirements', 0)
        disc_nc += row_d + row_o + row_x
        disc_total_req += row_total
        if row_c + row_d + row_o + row_x != row_total:
            errors.append(
                f"Discipline {d['key']}: C({row_c})+D({row_d})+O({row_o})+X({row_x}) "
                f"= {row_c+row_d+row_o+row_x} != Total({row_total})"
            )

    if len(findings) == 0:
        errors.append('No findings in findings array')

    if len(findings) > disc_nc and disc_nc > 0:
        errors.append(
            f"Findings count ({len(findings)}) exceeds discipline "
            f"non-compliant total ({disc_nc})"
        )

    req_count = len(requirements)
    if req_count > 0 and req_count != disc_total_req:
        errors.append(f"Requirements list ({req_count}) != discipline total ({disc_total_req})")

    return errors


# ---------------------------------------------------------------------------
# Stats file (for Claude exec summary prompt)
# ---------------------------------------------------------------------------
def write_synthesis_stats(output_dir, data):
    """Write human-readable summary for Claude exec summary prompt."""
    findings = data.get('findings', [])
    disciplines = data.get('disciplines', [])
    requirements = data.get('requirements', [])
    project = data.get('project', {})

    total_req = sum(d.get('summary', {}).get('total_requirements', 0) for d in disciplines)
    total_compliant = sum(d.get('summary', {}).get('compliant', 0) for d in disciplines)
    compliance_pct = (total_compliant / total_req * 100) if total_req > 0 else 0

    sev = {'Critical': 0, 'Major': 0, 'Minor': 0}
    for f in findings:
        s = f.get('severity', 'Minor')
        if s in sev:
            sev[s] += 1

    lines = [
        'WSU DESIGN STANDARDS COMPLIANCE REVIEW — SYNTHESIS STATISTICS',
        '=' * 60,
        '',
        f"Project: {project.get('name', '')}",
        f"Phase: {project.get('phase', '')}",
        f"Construction Type: {project.get('constructionType', '')}",
        f"Review Date: {project.get('reviewDate', '')}",
        '',
        f"Disciplines Reviewed: {len(disciplines)}",
        f"Total Requirements Checked: {total_req}",
        f"Overall Compliance: {compliance_pct:.1f}%",
        '',
        'FINDINGS BY SEVERITY:',
        f"  Critical: {sev['Critical']}",
        f"  Major:    {sev['Major']}",
        f"  Minor:    {sev['Minor']}",
        f"  Total:    {sum(sev.values())}",
        '',
        'DISCIPLINE BREAKDOWN:',
    ]

    for d in disciplines:
        s = d.get('summary', {})
        name = d.get('name', d.get('key', ''))
        t = s.get('total_requirements', 0)
        c = s.get('compliant', 0)
        pct = f"{c/t*100:.1f}%" if t > 0 else "N/A"
        lines.append(f"  {name}: {t} requirements, {pct} compliant, "
                     f"{s.get('deviations',0)}D / {s.get('omissions',0)}O / {s.get('concerns',0)}X")

    # Missing / failed disciplines
    missing = data.get('missingDisciplines', [])
    empty = data.get('emptyDisciplines', [])
    if missing or empty:
        lines.append('')
        lines.append('INCOMPLETE REVIEW WARNING:')
        if missing:
            lines.append(f"  {len(missing)} discipline(s) failed to produce any results:")
            for md in missing:
                lines.append(f"    - {md['name']}")
        if empty:
            lines.append(f"  {len(empty)} discipline(s) produced empty results (0 requirements):")
            for ed in empty:
                lines.append(f"    - {ed['name']}")
        lines.append("  The compliance statistics above reflect ONLY the disciplines that produced results.")
        lines.append("  This review is INCOMPLETE — the missing disciplines were not evaluated.")

    if sev['Critical'] > 0:
        lines.append('')
        lines.append('CRITICAL FINDINGS:')
        for f in findings:
            if f.get('severity') == 'Critical':
                lines.append(f"  {f['id']}: [{f.get('status','')}] Div {f.get('division','')} — "
                             f"{(f.get('title','') or f.get('issue',''))[:100]}")

    stats_path = os.path.join(output_dir, 'synthesis-stats.txt')
    with open(stats_path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines))
    print(f"  Written: {stats_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    if len(sys.argv) < 2:
        print("Usage: python synthesize.py <output_dir>")
        sys.exit(1)

    output_dir = sys.argv[1]
    if not os.path.isdir(output_dir):
        print(f"ERROR: Output directory does not exist: {output_dir}", file=sys.stderr)
        sys.exit(1)

    # Read job.json from parent directory
    job_dir = os.path.dirname(os.path.abspath(output_dir))
    job_path = os.path.join(job_dir, 'job.json')
    job = {}
    if os.path.isfile(job_path):
        with open(job_path, 'r', encoding='utf-8') as f:
            job = json.load(f)
        print(f"  Read job metadata: {job.get('projectName', '')}")
    else:
        print(f"WARNING: No job.json found at {job_path}", file=sys.stderr)

    # Discover and load discipline files
    files = discover_discipline_files(output_dir)
    if not files:
        err = 'No discipline findings files found'
        with open(os.path.join(output_dir, 'FAILED'), 'w', encoding='utf-8') as fh:
            fh.write(err)
        sys.exit(1)

    print(f"  Found {len(files)} discipline files")

    all_disciplines = []
    for fp in files:
        key, data = load_discipline(fp)
        if key and data:
            # Normalize requirements in-place
            for req in data.get('requirements', []):
                normalize_requirement(req, key)
            all_disciplines.append((key, data))
            print(f"    Loaded: {key} ({len(data.get('requirements', []))} requirements)")

    if not all_disciplines:
        err = 'No valid discipline files could be loaded'
        with open(os.path.join(output_dir, 'FAILED'), 'w', encoding='utf-8') as fh:
            fh.write(err)
        sys.exit(1)

    # Build discipline summaries — recompute from actual requirements (Claude miscounts)
    disciplines_out = []
    for disc_key, disc_data in all_disciplines:
        name = DISCIPLINE_META.get(disc_key, disc_key.replace('-', ' ').title())
        divs = normalize_divisions_reviewed(disc_data.get('divisions_reviewed', []))
        reqs = disc_data.get('requirements', [])

        # Recompute summary from actual requirement statuses
        counts = {'C': 0, 'D': 0, 'O': 0, 'X': 0}
        for req in reqs:
            st = req.get('status', 'C')
            if st in counts:
                counts[st] += 1

        disciplines_out.append({
            'key': disc_key,
            'name': name,
            'divisions_reviewed': divs,
            'summary': {
                'total_requirements': len(reqs),
                'compliant': counts['C'],
                'deviations': counts['D'],
                'omissions': counts['O'],
                'concerns': counts['X'],
            },
        })

    # Detect missing disciplines (expected from job.json but no JSON file produced)
    expected_groups = job.get('disciplineGroups', [])
    loaded_keys = {key for key, _ in all_disciplines}
    missing_disciplines = []
    for grp in expected_groups:
        gk = grp.get('key', '')
        if gk and gk not in loaded_keys:
            missing_disciplines.append({
                'key': gk,
                'name': grp.get('name', DISCIPLINE_META.get(gk, gk)),
                'reason': 'No findings file produced (discipline scan failed)',
            })
    # Also flag disciplines that loaded but had 0 requirements
    empty_disciplines = []
    for disc_key, disc_data in all_disciplines:
        if len(disc_data.get('requirements', [])) == 0:
            empty_disciplines.append({
                'key': disc_key,
                'name': DISCIPLINE_META.get(disc_key, disc_key),
                'reason': 'Findings file exists but contains 0 requirements',
            })

    if missing_disciplines:
        print(f"  WARNING: {len(missing_disciplines)} disciplines missing:")
        for md in missing_disciplines:
            print(f"    - {md['name']}: {md['reason']}")
    if empty_disciplines:
        print(f"  WARNING: {len(empty_disciplines)} disciplines empty:")
        for ed in empty_disciplines:
            print(f"    - {ed['name']}: {ed['reason']}")

    # Merge findings
    print("  Merging findings...")
    findings, requirements, id_map, variances = merge_findings(all_disciplines)
    print(f"    {len(findings)} findings, {len(requirements)} requirements, {len(variances)} variances")

    # Build narratives
    narratives = build_narratives(all_disciplines, findings)

    # Assemble output
    review_data = {
        'project': {
            'name': job.get('projectName', ''),
            'phase': job.get('reviewPhase', ''),
            'constructionType': job.get('constructionType', ''),
            'reviewDate': date.today().isoformat(),
        },
        'disciplines': disciplines_out,
        'findings': findings,
        'requirements': requirements,
        'variances': variances,
        'narratives': narratives,
        'missingDisciplines': missing_disciplines,
        'emptyDisciplines': empty_disciplines,
    }

    # Validate
    print("  Validating...")
    errors = validate_output(review_data)
    if errors:
        print("  VALIDATION WARNINGS (non-fatal):", file=sys.stderr)
        for e in errors:
            print(f"    - {e}", file=sys.stderr)
        # Don't fail — let generate_reports.py do the final validation gate

    # Write output
    out_path = os.path.join(output_dir, 'review-data.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(review_data, f, indent=2, ensure_ascii=False)
    print(f"  Written: {out_path}")

    # Write stats for exec summary prompt
    write_synthesis_stats(output_dir, review_data)

    print("  Synthesis complete.")
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
