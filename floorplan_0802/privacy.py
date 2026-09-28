"""Fail the build if floorplan.json would publish anything outside the approved public set."""
import json
import re


class PrivacyError(RuntimeError):
    pass


LAYER_RE = re.compile(r"\bA-[A-Z]{3,4}(-[A-Z]{3,4})*\b")
SENSITIVE_RE = re.compile(r"(EL|SN|SS|SC|SE|VS|VN|VW)$")


def check(floorplan):
    text = json.dumps(floorplan)
    m = LAYER_RE.search(text)
    if m:
        raise PrivacyError(f"CAD layer name in output: {m.group(0)}")
    if re.search(r"\.pdf|private[/\\]", text, re.I):
        raise PrivacyError("source pdf path in output")
    for f in floorplan["floors"]:
        for r in f["rooms"]:
            if not r.get("zones"):
                kind = "sensitive room" if SENSITIVE_RE.search(r["label"]) else "room without a zone"
                raise PrivacyError(f"{kind} in output: {r['label']} on {f['system']}")
