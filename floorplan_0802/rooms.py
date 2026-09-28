"""Find room shapes on one sheet: fill between seal lines, split shared areas by walking distance."""
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from skimage import measure

from .extract import FT_PER_PT


def _rasterize(segments, size_pt, s, line_px=2, dilate=2):
    w, h = int(size_pt[0] * s) + 2, int(size_pt[1] * s) + 2
    im = Image.new("L", (w, h), 0)
    g = ImageDraw.Draw(im)
    for a, b, c, d in segments:
        g.line([(a * s, b * s), (c * s, d * s)], fill=255, width=line_px)
    wall = np.array(im) > 0
    return ndimage.binary_dilation(wall, iterations=dilate) if dilate else wall


def _snap(lab, r, c, radius=15):
    h, w = lab.shape
    if 0 <= r < h and 0 <= c < w and lab[r, c]:
        return r, c
    r0, c0 = max(r - radius, 0), max(c - radius, 0)
    win = lab[r0:r + radius + 1, c0:c + radius + 1]
    ys, xs = np.nonzero(win)
    if not len(ys):
        return None
    k = np.argmin((ys + r0 - r) ** 2 + (xs + c0 - c) ** 2)
    return ys[k] + r0, xs[k] + c0


def geodesic_split(mask, seeds):
    h, w = mask.shape
    owner = np.full(mask.shape, -1, np.int32)
    front = np.array(seeds, dtype=np.int64).reshape(-1, 2)
    for k, (r, c) in enumerate(seeds):
        owner[r, c] = k
    steps = np.array([[1, 0], [-1, 0], [0, 1], [0, -1]])
    while len(front):
        nb = (front[:, None, :] + steps[None, :, :]).reshape(-1, 2)
        src = np.repeat(front, 4, axis=0)
        ok = (nb[:, 0] >= 0) & (nb[:, 0] < h) & (nb[:, 1] >= 0) & (nb[:, 1] < w)
        nb, src = nb[ok], src[ok]
        free = mask[nb[:, 0], nb[:, 1]] & (owner[nb[:, 0], nb[:, 1]] < 0)
        nb, src = nb[free], src[free]
        _, first = np.unique(nb[:, 0] * w + nb[:, 1], return_index=True)
        nb, src = nb[first], src[first]
        owner[nb[:, 0], nb[:, 1]] = owner[src[:, 0], src[:, 1]]
        front = nb
    return owner


def _trace(mask, off, s):
    padded = np.pad(mask, 1).astype(np.uint8)
    contours = measure.find_contours(padded, 0.5)
    if not contours:
        return None, 0.0
    ring = max(contours, key=len)
    ring = measure.approximate_polygon(ring, tolerance=0.5 / FT_PER_PT * s)
    pts = [((col - 1 + off[1]) / s, (row - 1 + off[0]) / s) for row, col in ring]
    area_px = mask.sum()
    return pts, float(area_px / (s * s) * FT_PER_PT ** 2)


def find_rooms(sheet, s=2):
    wall = _rasterize(sheet.seal, sheet.page_size, s)
    lab, _ = ndimage.label(~wall)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])).tolist())
    seeds = {}
    for name, x, y in sheet.labels:
        hit = _snap(lab, int(round(y * s)), int(round(x * s)))
        if hit is None:
            continue
        region = int(lab[hit])
        if region == 0 or region in border:
            continue
        seeds.setdefault(region, []).append((name, hit[0], hit[1]))
    objs = ndimage.find_objects(lab)
    out = {}
    for region, lst in seeds.items():
        sl = objs[region - 1]
        sub = lab[sl] == region
        off = (sl[0].start, sl[1].start)
        owner = geodesic_split(sub, [(r - off[0], c - off[1]) for _, r, c in lst])
        masks = {}
        for k, (name, _, _) in enumerate(lst):
            masks[name] = masks.get(name, np.zeros_like(sub)) | (owner == k)
        for name, m in masks.items():
            poly, area = _trace(m, off, s)
            if poly and (name not in out or area > out[name]["area_ft2"]):
                out[name] = {"poly_pt": poly, "area_ft2": area}
    return out


def _regions(sheet, s):
    wall = _rasterize(sheet.seal, sheet.page_size, s)
    lab, _ = ndimage.label(~wall)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])).tolist())
    return wall, lab, border


def _outline(mask, s, min_ft2):
    comps, n = ndimage.label(mask)
    out = []
    for k, sl in enumerate(ndimage.find_objects(comps), start=1):
        m = comps[sl] == k
        poly, area = _trace(m, (sl[0].start, sl[1].start), s)
        if poly and area >= min_ft2:
            out.append(poly)
    return out


def floor_polygons(sheet, s=2, wall_px=6, min_ft2=50):
    """Floor outline(s) in page pt: every enclosed area of the sheet, minus areas marked OPEN TO BELOW."""
    wall, lab, border = _regions(sheet, s)
    open_regions = set()
    for x, y in sheet.open_marks:
        hit = _snap(lab, int(round(y * s)), int(round(x * s)))
        if hit is not None:
            open_regions.add(int(lab[hit]))
    # an area holding an OPEN TO BELOW note is open, even if it also touches rooms (conservative:
    # rooms that share it are left out of the floor rather than drawing open area as floor)
    inside = (lab > 0) & ~np.isin(lab, list(border | open_regions))
    mask = ndimage.binary_fill_holes(ndimage.binary_dilation(inside, iterations=wall_px) & (inside | wall))
    return _outline(mask, s, min_ft2)


def enclosure_polygon(sheet, label, s=2, wall_px=6):
    """Outline in page pt of the enclosed area that holds one label, walls included."""
    wall, lab, border = _regions(sheet, s)
    pos = next(((x, y) for n, x, y in sheet.labels if n == label), None)
    if pos is None:
        return None
    hit = _snap(lab, int(round(pos[1] * s)), int(round(pos[0] * s)))
    if hit is None or int(lab[hit]) in border:
        return None
    region = lab == lab[hit]
    mask = ndimage.binary_fill_holes(ndimage.binary_dilation(region, iterations=wall_px) & (region | wall))
    polys = _outline(mask, s, 0)
    return max(polys, key=len) if polys else None
