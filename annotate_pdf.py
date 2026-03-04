#!/usr/bin/env python3
"""
WSU Design Standards Review — PDF Annotation Generator

Reads review-data.json and the original uploaded PDF, then:
1. Groups non-compliant findings by drawing sheet
2. Maps sheet IDs to PDF page indices by scanning extracted page text
3. Renders each page as a 72 DPI image
4. Sends page image + findings list to Claude vision for coordinate identification
5. Writes FreeText callout annotations via PyMuPDF
6. Saves annotated PDF as review-markup.pdf

Usage:
    python annotate_pdf.py <job-dir>

Expects:
    <job-dir>/output/review-data.json
    <job-dir>/pages/page-NNNN.txt (extracted page text)
    <job-dir>/input.pdf
"""

import fitz  # PyMuPDF
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed


# Severity color mapping (RGB, 0-1 scale for PyMuPDF)
SEVERITY_COLORS = {
    'Critical': {'fill': (1.0, 0.85, 0.85), 'border': (0.86, 0.15, 0.15)},  # red
    'Major':    {'fill': (1.0, 0.93, 0.82), 'border': (0.96, 0.62, 0.04)},  # orange
    'Minor':    {'fill': (1.0, 1.0, 0.85),  'border': (0.80, 0.68, 0.00)},  # yellow
}
DEFAULT_COLOR = {'fill': (0.9, 0.9, 0.9), 'border': (0.5, 0.5, 0.5)}

# Sheet ID pattern: letter(s) + digit + dot + digit(s), e.g., G1.0, A1.1, M2.01
SHEET_RE = re.compile(r'\b([A-Z]{1,2}\d\.\d{1,2})\b')


def load_review_data(job_dir):
    path = os.path.join(job_dir, 'output', 'review-data.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def find_uploaded_pdf(job_dir):
    # Check for input.pdf at job root (current server convention)
    root_pdf = os.path.join(job_dir, 'input.pdf')
    if os.path.isfile(root_pdf):
        return root_pdf
    # Fallback: check upload/ subdirectory
    upload_dir = os.path.join(job_dir, 'upload')
    if os.path.isdir(upload_dir):
        for fname in os.listdir(upload_dir):
            if fname.lower().endswith('.pdf'):
                return os.path.join(upload_dir, fname)
    return None


def build_sheet_page_map(job_dir, total_pages):
    """Map sheet IDs to 0-based page indices by scanning extracted page text.

    Heuristic: each page's 'primary' sheet ID is the one that appears on that
    page but on the fewest OTHER pages (most unique to that page).  Page 1
    (the cover/index) is skipped as it references all sheets.
    """
    pages_dir = os.path.join(job_dir, 'pages')
    if not os.path.isdir(pages_dir):
        return {}

    # Collect sheet IDs per page
    page_sheets = {}  # page_idx -> set of sheet IDs
    global_counts = Counter()  # sheet_id -> how many pages mention it

    for page_idx in range(total_pages):
        fname = f'page-{page_idx + 1:04d}.txt'
        fpath = os.path.join(pages_dir, fname)
        if not os.path.isfile(fpath):
            continue
        with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read().upper()
        ids = set(SHEET_RE.findall(text))
        page_sheets[page_idx] = ids
        for sid in ids:
            global_counts[sid] += 1

    # For each page, find the most unique sheet ID
    sheet_map = {}
    for page_idx in range(total_pages):
        ids = page_sheets.get(page_idx, set())
        if not ids:
            continue
        # Pick the ID that appears on the fewest pages (most unique)
        best = min(ids, key=lambda sid: global_counts[sid])
        if best not in sheet_map:
            sheet_map[best] = page_idx

    return sheet_map


def parse_sheet_refs(ref_str):
    """Parse comma-separated sheet references, returning clean sheet IDs.

    Input: 'A1.2, A3.1' or 'G1.0, A1.1, A1.2, A3.1' or 'N/A - no scope'
    Output: ['A1.2', 'A3.1'] (skips N/A entries)
    """
    if not ref_str:
        return []
    ids = SHEET_RE.findall(ref_str.upper())
    return ids


def group_findings_by_page(findings, sheet_map):
    """Group non-compliant findings by PDF page index.

    Uses pdf_reference or drawing_sheet field, parses comma-separated sheet IDs,
    maps each to a page via sheet_map. A finding may appear on multiple pages.
    """
    groups = {}  # page_idx -> list of findings
    unmapped = 0

    for f in findings:
        status = f.get('status', '')
        if status in ('C', 'NA'):
            continue
        # Try pdf_reference first, then drawing_sheet
        ref = f.get('pdf_reference') or f.get('drawing_sheet') or ''
        sheet_ids = parse_sheet_refs(ref)
        if not sheet_ids:
            unmapped += 1
            continue
        placed = False
        for sid in sheet_ids:
            page_idx = sheet_map.get(sid)
            if page_idx is not None:
                groups.setdefault(page_idx, []).append(f)
                placed = True
                break  # Place on first matching page only
        if not placed:
            unmapped += 1

    if unmapped:
        print(f"  {unmapped} findings could not be mapped to a PDF page")
    return groups


def render_page_image(doc, page_idx, dpi=72):
    """Render a PDF page as PNG image bytes."""
    page = doc[page_idx]
    pix = page.get_pixmap(dpi=dpi)
    return pix.tobytes('png')


def call_vision_for_coordinates(page_image_path, findings_for_page, claude_path='claude'):
    """Send page image + findings to Claude vision, get back coordinates."""
    findings_text = "\n".join(
        f"- {f.get('id', f.get('finding_id', '?'))}: "
        f"{f.get('issue', f.get('requirement', 'Unknown issue'))}"
        for f in findings_for_page
    )

    prompt = (
        f"Read the image file at: {page_image_path}\n\n"
        "You are analyzing a construction drawing sheet. "
        "The following design review findings were identified on this sheet:\n\n"
        f"{findings_text}\n\n"
        "For each finding, identify the specific location on the drawing where "
        "the issue exists. Return a JSON array with one object per finding:\n"
        "[\n"
        '  { "finding_id": "F-001", "x_pct": 45.2, "y_pct": 62.8 }\n'
        "]\n\n"
        "x_pct and y_pct are percentages (0-100) of the page width and height "
        "respectively, measured from the TOP-LEFT corner.\n\n"
        "If you cannot identify a specific location for a finding (e.g., "
        "something is missing from the drawing entirely), set x_pct and y_pct "
        "to -1.\n\n"
        "Return ONLY the JSON array, no other text."
    )

    try:
        # Build clean env: strip CLAUDECODE to avoid nested-session detection
        vision_env = {k: v for k, v in os.environ.items() if k != 'CLAUDECODE'}
        vision_env['CLAUDE_CODE_MAX_OUTPUT_TOKENS'] = '16000'
        # Pipe prompt via stdin (Windows has ~32K char command-line limit)
        result = subprocess.run(
            [claude_path, '-p',
             '--model', 'sonnet',
             '--output-format', 'text',
             '--allowedTools', 'Read',
             '--dangerously-skip-permissions'],
            input=prompt,
            capture_output=True, text=True, encoding='utf-8',
            timeout=120, env=vision_env,
        )
        raw = result.stdout.strip()
        # Try to parse JSON from response
        idx = raw.find('[')
        if idx >= 0:
            raw = raw[idx:]
        end_idx = raw.rfind(']')
        if end_idx >= 0:
            raw = raw[:end_idx + 1]
        coords = json.loads(raw)
        return coords
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
        print(f"  Vision call failed: {e}", file=sys.stderr)
        return []


def write_annotations(doc, page_idx, findings, coordinates):
    """Write FreeText callout annotations on the PDF page."""
    page = doc[page_idx]
    rect = page.rect
    pw, ph = rect.width, rect.height

    # Build coordinate lookup
    coord_map = {}
    for c in coordinates:
        fid = c.get('finding_id', '')
        coord_map[fid] = c

    # Track text box positions to avoid overlap
    used_y_positions = []

    for i, f in enumerate(findings):
        fid = f.get('id', f.get('finding_id', f'F-{i}'))
        severity = f.get('severity', 'Minor')
        colors = SEVERITY_COLORS.get(severity, DEFAULT_COLOR)
        issue = f.get('issue', f.get('requirement', 'Review finding'))
        if len(issue) > 120:
            issue = issue[:117] + '...'
        label = f"[{fid}] {issue}"

        coord = coord_map.get(fid, {})
        x_pct = coord.get('x_pct', -1)
        y_pct = coord.get('y_pct', -1)

        if x_pct < 0 or y_pct < 0:
            # Fallback: place sticky note in right margin, stacked vertically
            note_point = fitz.Point(pw * 0.85, ph * (0.10 + i * 0.04))
            if note_point.y > ph * 0.90:
                note_point = fitz.Point(pw * 0.70, ph * (0.10 + (i - 20) * 0.04))
            annot = page.add_text_annot(note_point, label)
            annot.set_info(title="WSU Design Review", content=label)
            annot.update()
            continue

        # Target point on the drawing
        target_x = pw * (x_pct / 100.0)
        target_y = ph * (y_pct / 100.0)

        # Calculate text box position (offset from target, avoid overlap)
        box_w = min(200, pw * 0.15)
        box_h = 36

        box_x = target_x + 30
        if box_x + box_w > pw - 20:
            box_x = target_x - box_w - 30

        box_y = target_y - box_h / 2
        for used_y in used_y_positions:
            if abs(box_y - used_y) < box_h + 5:
                box_y = used_y + box_h + 5
        used_y_positions.append(box_y)

        box_y = max(10, min(box_y, ph - box_h - 10))
        box_x = max(10, min(box_x, pw - box_w - 10))

        text_rect = fitz.Rect(box_x, box_y, box_x + box_w, box_y + box_h)

        annot = page.add_freetext_annot(
            text_rect,
            label,
            fontsize=7,
            fill_color=colors['fill'],
        )
        annot.border = {"width": 1, "color": colors['border']}
        annot.set_info(title="WSU Design Review")
        annot.update()


def annotate_pdf(job_dir, claude_path='claude'):
    """Main entry point: annotate the uploaded PDF with review findings."""
    print("Phase 4: PDF Annotation")

    review_data = load_review_data(job_dir)
    pdf_path = find_uploaded_pdf(job_dir)

    if not pdf_path:
        print("  ERROR: No uploaded PDF found", file=sys.stderr)
        return False

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    output_path = os.path.join(job_dir, 'output', 'review-markup.pdf')

    # Get all non-compliant findings
    all_findings = review_data.get('findings', [])
    if not all_findings:
        all_findings = [r for r in review_data.get('requirements', [])
                        if r.get('status') not in ('C', 'NA')]
    if not all_findings:
        print("  No non-compliant findings to annotate")
        doc.save(output_path)
        doc.close()
        print(f"  Saved (unannotated): {output_path}")
        return True

    # Build sheet-to-page mapping from extracted page text
    sheet_map = build_sheet_page_map(job_dir, total_pages)
    print(f"  Sheet map: {len(sheet_map)} sheets mapped to pages")
    for sid, pidx in sorted(sheet_map.items()):
        print(f"    {sid} -> page {pidx + 1}")

    # Group findings by page
    findings_by_page = group_findings_by_page(all_findings, sheet_map)
    if not findings_by_page:
        print("  No findings could be mapped to PDF pages")
        doc.save(output_path)
        doc.close()
        print(f"  Saved (unannotated): {output_path}")
        return True

    total_findings = sum(len(v) for v in findings_by_page.values())
    print(f"  {len(findings_by_page)} pages to annotate, {total_findings} findings")

    # Render page images and dispatch vision calls
    temp_dir = tempfile.mkdtemp(prefix='wsu_vision_')
    vision_tasks = {}

    for page_idx, page_findings in findings_by_page.items():
        img_bytes = render_page_image(doc, page_idx)
        img_path = os.path.join(temp_dir, f'page_{page_idx}.png')
        with open(img_path, 'wb') as f:
            f.write(img_bytes)
        vision_tasks[page_idx] = {
            'findings': page_findings,
            'img_path': img_path,
        }

    # Run vision calls in parallel (max 4 concurrent)
    results = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        for page_idx, task in vision_tasks.items():
            future = executor.submit(
                call_vision_for_coordinates,
                task['img_path'],
                task['findings'],
                claude_path
            )
            futures[future] = page_idx

        for future in as_completed(futures):
            page_idx = futures[future]
            try:
                coords = future.result()
                results[page_idx] = coords
                print(f"  Page {page_idx + 1}: {len(coords)} coordinates returned")
            except Exception as e:
                print(f"  Page {page_idx + 1}: vision failed: {e}", file=sys.stderr)
                results[page_idx] = []

    # Write annotations
    for page_idx, task in vision_tasks.items():
        coords = results.get(page_idx, [])
        write_annotations(doc, page_idx, task['findings'], coords)

    doc.save(output_path)
    doc.close()
    print(f"  Saved: {output_path}")

    # Cleanup temp images
    for f in os.listdir(temp_dir):
        os.remove(os.path.join(temp_dir, f))
    os.rmdir(temp_dir)

    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python annotate_pdf.py <job-dir> [claude-path]", file=sys.stderr)
        sys.exit(1)
    job_dir = sys.argv[1]
    claude_path = sys.argv[2] if len(sys.argv) > 2 else 'claude'
    success = annotate_pdf(job_dir, claude_path=claude_path)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
