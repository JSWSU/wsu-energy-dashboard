"""Read the 0802 R-sheets PDF by CAD layer. Read-only."""
import re
from dataclasses import dataclass

import fitz

FT_PER_PT = 20 / 72
SHEET_SYSTEM = {"R-1": "Ground Floor", "R-2": "Mezzanine", "R-3": "Floor-01",
                "R-4": "Floor-02", "R-5": "Penthouse"}
GSF = {"Ground Floor": 17436, "Mezzanine": 4935, "Floor-01": 20679,
       "Floor-02": 21387, "Penthouse": 3368}
WALL_LAYERS = {"A-WALL", "A-WALL-CURT", "A-WALL-PRHT"}
GLAZ_LAYERS = {"A-GLAZ", "A-GLAZ-FRAM"}
SEAL_PREFIXES = ("A-WALL", "A-GLAZ", "A-DOOR", "A-COLS", "A-SPAC-PHWL", "A-FLOR-EVTR")
LABEL_RE = re.compile(r"[GM]?\d{1,3}[A-Z]{0,3}")
SCALE_WORDS = {"0", "5", "10", "20"}


class AlignmentError(RuntimeError):
    pass


@dataclass
class Sheet:
    sheet: str
    system: str
    gsf: int
    walls: list
    glazing: list
    seal: list
    labels: list
    page_size: tuple
    matrix: fitz.Matrix


def _bezier(p0, p1, p2, p3, n=10):
    out = []
    for k in range(n + 1):
        t = k / n
        a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
        out.append((a * p0.x + b * p1.x + c * p2.x + d * p3.x, a * p0.y + b * p1.y + c * p2.y + d * p3.y))
    return out


def _segments(item):
    kind = item[0]
    if kind == "l":
        return [(item[1].x, item[1].y, item[2].x, item[2].y)]
    if kind == "re":
        r = item[1]
        return [(r.x0, r.y0, r.x1, r.y0), (r.x1, r.y0, r.x1, r.y1),
                (r.x1, r.y1, r.x0, r.y1), (r.x0, r.y1, r.x0, r.y0)]
    if kind == "qu":
        q = item[1]
        pts = [q.ul, q.ur, q.lr, q.ll]
        return [(pts[i].x, pts[i].y, pts[(i + 1) % 4].x, pts[(i + 1) % 4].y) for i in range(4)]
    if kind == "c":
        pts = _bezier(*item[1:5])
        return [(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]) for i in range(len(pts) - 1)]
    return []


def _sheet_id(page):
    ids = [w[4] for w in page.get_text("words") if re.fullmatch(r"R-[1-5]", w[4])]
    if len(set(ids)) != 1:
        raise ValueError(f"page {page.number + 1}: expected one sheet number, found {ids}")
    return ids[0]


def load_sheets(pdf_path):
    doc = fitz.open(pdf_path)
    sheets = []
    for page in doc:
        sid = _sheet_id(page)
        walls, glazing, seal = [], [], []
        for dr in page.get_drawings():
            layer = dr.get("layer") or ""
            segs = [s for it in dr["items"] for s in _segments(it)]
            if layer in WALL_LAYERS:
                walls += segs
            elif layer in GLAZ_LAYERS:
                glazing += segs
            if layer.startswith(SEAL_PREFIXES):
                seal += segs
        labels = []
        for w in page.get_text("words"):
            if LABEL_RE.fullmatch(w[4]) and w[4] not in SCALE_WORDS:
                labels.append((w[4], (w[0] + w[2]) / 2, (w[1] + w[3]) / 2))
        system = SHEET_SYSTEM[sid]
        sheets.append(Sheet(sid, system, GSF[system], walls, glazing, seal, labels,
                            (page.mediabox.width, page.mediabox.height), page.rotation_matrix))
    return sorted(sheets, key=lambda s: s.sheet)


def to_feet(sheet, x, y):
    p = fitz.Point(x, y) * sheet.matrix
    return (round(p.x * FT_PER_PT, 2), round(-p.y * FT_PER_PT, 2))


def _wall_min(sheet):
    xs = [v for a, b, c, d in sheet.walls for v in (a, c)]
    ys = [v for a, b, c, d in sheet.walls for v in (b, d)]
    return min(xs), min(ys)


def check_alignment(sheets, tol_ft=2.0):
    """R-1..R-4 share one page origin; their wall extents must start at the same corner."""
    ref = next(s for s in sheets if s.sheet == "R-3")
    rx, ry = _wall_min(ref)
    bad = []
    for s in sheets:
        if s.sheet in ("R-3", "R-5"):
            continue
        x, y = _wall_min(s)
        if abs(x - rx) * FT_PER_PT > tol_ft or abs(y - ry) * FT_PER_PT > tol_ft:
            bad.append(f"{s.sheet} (offset {(x - rx) * FT_PER_PT:.1f} ft, {(y - ry) * FT_PER_PT:.1f} ft)")
    if bad:
        raise AlignmentError("sheets do not line up with R-3: " + ", ".join(bad))
