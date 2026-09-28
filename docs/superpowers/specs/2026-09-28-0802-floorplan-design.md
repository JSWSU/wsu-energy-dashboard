# 0802 Floor Plan Explorer: Design

Date: 09/28/2026
Page: `seh-energy.html` (Schweitzer Engineering Hall, building 0802), tab "Explore the Building"
Status: approved in conversation 09/28/2026; this spec awaits review.

## Goal

Replace the schematic tile grid in the 3D view with the real floor plans of building 0802. Each SkySpark zone colors its real room. A student finds a classroom on the plan and sees its temperature, comfort, CO2 and airflow there.

Success test: Room 105 appears on the east side of the First Floor, as on sheet R-3, and takes its color from boxes FPB.L1-16A and FPB.L1-16B.

## Decisions (from the owner)

1. Public, simplified plan (option 1). The public page shows walls, glazing and the rooms that have a SkySpark zone. It shows no doors, door swings, stairs, fixtures or furniture. It shows no labels for electrical, mechanical or stair rooms.
2. The floor plan is used in the Explore the Building tab.
3. Square footage: the R-sheet gross square feet (Facilities space record). Building total 67,805 GSF; per floor: Ground 17,436, Mezzanine 4,935, First 20,679, Second 21,387, Mechanical Penthouse 3,368. The header and the energy-per-square-foot figure use 67,805.

## Source

- R-sheets PDF, 5 pages (R-1 Ground, R-2 Mezzanine, R-3 First, R-4 Second, R-5 Mechanical Penthouse), plotted 11/20/2025 and 11/21/2025 from AutoCAD Map 3D, scale 1" = 20'.
- The PDF keeps the CAD layers (optional content groups). Pages carry a /Rotate of 270; drawing and text coordinates share the unrotated page space (792 x 1224 pt).
- 1 pt on the sheet = 20/72 ft.
- The PDF lives in `C:\Users\john.slagboom\Desktop\Git\private\0802_r-sheets.pdf`. The `private/` folder is gitignored. The PDF is never pushed.

## Component 1: build script `build_0802_floorplan.py`

Runs by hand when the R-sheets change. Not part of the weekly job.

Input: the PDF path (default above) and `data/0802/points.json` (for the zone list).

Steps per page:

1. Read drawings with PyMuPDF. Keep only allow-listed layers:
   - Walls for display: `A-WALL`, `A-WALL-CURT`, `A-WALL-PRHT`, `A-GLAZ`, `A-GLAZ-FRAM`.
   - Extra lines used only to seal rooms for the fill (never written to output): `A-DOOR`, `A-DOOR-FRAM`, `A-DOOR-SWNG`, `A-SPAC-PHWL`, `A-FLOR-EVTR`, `A-COLS`.
2. Rasterize the seal lines at 4 px per pt; dilate 3 px. Label the open regions (SciPy).
3. Read room labels: words that match `[GM]?\d{1,3}[A-Z]{0,3}`, excluding the scale bar numbers.
4. For each label, find its region. A region that touches the page border is outside and is rejected.
5. When several labels share one region, split the region by walking distance: a multi-source breadth-first search from each label point through open pixels. Each pixel goes to the nearest label.
6. Trace each room's pixel set to a polygon (scikit-image `find_contours`, then `approximate_polygon` at 0.5 ft tolerance). Keep the largest outer ring.
7. Convert all coordinates to feet. Rotate so plan north is up, as printed on the sheet.

Alignment across floors:

- Compute the bounding box of `A-WALL` lines per page.
- Use the First Floor (R-3) as the reference origin. Offset each other floor by its sheet position. Before any offset, check that the page-space position of the shared exterior walls on R-1, R-3 and R-4 agree within 2 ft. If they do not, stop with an error that names the pages. Do not guess an offset.

Zone to room matching:

1. Room key from the equipment alias (`basNameNew`) or name, pattern `RM([GM]?\d+[A-Z]*)`.
2. Exact label match, then the override table below.
3. Anything left is an unlocated zone, listed in the report and placed in the floor strip.

Override table (starting set; the build report confirms each one):

| SkySpark | Room label | Reason |
|---|---|---|
| alias `FPB.RMG05` (FPB.G1A, G1B, G1C) | G5 | leading zero; confirmed |
| alias `FPB.STAIRS` (FPB.G2) | none, floor strip | stairs are not shown |

Candidates that are NOT applied until the owner confirms them (they stay in the floor strip and appear in the build report):

- alias `FPB.CORR` (FPB.G4): a ground floor corridor, label unknown.
- `FPB.L1-4` alias `FPB.RM126`: suite 126A to 126E or corridor 126X, unknown.

Output `data/0802/floorplan.json`:

```
{
  "generated": "...", "source": "R-sheets plotted 11/20/2025 and 11/21/2025",
  "units": "ft",
  "floors": [
    { "system": "Ground Floor", "sheet": "R-1", "gsf": 17436,
      "walls": [[x1,y1,x2,y2], ...],
      "glazing": [[x1,y1,x2,y2], ...],
      "rooms": [ { "label": "G19", "poly": [[x,y], ...], "center": [x,y],
                   "zones": ["WFCU.RMG19"] } ] }
  ],
  "unlocated": [ { "equip": "Ground Floor Radiant Floor", "system": "Ground Floor" } ],
  "gsfTotal": 67805
}
```

Only rooms with at least one zone are written. Room labels for rooms without a zone are not written.

Privacy check (the build fails when any rule breaks):

- No output key or value names a door, stair, fixture or furniture layer.
- No room label contains `EL`, `SN`, `SS`, `SC`, `SE`, `VS`, `VN`, `VW` (electrical rooms, stairs, vestibules), except when a SkySpark zone names that room.
- The PDF path is not in the output.

Build report (printed): rooms per floor, zones matched, zones unlocated, overrides used, alignment offsets.

## Component 2: page changes in `seh-energy.html`

Explore the Building tab:

1. Load `floorplan.json` with the other two data files. If it fails to load, fall back to the current schematic grid and show a one-line note.
2. Floors stack in sheet order (Ground, Mezzanine, First, Second, Penthouse) with a visual gap. Plan feet are scaled by 1/2.8 so the building matches the current scene size (about 53 units wide); camera and equipment sizes stay as they are.
3. Walls: one merged `BufferGeometry` per floor, each segment extruded 3 ft high and 0.5 ft thick. Glazing: the same, 3 ft high, translucent blue.
4. Rooms: `ShapeGeometry` from each polygon, lifted 0.1 ft above the slab. Color by the current mode, using the mean of the room's zones at the selected hour. Rooms without data: gray.
5. Floor strip: along the south edge of each floor, one tile per unlocated zone, same coloring.
6. Floor buttons: All, Ground, Mezzanine, First, Second, Penthouse. A single floor hides the others, moves the camera to a top-down view over that floor and shows room numbers as sprites. "All" restores the stack and the orbit view.
7. Picking, tooltips, the detail panel and the time slider work on rooms. A room tooltip lists each zone in it. The detail panel shows the first zone and a switch between zones when there are two or more.
8. Mechanical equipment, meter bars, DOAS-01 and the utility risers move beside the footprint on the west side, labeled "Equipment (schematic, not to location)".
9. The info box under the scene says the plan comes from WSU Facilities reference floor plans, is approximate, and shows only rooms with building-control zones.

Header and data notes: 67,805 GSF (R-sheets). About the Data states the floor plan source and the date plotted.

## Component 3: operations

- `docs/SEH-ENERGY-OPERATIONS.txt` gets a section on rebuilding the floor plan.
- `.gitignore` gets `private/`.
- The weekly job does not run the floor plan build.

## Error handling

- Build: alignment mismatch, privacy rule break, or a floor with zero wall segments stops the build with a clear message. A located room whose shape cannot be traced (its area leaks outside) gets an 8 ft square at its label point and is listed in the report. Unmatched zones do not stop it; they go to the report and the floor strip.
- Page: a missing or invalid `floorplan.json` falls back to the schematic grid.

## Testing

1. Build script: privacy check and alignment check run on every build.
2. Unit check in the build: at least 54 of the 71 zones located (43 rooms on 09/28/2026); Room 105 has zones FPB.L1-16A and FPB.L1-16B.
3. Browser (Playwright, headless): zero console errors; every tab loads; the First Floor button shows a top-down plan; Room 105's polygon center is in the east half of the First Floor bounding box; clicking Room 105 opens its detail panel.
4. Visual check: screenshots of each floor, light and dark mode, and phone width, compared by eye against sheets R-1 to R-5.

## Out of scope

- Other buildings.
- Editing the R-sheets or room data.
- Room names or uses (the sheets carry numbers only).
