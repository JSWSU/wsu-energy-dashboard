"""Export Schweitzer Engineering Hall (0802) data from SkySpark for seh-energy.html.

Read-only. Writes data/0802/points.json and data/0802/meters.json.
Run: py export_0802.py
"""
import importlib.util, json, os, time, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("aud", os.path.join(HERE, "auto-update-data.py"))
aud = importlib.util.module_from_spec(spec); spec.loader.exec_module(aud)
cfg = json.load(open(os.path.join(HERE, "skyspark-auth.json")))
BASE, PROJ = cfg["base_url"], cfg["project"]
SITE = "@p:wsumeters:r:309fac68-99fd2383"          # site 0802
WEATHER_TEMP = "@p:wsumeters:r:27ab2ffe-4d782119"  # Pullman, WA Temp
HIS_START = "2026-02-05"                            # first 0802 history
OUT = os.path.join(HERE, "data", "0802")
HDR = None


def ev(expr, timeout=600):
    global HDR
    e = expr.replace("\\", "\\\\").replace('"', '\\"')
    body = f'ver:"3.0"\nexpr\n"{e}"\n'.encode()
    for attempt in range(2):
        if HDR is None or attempt:
            HDR = aud.scram_login(BASE, PROJ, cfg["username"], cfg["password"])
        st, _, resp = aud.http(f"{BASE}/api/{PROJ}/eval", method="POST",
                               headers={**HDR, "Content-Type": "text/zinc; charset=utf-8",
                                        "Accept": "application/json"}, body=body, timeout=timeout)
        if st in (401, 403) and attempt == 0:
            continue
        if st != 200:
            raise RuntimeError(f"HTTP {st}: {resp[:400]}")
        g = json.loads(resp)
        if "err" in g.get("meta", {}):
            raise RuntimeError(json.dumps(g["meta"])[:600])
        time.sleep(0.5)
        return g


def s(v):
    """Haystack JSON value to plain python."""
    if isinstance(v, dict):
        k = v.get("_kind")
        if k == "ref": return v.get("dis") or v.get("val")
        if k == "number": return v.get("val")
        if k == "marker": return True
        if k in ("dateTime", "date"): return v.get("val")
        if k == "na": return None
        return v.get("val", v.get("dis"))
    return v


def rnd(x):
    if x is None or isinstance(x, bool) or not isinstance(x, (int, float)): return x
    if x != x: return None
    a = abs(x)
    return round(x, 3 if a < 10 else 2 if a < 1000 else 0)


def ts_epoch(v):
    return int(datetime.datetime.fromisoformat(s(v)).timestamp())


def his_grid(g):
    """Wide his grid -> (point id list, epoch list, {id: values})."""
    cols = [c for c in g["cols"] if c["name"] != "ts"]
    ids = [c["meta"]["id"]["val"] for c in cols]
    t = [ts_epoch(r["ts"]) for r in g["rows"]]
    vals = {pid: [rnd(s(r.get(c["name"]))) for r in g["rows"]] for pid, c in zip(ids, cols)}
    return ids, t, vals


def strip_equip(name):
    return name[5:] if name and name.startswith("0802 ") else name


def main():
    os.makedirs(OUT, exist_ok=True)
    site = ev(f"readById({SITE})")["rows"][0]
    equips = ev(f"readAll(equip and siteRef=={SITE})")["rows"]
    points = ev(f"readAll(point and siteRef=={SITE})")["rows"]
    print(f"site 0802: {len(equips)} equips, {len(points)} points")

    eq_out = []
    for e in equips:
        tags = sorted(k for k, v in e.items() if isinstance(v, dict) and v.get("_kind") == "marker")
        eq_out.append({
            "id": e["id"]["val"], "name": strip_equip(s(e["id"])), "type": s(e.get("equipTypeName")),
            "system": strip_equip(s(e.get("systemRef"))), "parent": strip_equip(s(e.get("equipRef"))),
            "submeterOf": strip_equip(s(e.get("submeterOf"))), "ahu": strip_equip(s(e.get("ahuRef"))),
            "voltage": s(e.get("voltage")), "alias": s(e.get("basNameNew")), "tags": tags})

    # hourly averages for the last 7 days, one read per system to keep grids small
    end = datetime.date.today()
    rng = f"{(end - datetime.timedelta(days=7)).isoformat()}..{end.isoformat()}"
    systems = sorted({e["systemRef"]["val"] for e in equips if e.get("systemRef")})
    t0 = int(datetime.datetime.combine(end - datetime.timedelta(days=7), datetime.time()).astimezone().timestamp())
    t1 = int(datetime.datetime.combine(end + datetime.timedelta(days=1), datetime.time()).astimezone().timestamp())
    hourly_t = list(range(t0, t1, 3600))
    slot = {x: i for i, x in enumerate(hourly_t)}
    hourly = {}
    for sysid in systems + [None]:
        flt = f"systemRef==@{sysid}" if sysid else "not systemRef"
        try:
            g = ev(f"readAll(point and his and kind==\"Number\" and siteRef=={SITE} and {flt})"
                   f".hisRead(parseDate(\"{rng.split('..')[0]}\")..parseDate(\"{rng.split('..')[1]}\"))"
                   f".hisRollup(avg,1hr)")
        except RuntimeError as ex:
            print("hourly read failed", sysid, ex); continue
        if not g["rows"]: continue
        ids, t, vals = his_grid(g)
        for pid in ids:
            arr = [None] * len(hourly_t)
            for x, v in zip(t, vals[pid]):
                if x in slot: arr[slot[x]] = v
            hourly[pid] = arr
    print(f"hourly series: {len(hourly)} points x {len(hourly_t or [])} hours")

    pt_out = []
    for p in points:
        pid = p["id"]["val"]
        tags = sorted(k for k, v in p.items() if isinstance(v, dict) and v.get("_kind") == "marker"
                      and k not in ("point", "his", "hisAppendNA", "bacnetCur", "batchTagged", "cacheHis"))
        cv = s(p.get("curVal"))
        pt_out.append({
            "id": pid, "equip": strip_equip(s(p.get("equipRef"))), "system": strip_equip(s(p.get("systemRef"))),
            "name": p.get("navName"), "desc": s(p.get("basDescription")), "unit": s(p.get("unit")),
            "kind": p.get("kind"), "cur": rnd(cv) if not isinstance(cv, str) else cv,
            "status": s(p.get("curStatus")), "enum": s(p.get("enum")),
            "hisStart": (s(p.get("hisStart")) or "")[:10] or None, "hisEnd": (s(p.get("hisEnd")) or "")[:16] or None,
            "tags": tags, "h": hourly.get(pid)})

    generated = datetime.datetime.now().astimezone().isoformat(timespec="minutes")
    json.dump({"generated": generated, "site": {"name": s(site.get("building")), "number": "0802",
               "yearBuilt": s(site.get("yearBuilt"))},
               "hourlyStart": hourly_t[0] if hourly_t else None, "hourlyStep": 3600,
               "equips": eq_out, "points": pt_out},
              open(os.path.join(OUT, "points.json"), "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False)

    # ---- meters: 15-min for 7 days, daily since first history ----
    def pick(eqname, nav):
        for p in points:
            if s(p.get("equipRef")) == "0802 " + eqname and p.get("navName") == nav:
                return p["id"]["val"]
        return None

    series = [("Electric", "Electric", "total elec power", "kW", "elec")]
    for e in sorted(eq_out, key=lambda x: x["name"]):
        if e["type"] == "Elec Meter" and e["name"] != "Electric":
            series.append((e["name"].split(" ")[0], e["name"], "elec power", "kW", "elec"))
    series += [("0802_CE_001", "0802_CE_001", "chw clg power", "BTU/h", "chw"),
               ("0802_HE_001", "0802_HE_001", "hhw htg power", "BTU/h", "hhw"),
               ("0802_DW_001", "0802_DW_001", "dcw flow", "gal/min", "dcw"),
               ("0802_DHW_001", "0802_DHW_001", "dhw flow", "gal/min", "dhw")]
    meters = []
    for key, eqname, nav, unit, util in series:
        pid = pick(eqname, nav)
        if not pid:
            print("missing", eqname, nav); continue
        e = next((x for x in eq_out if x["name"] == eqname), {})
        meters.append({"key": key, "equip": eqname, "point": nav, "id": pid, "unit": unit, "utility": util,
                       "submeterOf": e.get("submeterOf"), "voltage": e.get("voltage")})
    meters.append({"key": "OAT", "equip": "Pullman weather", "point": "outside air temp",
                   "id": WEATHER_TEMP[1:], "unit": "°F", "utility": "weather"})

    idlist = ",".join("@" + m["id"] for m in meters)
    d7 = (end - datetime.timedelta(days=7)).isoformat()
    g = ev(f"[{idlist}].map(id=>readById(id)).toGrid.hisRead(parseDate(\"{d7}\")..today()).hisRollup(avg,15min)")
    ids, t15, v15 = his_grid(g)
    g = ev(f"[{idlist}].map(id=>readById(id)).toGrid.hisRead(parseDate(\"{HIS_START}\")..today()).hisRollup(avg,1day)")
    idsd, td, vd = his_grid(g)
    for m in meters:
        m["q15"] = v15.get(m["id"])
        m["daily"] = vd.get(m["id"])

    json.dump({"generated": generated, "q15Start": t15[0] if t15 else None, "q15Step": 900, "q15t": t15,
               "dailyT": td, "meters": meters},
              open(os.path.join(OUT, "meters.json"), "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False)
    for f in ("points.json", "meters.json"):
        print(f, os.path.getsize(os.path.join(OUT, f)) // 1024, "KB")


if __name__ == "__main__":
    main()
