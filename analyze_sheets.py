#!/usr/bin/env python3
"""Analyze extracted PDF pages to classify construction disciplines.

Reads extracted page text files (from extract_pdf.py) and detects which
construction disciplines are present by looking for:
  - Sheet designations (e.g., A1.01 = architectural, E-1 = electrical)
  - Keywords (e.g., "panel schedule" = electrical, "plumbing" = plumbing)

Maps detected content to the 8 discipline groups and their CSI divisions,
then outputs analysis.json.

Usage: python analyze_sheets.py <pages_dir> <output_json>
"""

import json
import os
import re
import sys
from collections import defaultdict

# ---------------------------------------------------------------------------
# Discipline group definitions (mirrors review-server.pl @ALL_GROUPS)
# ---------------------------------------------------------------------------
DISCIPLINE_GROUPS = {
    'arch-structure': {
        'name': 'Architectural — Structure & Envelope',
        'divisions': ['02', '03', '04', '05', '07', '08'],
    },
    'arch-finishes': {
        'name': 'Architectural — Finishes & Equipment',
        'divisions': ['09', '10', '11', '12', '13', '14'],
    },
    'fire-protection': {
        'name': 'Fire Protection and Security',
        'divisions': ['21', '28'],
    },
    'plumbing': {
        'name': 'Plumbing',
        'divisions': ['22'],
    },
    'hvac-controls': {
        'name': 'HVAC and Building Automation',
        'divisions': ['23', '25'],
    },
    'electrical': {
        'name': 'Electrical',
        'divisions': ['26'],
    },
    'communications': {
        'name': 'Communications and Technology',
        'divisions': ['27'],
    },
    'civil-site': {
        'name': 'Civil, Site, and Utilities',
        'divisions': ['31', '32', '33', '40'],
    },
}

# ---------------------------------------------------------------------------
# Sheet designation patterns
# ---------------------------------------------------------------------------
# Maps sheet prefix letter(s) to a category.
# Common AEC sheet naming conventions:
#   A  = Architectural
#   S  = Structural
#   C  = Civil
#   L  = Landscape
#   M  = Mechanical / HVAC
#   P  = Plumbing
#   FP = Fire Protection
#   FA = Fire Alarm
#   E  = Electrical
#   T  = Telecom / Technology / Communications
#   G  = General
#   D  = Demolition
#   Q  = Equipment / Laboratory (specialty)
#   I  = Interiors
#   K  = Dietary / Kitchen equipment
#   R  = Resource / special
#   W  = Water (civil)
#
# Format in real data: PREFIX-NNN (e.g., A-001, FP-101, M-000)
# Also common: PREFIX + digits (A1.01, A101), PREFIX + dot + digits

# Refined pattern for extracting sheet IDs from title blocks and sheet indexes.
# This targets lines where the sheet ID appears as a standalone label
# (e.g., "A-001", "FP-101", "M-000", "E-501"), not embedded in dimensions
# or manufacturer model numbers (e.g., K-2202 Kohler fixture).
# Only matches known AEC sheet prefixes.
# Excludes K (Kohler model numbers), R (too broad).
SHEET_ID_RE = re.compile(
    r'\b(FP|FA|FS|QL|A|S|C|L|M|P|E|T|G|D|Q|I|W)-(\d{3,4})\b'
)

# ---------------------------------------------------------------------------
# Keyword patterns for discipline detection
# ---------------------------------------------------------------------------
KEYWORD_PATTERNS = [
    # (compiled regex, category, weight)
    # --- Architectural ---
    (re.compile(r'\bfloor\s+plan\b', re.IGNORECASE),              'architectural',     1),
    (re.compile(r'\bbuilding\s+elevation', re.IGNORECASE),         'architectural',     2),
    (re.compile(r'\bbuilding\s+section', re.IGNORECASE),           'architectural',     2),
    (re.compile(r'\bwall\s+section', re.IGNORECASE),               'architectural',     2),
    (re.compile(r'\breflected\s+ceiling', re.IGNORECASE),          'architectural',     2),
    (re.compile(r'\bfinish\s+plan\b', re.IGNORECASE),              'architectural',     2),
    (re.compile(r'\bfinish\s+schedule\b', re.IGNORECASE),          'arch-finishes',     2),
    (re.compile(r'\bdoor\s+schedule\b', re.IGNORECASE),            'arch-finishes',     2),
    (re.compile(r'\bpartition\s+type', re.IGNORECASE),             'arch-finishes',     2),
    (re.compile(r'\binterior\s+elevation', re.IGNORECASE),         'arch-finishes',     2),
    (re.compile(r'\broof\s+plan\b', re.IGNORECASE),                'architectural',     1),

    # --- Structural ---
    (re.compile(r'\bfoundation\s+plan\b', re.IGNORECASE),         'structural',        2),
    (re.compile(r'\bframing\s+plan\b', re.IGNORECASE),            'structural',        2),
    (re.compile(r'\bframing\s+detail', re.IGNORECASE),            'structural',        2),
    (re.compile(r'\bfoundation\s+detail', re.IGNORECASE),         'structural',        2),
    (re.compile(r'\bstructural\s+general\s+note', re.IGNORECASE), 'structural',        2),
    (re.compile(r'\bshear\s+wall\b', re.IGNORECASE),              'structural',        1),
    (re.compile(r'\bsnow\s+drift\b', re.IGNORECASE),              'structural',        2),
    (re.compile(r'\bspecial\s+inspection', re.IGNORECASE),         'structural',        2),

    # --- Civil ---
    (re.compile(r'\bcivil\s+site\b', re.IGNORECASE),              'civil',             2),
    (re.compile(r'\bgrading\s+plan\b', re.IGNORECASE),            'civil',             2),
    (re.compile(r'\bstormwater\b', re.IGNORECASE),                 'civil',             2),
    (re.compile(r'\berosion\s+control\b', re.IGNORECASE),          'civil',             2),
    (re.compile(r'\bsite\s+utility\b', re.IGNORECASE),             'civil',             2),
    (re.compile(r'\bsite\s+plan\b', re.IGNORECASE),                'civil',             1),
    (re.compile(r'\bcontour\s+plan\b', re.IGNORECASE),             'civil',             2),
    (re.compile(r'\bdemolition\s+plan\b', re.IGNORECASE),          'civil',             1),

    # --- Landscape ---
    (re.compile(r'\blandscape\s+plan\b', re.IGNORECASE),          'landscape',         2),
    (re.compile(r'\blandscape\s+site\b', re.IGNORECASE),          'landscape',         2),
    (re.compile(r'\bplanting\s+plan\b', re.IGNORECASE),           'landscape',         2),
    (re.compile(r'\birrigation\s+plan\b', re.IGNORECASE),         'landscape',         2),

    # --- Mechanical / HVAC ---
    (re.compile(r'\bhvac\b', re.IGNORECASE),                       'mechanical',        2),
    (re.compile(r'\bmechanical\s+plan\b', re.IGNORECASE),          'mechanical',        2),
    (re.compile(r'\bmechanical\s+schedule', re.IGNORECASE),        'mechanical',        2),
    (re.compile(r'\bduct\s+plan\b', re.IGNORECASE),                'mechanical',        2),
    (re.compile(r'\bpiping\s+plan\b', re.IGNORECASE),              'mechanical',        2),
    (re.compile(r'\bair\s+handling\b', re.IGNORECASE),             'mechanical',        2),
    (re.compile(r'\bhvac\s+schedule', re.IGNORECASE),              'mechanical',        2),
    (re.compile(r'\bhvac\s+detail', re.IGNORECASE),                'mechanical',        2),
    (re.compile(r'\bhvac\s+floor\s+plan', re.IGNORECASE),          'mechanical',        3),
    (re.compile(r'\bbuilding\s+automation\b', re.IGNORECASE),      'mechanical',        2),
    (re.compile(r'\bcontrol\s+sequence', re.IGNORECASE),           'mechanical',        2),
    (re.compile(r'\bBAS\b'),                                        'mechanical',        2),

    # --- Plumbing ---
    (re.compile(r'\bplumbing\s+plan\b', re.IGNORECASE),           'plumbing',          2),
    (re.compile(r'\bplumbing\s+detail', re.IGNORECASE),            'plumbing',          2),
    (re.compile(r'\bplumbing\s+schedule', re.IGNORECASE),          'plumbing',          2),
    (re.compile(r'\bplumbing\s+floor\b', re.IGNORECASE),           'plumbing',          3),
    (re.compile(r'\bplumbing\s+fixture', re.IGNORECASE),           'plumbing',          3),
    (re.compile(r'\bplumbing\s+underslab\b', re.IGNORECASE),       'plumbing',          3),
    (re.compile(r'\bplumbing\s+legend\b', re.IGNORECASE),          'plumbing',          2),
    (re.compile(r'\bdomestic\s+water\b', re.IGNORECASE),           'plumbing',          2),
    (re.compile(r'\bsanitary\s+sewer\b', re.IGNORECASE),           'plumbing',          2),
    (re.compile(r'\bwater\s+heater\b', re.IGNORECASE),             'plumbing',          1),
    (re.compile(r'\broof\s+drain\b', re.IGNORECASE),               'plumbing',          1),
    (re.compile(r'\bfloor\s+drain\b', re.IGNORECASE),              'plumbing',          1),

    # --- Fire Protection ---
    (re.compile(r'\bfire\s+protection\b', re.IGNORECASE),          'fire-protection',   2),
    (re.compile(r'\bfire\s+suppression\b', re.IGNORECASE),         'fire-protection',   2),
    (re.compile(r'\bfire\s+alarm\b', re.IGNORECASE),               'fire-alarm',        2),
    (re.compile(r'\bsprinkler\s+plan\b', re.IGNORECASE),           'fire-protection',   2),
    (re.compile(r'\bsprinkler\s+system\b', re.IGNORECASE),         'fire-protection',   2),
    (re.compile(r'\bfire\s+protection\s+plan\b', re.IGNORECASE),   'fire-protection',   3),
    (re.compile(r'\bfire\s+protection\s+legend\b', re.IGNORECASE), 'fire-protection',   3),

    # --- Electrical ---
    (re.compile(r'\belectrical\s+plan\b', re.IGNORECASE),          'electrical',        2),
    (re.compile(r'\belectrical\s+power\b', re.IGNORECASE),         'electrical',        2),
    (re.compile(r'\belectrical\s+lighting\b', re.IGNORECASE),      'electrical',        2),
    (re.compile(r'\belectrical\s+detail', re.IGNORECASE),          'electrical',        2),
    (re.compile(r'\belectrical\s+legend\b', re.IGNORECASE),        'electrical',        2),
    (re.compile(r'\belectrical\s+one-line\b', re.IGNORECASE),      'electrical',        3),
    (re.compile(r'\bone-line\s+diagram\b', re.IGNORECASE),         'electrical',        2),
    (re.compile(r'\bpanel\s*board\s+schedule\b', re.IGNORECASE),   'electrical',        3),
    (re.compile(r'\bpanel\s+schedule\b', re.IGNORECASE),           'electrical',        3),
    (re.compile(r'\blighting\s+fixture\s+schedule\b', re.IGNORECASE), 'electrical',     3),
    (re.compile(r'\blighting\s+plan\b', re.IGNORECASE),            'electrical',        2),
    (re.compile(r'\bgrounding\b', re.IGNORECASE),                   'electrical',        1),
    (re.compile(r'\bswitchboard\b', re.IGNORECASE),                 'electrical',        2),
    (re.compile(r'\btransformer\b', re.IGNORECASE),                 'electrical',        1),

    # --- Communications / Telecom ---
    (re.compile(r'\btelecommunication', re.IGNORECASE),            'telecom',           2),
    (re.compile(r'\bdata\s+infrastructure\b', re.IGNORECASE),      'telecom',           2),
    (re.compile(r'\bIDF\b'),                                        'telecom',           1),
    (re.compile(r'\bMDF\b'),                                        'telecom',           1),
    (re.compile(r'\bfiber\s+optic\b', re.IGNORECASE),              'telecom',           2),
    (re.compile(r'\bnetwork\s+rack\b', re.IGNORECASE),             'telecom',           2),
    (re.compile(r'\baudio[\s-]?visual\b', re.IGNORECASE),          'telecom',           2),

    # --- General / Cover ---
    (re.compile(r'\bsheet\s+index\b', re.IGNORECASE),             'general',           1),
    (re.compile(r'\bregulatory.*code\s+summary\b', re.IGNORECASE), 'general',          2),
    (re.compile(r'\blife\s+safety\s+plan\b', re.IGNORECASE),       'general',          2),
    (re.compile(r'\bcode\s+summary\b', re.IGNORECASE),             'general',          1),
]

# ---------------------------------------------------------------------------
# Category -> discipline group mapping
# ---------------------------------------------------------------------------
CATEGORY_TO_DISCIPLINES = {
    'architectural':    ['arch-structure', 'arch-finishes'],
    'structural':       ['arch-structure'],
    'civil':            ['civil-site'],
    'landscape':        ['civil-site'],
    'civil-water':      ['civil-site'],
    'demolition':       ['civil-site', 'arch-structure'],
    'mechanical':       ['hvac-controls'],
    'plumbing':         ['plumbing'],
    'fire-protection':  ['fire-protection'],
    'fire-alarm':       ['fire-protection'],
    'fire-suppression': ['fire-protection'],
    'electrical':       ['electrical'],
    'telecom':          ['communications'],
    'general':          [],  # general sheets don't map to a specific discipline
    'equipment':        ['arch-finishes'],
    'interiors':        ['arch-finishes'],
    'kitchen':          ['arch-finishes'],
    'resource':         [],
    'arch-finishes':    ['arch-finishes'],
}

# Category -> CSI divisions mapping, keyed by (category, discipline) for precision.
# When a category maps to multiple disciplines, each discipline gets only its
# own relevant divisions (e.g., 'architectural' -> arch-structure gets 02-08,
# arch-finishes gets 09-14).
CATEGORY_TO_DIVISIONS = {
    'architectural':    ['02', '03', '04', '05', '07', '08', '09', '10', '11', '12', '13', '14'],
    'structural':       ['03', '04', '05'],
    'civil':            ['31', '32', '33'],
    'landscape':        ['32'],
    'civil-water':      ['33'],
    'demolition':       ['02'],
    'mechanical':       ['23', '25'],
    'plumbing':         ['22'],
    'fire-protection':  ['21'],
    'fire-alarm':       ['28'],
    'fire-suppression': ['21'],
    'electrical':       ['26'],
    'telecom':          ['27'],
    'general':          [],
    'equipment':        ['11', '12', '13', '14'],
    'interiors':        ['09', '10', '12'],
    'kitchen':          ['11'],
    'resource':         [],
    'arch-finishes':    ['09', '10', '11', '12', '13', '14'],
}

def get_divisions_for_discipline(category, discipline_key):
    """Return only the CSI divisions relevant to a specific discipline group.

    When a category maps to multiple discipline groups (e.g., 'architectural'
    maps to both arch-structure and arch-finishes), each discipline should only
    get the divisions that belong to it, not all divisions from the category.
    """
    cat_divs = set(CATEGORY_TO_DIVISIONS.get(category, []))
    disc_divs = set(DISCIPLINE_GROUPS.get(discipline_key, {}).get('divisions', []))
    # Intersect: only divisions that belong to BOTH the category and the discipline
    result = cat_divs & disc_divs
    return result if result else cat_divs  # fallback to all category divs if no overlap


# ---------------------------------------------------------------------------
# Analysis functions
# ---------------------------------------------------------------------------

def read_manifest(pages_dir):
    """Read manifest.txt and return total page count."""
    manifest_path = os.path.join(pages_dir, 'manifest.txt')
    if not os.path.isfile(manifest_path):
        print(f"WARNING: No manifest.txt found in {pages_dir}", file=sys.stderr)
        return 0
    with open(manifest_path, 'r', encoding='utf-8') as f:
        first_line = f.readline().strip()
    m = re.match(r'Pages:\s*(\d+)', first_line)
    return int(m.group(1)) if m else 0


def extract_sheet_ids(text):
    """Extract sheet designation IDs from text.

    Returns a list of (sheet_id, category) tuples.
    """
    results = []
    for match in SHEET_ID_RE.finditer(text):
        prefix = match.group(1).upper()
        number = match.group(2)
        sheet_id = f"{prefix}-{number}"
        category = prefix_to_category(prefix)
        if category:
            results.append((sheet_id, category))
    return results


def prefix_to_category(prefix):
    """Map a sheet prefix to a category name."""
    mapping = {
        'A': 'architectural',
        'S': 'structural',
        'C': 'civil',
        'L': 'landscape',
        'M': 'mechanical',
        'P': 'plumbing',
        'E': 'electrical',
        'T': 'telecom',
        'G': 'general',
        'D': 'demolition',
        'Q': 'equipment',
        'I': 'interiors',
        'K': 'kitchen',
        'R': 'resource',
        'W': 'civil-water',
        'FP': 'fire-protection',
        'FA': 'fire-alarm',
        'FS': 'fire-suppression',
    }
    # Try multi-letter prefix first, then single
    if prefix in mapping:
        return mapping[prefix]
    if len(prefix) > 1 and prefix[0] in mapping:
        return mapping[prefix[0]]
    return None


def detect_keywords(text):
    """Detect discipline keywords in text.

    Returns list of (category, weight) tuples.
    """
    results = []
    for pattern, category, weight in KEYWORD_PATTERNS:
        if pattern.search(text):
            results.append((category, weight))
    return results


def analyze_page(page_path):
    """Analyze a single page file.

    Returns dict with:
      - sheet_ids: list of (sheet_id, category)
      - categories: dict of category -> total weight
      - keywords_found: list of category names
    """
    try:
        with open(page_path, 'r', encoding='utf-8') as f:
            text = f.read()
    except (OSError, UnicodeDecodeError) as e:
        print(f"WARNING: Cannot read {page_path}: {e}", file=sys.stderr)
        return {'sheet_ids': [], 'categories': {}, 'keywords_found': []}

    categories = defaultdict(int)
    all_sheet_ids = []

    # 1. Extract sheet IDs (precise: PREFIX-NNN format)
    sheet_ids = extract_sheet_ids(text)
    for sid, cat in sheet_ids:
        categories[cat] += 3  # high weight for explicit sheet IDs
        all_sheet_ids.append((sid, cat))

    # 2. Detect keywords
    keywords = detect_keywords(text)
    keywords_found = []
    for cat, weight in keywords:
        categories[cat] += weight
        keywords_found.append(cat)

    return {
        'sheet_ids': all_sheet_ids,
        'categories': dict(categories),
        'keywords_found': keywords_found,
    }


def analyze_pages(pages_dir):
    """Analyze all pages in the directory.

    Returns the full analysis result dict.
    """
    total_pages = read_manifest(pages_dir)
    if total_pages == 0:
        # Try counting page files directly
        page_files = sorted(
            f for f in os.listdir(pages_dir)
            if f.startswith('page-') and f.endswith('.txt')
        )
        total_pages = len(page_files)
    else:
        page_files = [f"page-{i+1:04d}.txt" for i in range(total_pages)]

    # Per-page analysis
    page_details = {}
    all_categories = defaultdict(int)       # category -> total weight
    category_pages = defaultdict(set)       # category -> set of page numbers
    all_sheet_ids = defaultdict(set)         # category -> set of sheet IDs
    discipline_pages = defaultdict(set)     # discipline -> set of page numbers
    discipline_sheet_ids = defaultdict(set) # discipline -> set of sheet IDs
    discipline_divisions = defaultdict(set) # discipline -> set of CSI divisions
    unclassified = []

    for page_file in page_files:
        page_path = os.path.join(pages_dir, page_file)
        if not os.path.isfile(page_path):
            continue

        # Extract page number from filename
        m = re.match(r'page-(\d+)\.txt', page_file)
        if not m:
            continue
        page_num = int(m.group(1))

        result = analyze_page(page_path)

        # Collect sheet IDs
        for sid, cat in result['sheet_ids']:
            all_sheet_ids[cat].add(sid)

        # Aggregate category weights
        page_classified = False
        page_cats = set()
        for cat, weight in result['categories'].items():
            all_categories[cat] += weight
            category_pages[cat].add(page_num)

            # Map to disciplines
            disc_keys = CATEGORY_TO_DISCIPLINES.get(cat, [])
            for dk in disc_keys:
                discipline_pages[dk].add(page_num)
                # Use per-discipline division filtering to avoid
                # e.g., arch-structure getting finishes divisions
                divs = get_divisions_for_discipline(cat, dk)
                discipline_divisions[dk].update(divs)
                for sid, scat in result['sheet_ids']:
                    if scat == cat:
                        discipline_sheet_ids[dk].add(sid)
                page_classified = True
            page_cats.add(cat)

        if not page_classified and result['categories']:
            # Has some categories but none map to disciplines (e.g., "general")
            pass
        elif not result['categories']:
            unclassified.append(page_num)

        # Store per-page detail
        page_detail = {
            'categories': list(page_cats),
            'sheet_ids': [sid for sid, _ in result['sheet_ids']],
        }
        if page_detail['categories'] or page_detail['sheet_ids']:
            page_details[str(page_num)] = page_detail

    # Build recommended_disciplines output
    recommended_disciplines = {}
    for dk, group_info in DISCIPLINE_GROUPS.items():
        if dk not in discipline_pages:
            continue
        pages_list = sorted(discipline_pages[dk])
        divs_list = sorted(discipline_divisions.get(dk, set()))
        sids_list = sorted(discipline_sheet_ids.get(dk, set()))
        recommended_disciplines[dk] = {
            'name': group_info['name'],
            'pages': pages_list,
            'page_count': len(pages_list),
            'divisions': divs_list,
            'sheet_ids': sids_list,
        }

    # Collect all recommended divisions
    all_recommended_divs = set()
    for dk in recommended_disciplines:
        all_recommended_divs.update(recommended_disciplines[dk]['divisions'])

    # Compute confidence
    classified_pages = total_pages - len(unclassified)
    if total_pages > 0:
        confidence = round(classified_pages / total_pages, 3)
    else:
        confidence = 0.0

    # Build detected_categories summary
    detected_categories_out = {}
    for cat in sorted(all_categories.keys()):
        detected_categories_out[cat] = {
            'weight': all_categories[cat],
            'pages': sorted(category_pages[cat]),
            'page_count': len(category_pages[cat]),
            'sheet_ids': sorted(all_sheet_ids.get(cat, set())),
        }

    analysis = {
        'total_pages': total_pages,
        'confidence': confidence,
        'detected_categories': detected_categories_out,
        'recommended_disciplines': recommended_disciplines,
        'recommended_divisions': sorted(all_recommended_divs),
        'unclassified_pages': unclassified,
        'page_details': page_details,
    }

    return analysis


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <pages_dir> <output_json>", file=sys.stderr)
        sys.exit(1)

    pages_dir = sys.argv[1]
    output_json = sys.argv[2]

    if not os.path.isdir(pages_dir):
        print(f"ERROR: Pages directory not found: {pages_dir}", file=sys.stderr)
        sys.exit(1)

    analysis = analyze_pages(pages_dir)

    # Write output
    os.makedirs(os.path.dirname(os.path.abspath(output_json)), exist_ok=True)
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)

    # Print summary
    n_disc = len(analysis['recommended_disciplines'])
    n_divs = len(analysis['recommended_divisions'])
    n_unclass = len(analysis['unclassified_pages'])
    total = analysis['total_pages']
    conf = analysis['confidence']

    disc_names = [
        analysis['recommended_disciplines'][dk]['name']
        for dk in sorted(analysis['recommended_disciplines'].keys())
    ]

    print(f"Sheet analysis: {total} pages, {n_disc} disciplines detected, "
          f"{n_divs} CSI divisions, {n_unclass} unclassified, "
          f"confidence={conf:.1%}")
    if disc_names:
        for name in disc_names:
            print(f"  - {name}")

    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
