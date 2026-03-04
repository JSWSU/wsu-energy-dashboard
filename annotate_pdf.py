#!/usr/bin/env python3
"""
WSU Design Standards Review — PDF Annotation Generator

Reads review-data.json and the original uploaded PDF, then:
1. Groups non-compliant findings by drawing sheet
2. Maps sheet IDs to PDF page indices using analysis.json
3. Renders each page as a 72 DPI image
4. Sends page image + findings list to Claude vision for coordinate identification
5. Writes FreeText callout annotations via PyMuPDF
6. Saves annotated PDF as review-markup.pdf

Usage:
    python annotate_pdf.py <job-dir>

Expects:
    <job-dir>/output/review-data.json
    <job-dir>/analysis.json
    <job-dir>/upload/<original>.pdf
"""

import fitz  # PyMuPDF
import json
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed


# Severity color mapping (RGB, 0-1 scale for PyMuPDF)
SEVERITY_COLORS = {
    'Critical': {'fill': (1.0, 0.85, 0.85), 'border': (0.86, 0.15, 0.15)},  # red
    'Major':    {'fill': (1.0, 0.93, 0.82), 'border': (0.96, 0.62, 0.04)},  # orange
    'Minor':    {'fill': (1.0, 1.0, 0.85),  'border': (0.80, 0.68, 0.00)},  # yellow
}
DEFAULT_COLOR = {'fill': (0.9, 0.9, 0.9), 'border': (0.5, 0.5, 0.5)}


def load_review_data(job_dir):
    path = os.path.join(job_dir, 'output', 'review-data.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_analysis(job_dir):
    path = os.path.join(job_dir, 'analysis.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def find_uploaded_pdf(job_dir):
    upload_dir = os.path.join(job_dir, 'upload')
    if not os.path.isdir(upload_dir):
        return None
    for fname in os.listdir(upload_dir):
        if fname.lower().endswith('.pdf'):
            return os.path.join(upload_dir, fname)
    return None


def build_sheet_page_map(analysis):
    """Map sheet IDs (e.g., 'M-201') to 0-based PDF page indices."""
    sheet_map = {}
    pages = analysis.get('pages', [])
    for page_info in pages:
        page_idx = page_info.get('pageIndex', page_info.get('page', 0))
        sheet_id = page_info.get('sheetId', '')
        if sheet_id:
            sheet_map[sheet_id.upper()] = page_idx
    return sheet_map


def group_findings_by_sheet(findings):
    """Group non-compliant findings by their drawing_sheet value."""
    groups = {}
    for f in findings:
        if f.get('status') == 'C':
            continue
        sheet = (f.get('drawing_sheet') or '').strip().upper()
        if not sheet:
            continue
        groups.setdefault(sheet, []).append(f)
    return groups


def render_page_image(doc, page_idx, dpi=72):
    """Render a PDF page as PNG image bytes."""
    page = doc[page_idx]
    pix = page.get_pixmap(dpi=dpi)
    return pix.tobytes('png')


def call_vision_for_coordinates(page_image_path, findings_for_page, claude_path='claude'):
    """Send page image + findings to Claude vision, get back coordinates."""
    findings_text = "\n".join(
        f"- {f.get('finding_id', '?')}: {f.get('issue', f.get('requirement', 'Unknown issue'))}"
        for f in findings_for_page
    )

    prompt = (
        f"Read the image file at: {page_image_path}\n\n"
        "You are analyzing a construction drawing sheet. "
        "The following design review findings were identified on this sheet:\n\n"
        f"{findings_text}\n\n"
        "For each finding, identify the specific location on the drawing where the issue exists. "
        "Return a JSON array with one object per finding:\n"
        "[\n"
        '  { "finding_id": "F-001", "x_pct": 45.2, "y_pct": 62.8 }\n'
        "]\n\n"
        "x_pct and y_pct are percentages (0-100) of the page width and height respectively, "
        "measured from the TOP-LEFT corner.\n\n"
        "If you cannot identify a specific location for a finding (e.g., something is missing "
        "from the drawing entirely), set x_pct and y_pct to -1.\n\n"
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
        # Find the closing bracket
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
        fid = f.get('finding_id', f'F-{i}')
        severity = f.get('severity', 'Minor')
        colors = SEVERITY_COLORS.get(severity, DEFAULT_COLOR)
        issue = f.get('issue', f.get('requirement', 'Review finding'))
        # Truncate issue text for annotation
        if len(issue) > 120:
            issue = issue[:117] + '...'
        label = f"[{fid}] {issue}"

        coord = coord_map.get(fid, {})
        x_pct = coord.get('x_pct', -1)
        y_pct = coord.get('y_pct', -1)

        if x_pct < 0 or y_pct < 0:
            # Fallback: place sticky note in title block area (bottom-right)
            note_point = fitz.Point(pw * 0.85, ph * (0.92 - i * 0.03))
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

        # Place box to the right or left of target, shifting down to avoid overlap
        box_x = target_x + 30
        if box_x + box_w > pw - 20:
            box_x = target_x - box_w - 30

        box_y = target_y - box_h / 2
        # Shift down if overlapping with existing annotations
        for used_y in used_y_positions:
            if abs(box_y - used_y) < box_h + 5:
                box_y = used_y + box_h + 5
        used_y_positions.append(box_y)

        # Clamp to page bounds
        box_y = max(10, min(box_y, ph - box_h - 10))
        box_x = max(10, min(box_x, pw - box_w - 10))

        text_rect = fitz.Rect(box_x, box_y, box_x + box_w, box_y + box_h)

        annot = page.add_freetext_annot(
            text_rect,
            label,
            fontsize=7,
            fill_color=colors['fill'],
            border_color=colors['border'],
        )
        annot.set_info(title="WSU Design Review")
        annot.update()


def annotate_pdf(job_dir, claude_path='claude'):
    """Main entry point: annotate the uploaded PDF with review findings."""
    print("Phase 4: PDF Annotation")

    review_data = load_review_data(job_dir)
    analysis = load_analysis(job_dir)
    pdf_path = find_uploaded_pdf(job_dir)

    if not pdf_path:
        print("  ERROR: No uploaded PDF found", file=sys.stderr)
        return False

    # Get all findings (non-compliant only)
    all_findings = review_data.get('findings', [])
    if not all_findings:
        # Try requirements array if findings is empty
        all_findings = [r for r in review_data.get('requirements', [])
                        if r.get('status') not in ('C', 'NA')]
    if not all_findings:
        print("  No non-compliant findings to annotate")
        # Still create a copy as review-markup.pdf
        doc = fitz.open(pdf_path)
        output_path = os.path.join(job_dir, 'output', 'review-markup.pdf')
        doc.save(output_path)
        doc.close()
        print(f"  Saved (unannotated): {output_path}")
        return True

    sheet_map = build_sheet_page_map(analysis)
    findings_by_sheet = group_findings_by_sheet(all_findings)

    doc = fitz.open(pdf_path)
    output_path = os.path.join(job_dir, 'output', 'review-markup.pdf')

    # Render page images and dispatch vision calls
    vision_tasks = {}
    temp_dir = tempfile.mkdtemp(prefix='wsu_vision_')

    for sheet_id, sheet_findings in findings_by_sheet.items():
        page_idx = sheet_map.get(sheet_id)
        if page_idx is None:
            # Try fuzzy match (strip leading zeros, case insensitive)
            for map_id, map_idx in sheet_map.items():
                if map_id.replace('-0', '-') == sheet_id.replace('-0', '-'):
                    page_idx = map_idx
                    break
        if page_idx is None or page_idx >= len(doc):
            print(f"  WARNING: Sheet {sheet_id} not found in PDF, skipping {len(sheet_findings)} findings")
            continue

        # Render page image
        img_bytes = render_page_image(doc, page_idx)
        img_path = os.path.join(temp_dir, f'page_{page_idx}.png')
        with open(img_path, 'wb') as f:
            f.write(img_bytes)

        vision_tasks[sheet_id] = {
            'page_idx': page_idx,
            'findings': sheet_findings,
            'img_path': img_path,
        }

    print(f"  {len(vision_tasks)} pages to annotate, {sum(len(v['findings']) for v in vision_tasks.values())} findings")

    # Run vision calls in parallel (max 4 concurrent to avoid rate limits)
    results = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        for sheet_id, task in vision_tasks.items():
            future = executor.submit(
                call_vision_for_coordinates,
                task['img_path'],
                task['findings'],
                claude_path
            )
            futures[future] = sheet_id

        for future in as_completed(futures):
            sheet_id = futures[future]
            try:
                coords = future.result()
                results[sheet_id] = coords
                print(f"  {sheet_id}: {len(coords)} coordinates returned")
            except Exception as e:
                print(f"  {sheet_id}: vision failed: {e}", file=sys.stderr)
                results[sheet_id] = []

    # Write annotations
    for sheet_id, task in vision_tasks.items():
        coords = results.get(sheet_id, [])
        write_annotations(doc, task['page_idx'], task['findings'], coords)

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
        print("Usage: python annotate_pdf.py <job-dir>", file=sys.stderr)
        sys.exit(1)
    job_dir = sys.argv[1]
    success = annotate_pdf(job_dir)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
