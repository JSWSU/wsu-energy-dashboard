"""Inland Power bill parser.

Extracts one record per sub-account from an Inland Power utility bill PDF.
Self-validates each record by checking internal math consistency.

Designed for Washington State University Facilities Services.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import pdfplumber


# -----------------------------------------------------------------------------
# Data model
# -----------------------------------------------------------------------------

@dataclass
class BillRecord:
    # Workbook columns A..W
    account: str = ""                          # A
    statement_date: Optional[datetime] = None  # B
    due_date: Optional[datetime] = None        # C
    meter: Optional[int] = None                # D
    service_address: str = ""                  # E
    period_from: Optional[datetime] = None     # F
    period_to: Optional[datetime] = None       # G
    days: Optional[int] = None                 # H
    prev_read: Optional[int] = None            # I
    pres_read: Optional[int] = None            # J
    multiplier: Optional[int] = None           # K
    kwh: Optional[int] = None                  # L
    energy_rate: Optional[float] = None        # M
    energy_charge: Optional[float] = None      # N
    demand_kw: Optional[float] = None          # O
    demand_rate: Optional[float] = None        # P
    demand_charge: Optional[float] = None      # Q
    service_availability: Optional[float] = None  # R
    outdoor_lighting: Optional[float] = None   # S
    total_current_charges: Optional[float] = None  # T
    previous_balance: Optional[float] = None   # U
    payment_received: Optional[float] = None   # V
    total_amount_due: Optional[float] = None   # W

    # Metadata (not written to workbook)
    source_pdf: str = ""
    warnings: list[str] = field(default_factory=list)
    estimated: bool = False
    final_bill: bool = False

    @property
    def dedup_key(self) -> tuple[str, str]:
        """Key for idempotent dedup against workbook: (account, stmt_date_mmddyyyy)."""
        sd = self.statement_date.strftime("%m/%d/%Y") if self.statement_date else ""
        return (self.account, sd)


# -----------------------------------------------------------------------------
# Regex patterns
# -----------------------------------------------------------------------------

MONEY = r"\$?-?[\d,]+\.\d{2}"
INT = r"[\d,]+"
DEC = r"[\d.]+"

RE_ACCOUNT_HEADER = re.compile(r"Account Number:\s*(\d{9})")
RE_BILLING_PERIOD = re.compile(
    r"Billing Period:\s*(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})\s*for\s*(\d+)\s*Days"
)
RE_BILLING_DATE = re.compile(r"Billing Date:\s*(\d{2}/\d{2}/\d{4})")
RE_SERVICE_ADDR = re.compile(r"Service Address:\s*([^\n]+?)\s*(?:Total Amount Due|$)", re.MULTILINE)
RE_PREV_BAL = re.compile(
    r"Previous Balance on\s*(\d{2}/\d{2}/\d{4})\s*(" + MONEY + r")"
)
RE_PAYMENT = re.compile(r"Payment Received\s*-?(" + MONEY + r")")
RE_TOTAL_AMT_DUE = re.compile(
    r"Total Amount Due\s*(" + MONEY + r")(?!\s+Due Date)"
)
RE_ENERGY_CHARGE = re.compile(
    r"Energy Charge\s*(" + INT + r")\s*kWh\s*@\s*(" + DEC + r")\s*(" + MONEY + r")"
)
RE_DEMAND_CHARGE = re.compile(
    r"Demand Charge\s*(" + DEC + r")\s*kW\s*@\s*(" + DEC + r")\s*(" + MONEY + r")"
)
RE_SAC = re.compile(r"Service Availability Charge\s*(" + MONEY + r")")
RE_OUTDOOR = re.compile(r"Outdoor Lighting(?: Charge)?\s*(" + MONEY + r")")
RE_TOTAL_CURRENT = re.compile(r"Total Current Charges\s*(" + MONEY + r")")
RE_WA_TAX = re.compile(r"WA State Tax.*?(" + MONEY + r")")
RE_TAD_HEADER = re.compile(r"Due Date:\s*(\d{2}/\d{2}/\d{4})")

# Meter reading line: two dates, days, prev, pres, multiplier (and optionally kwh on same line)
RE_METER_LINE = re.compile(
    r"(?:(\d{4,6})\s+)?(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)(?:\s+([\d,]+))?"
)


def _money(s: str) -> float:
    return float(s.replace("$", "").replace(",", ""))


def _date(s: str) -> datetime:
    return datetime.strptime(s, "%m/%d/%Y")


def _int(s: str) -> int:
    return int(s.replace(",", ""))


# -----------------------------------------------------------------------------
# Parser
# -----------------------------------------------------------------------------

def _extract_full_text(pdf_path: Path) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages)


def _split_account_blocks(text: str) -> list[tuple[str, str, str]]:
    """Split text by Account Number markers.

    Returns list of (account_num, detail_block, meter_block) where:
    - detail_block: text from "Account Number:" marker to next marker (or EOT)
    - meter_block: text from previous marker (or start) to this marker — contains
      the meter reading row which appears ABOVE "Account Information" in the PDF
    """
    markers = [(m.start(), m.group(1)) for m in RE_ACCOUNT_HEADER.finditer(text)]
    if not markers:
        return []

    blocks = []
    for i, (start, acc) in enumerate(markers):
        prev_end = markers[i - 1][0] if i > 0 else 0
        next_start = markers[i + 1][0] if i + 1 < len(markers) else len(text)
        meter_block = text[prev_end:start]
        detail_block = text[start:next_start]
        blocks.append((acc, detail_block, meter_block))
    return blocks


def _find_meter_reading(meter_block: str, billing_from: datetime, billing_to: datetime) -> tuple[
    Optional[int], Optional[int], Optional[int], Optional[int], Optional[int]
]:
    """Extract (meter, prev_read, pres_read, multiplier, kwh_from_line) from a meter block."""
    bf = billing_from.strftime("%m/%d/%Y")
    bt = billing_to.strftime("%m/%d/%Y")

    # Prefer the LAST matching meter line (the one closest to the account header)
    last_match = None
    for m in RE_METER_LINE.finditer(meter_block):
        if m.group(2) == bf and m.group(3) == bt:
            last_match = m

    if last_match is None:
        return None, None, None, None, None

    meter_from_line = int(last_match.group(1)) if last_match.group(1) else None
    prev = int(last_match.group(5))
    pres = int(last_match.group(6))
    mult = int(last_match.group(7))
    kwh_on_line = int(last_match.group(8).replace(",", "")) if last_match.group(8) else None

    # If meter number wasn't captured (happens when pdfplumber puts it on a separate line),
    # look for a standalone 4-6 digit number earlier in the meter block
    if meter_from_line is None:
        for line in reversed(meter_block.split("\n")):
            s = line.strip()
            if re.fullmatch(r"\d{4,6}", s):
                meter_from_line = int(s)
                break

    return meter_from_line, prev, pres, mult, kwh_on_line


def parse_pdf(pdf_path: str | Path) -> list[BillRecord]:
    """Parse an Inland bill PDF. Returns one BillRecord per sub-account found."""
    pdf_path = Path(pdf_path)
    text = _extract_full_text(pdf_path)

    records: list[BillRecord] = []
    for acc, block, meter_block in _split_account_blocks(text):
        rec = BillRecord(account=acc, source_pdf=pdf_path.name)

        # Statement date (Billing Date)
        m = RE_BILLING_DATE.search(block)
        if m:
            rec.statement_date = _date(m.group(1))

        # Due date (look for "Due Date: MM/DD/YYYY" before billing info)
        m = RE_TAD_HEADER.search(block)
        if m:
            rec.due_date = _date(m.group(1))

        # Billing period
        m = RE_BILLING_PERIOD.search(block)
        if m:
            rec.period_from = _date(m.group(1))
            rec.period_to = _date(m.group(2))
            rec.days = int(m.group(3))

        # Service address
        m = RE_SERVICE_ADDR.search(block)
        if m:
            rec.service_address = m.group(1).strip()

        # Previous balance
        m = RE_PREV_BAL.search(block)
        if m:
            rec.previous_balance = _money(m.group(2))

        # Payment received (stored as negative per workbook convention)
        m = RE_PAYMENT.search(block)
        if m:
            rec.payment_received = -_money(m.group(1))

        # Total Amount Due for this account block
        m = RE_TOTAL_AMT_DUE.search(block)
        if m:
            rec.total_amount_due = _money(m.group(1))

        # Energy charge: kwh, rate, charge
        m = RE_ENERGY_CHARGE.search(block)
        if m:
            rec.kwh = _int(m.group(1))
            rec.energy_rate = float(m.group(2))
            rec.energy_charge = _money(m.group(3))

        # Demand charges — there can be multiple lines (tiered demand)
        demand_matches = list(RE_DEMAND_CHARGE.finditer(block))
        if demand_matches:
            # Sum all demand charges; use the largest kW and its rate as reported
            total_demand = 0.0
            largest_kw = 0.0
            demand_rate = None
            for dm in demand_matches:
                kw = float(dm.group(1))
                rate = float(dm.group(2))
                charge = _money(dm.group(3))
                total_demand += charge
                if charge > 0 and kw >= largest_kw:
                    largest_kw = kw
                    demand_rate = rate
            if total_demand > 0:
                rec.demand_kw = largest_kw
                rec.demand_rate = demand_rate
                rec.demand_charge = round(total_demand, 2)

        # Service Availability Charge
        m = RE_SAC.search(block)
        if m:
            rec.service_availability = _money(m.group(1))

        # Outdoor Lighting
        m = RE_OUTDOOR.search(block)
        if m:
            rec.outdoor_lighting = _money(m.group(1))

        # Total Current Charges
        m = RE_TOTAL_CURRENT.search(block)
        if m:
            rec.total_current_charges = _money(m.group(1))

        # Meter reading line (uses billing_from/to to disambiguate from other months)
        if rec.period_from and rec.period_to:
            meter, prev, pres, mult, kwh_line = _find_meter_reading(
                meter_block, rec.period_from, rec.period_to
            )
            rec.meter = meter
            rec.prev_read = prev
            rec.pres_read = pres
            rec.multiplier = mult

            # If kwh wasn't on the line, the Energy Charge line gave us kwh
            # Cross-check: (pres - prev) * mult should equal kwh
            if prev is not None and pres is not None and mult is not None:
                computed = (pres - prev) * mult
                if rec.kwh is None:
                    rec.kwh = computed
                elif computed != rec.kwh:
                    # Final bills may have 0 readings but nonzero kWh claim, flag it
                    rec.warnings.append(
                        f"kWh mismatch: computed {computed} vs energy-charge line {rec.kwh}"
                    )

        # Final bill detection
        if rec.days == 0 or (rec.prev_read is not None and rec.pres_read is not None
                             and rec.prev_read == rec.pres_read and rec.kwh == 0):
            rec.final_bill = True

        records.append(rec)

    return records


# -----------------------------------------------------------------------------
# Validation
# -----------------------------------------------------------------------------

def validate(rec: BillRecord, tolerance: float = 0.02) -> list[str]:
    """Check internal math consistency. Returns list of error strings (empty = OK)."""
    errors: list[str] = []

    def near(a, b, tol=tolerance):
        if a is None or b is None:
            return True
        return abs(a - b) <= tol

    # 1. Account number format
    if not re.fullmatch(r"\d{9}", rec.account or ""):
        errors.append(f"invalid account number: {rec.account!r}")

    # 2. Required dates
    if rec.statement_date is None:
        errors.append("missing statement date")
    if rec.period_from is None or rec.period_to is None:
        errors.append("missing billing period")

    # 3. Reading math: (pres - prev) * mult = kwh (skip for final bills)
    if not rec.final_bill:
        if (rec.prev_read is not None and rec.pres_read is not None
                and rec.multiplier is not None and rec.kwh is not None):
            computed = (rec.pres_read - rec.prev_read) * rec.multiplier
            if computed != rec.kwh and rec.pres_read < rec.prev_read:
                # Meter register rollover: dial wraps past its max (e.g. prev
                # 98941 -> pres 717 on a 5-digit register = 1776 kWh). Try the
                # smallest power-of-ten modulus that covers the previous read.
                modulus = 10 ** len(str(int(rec.prev_read)))
                computed = (modulus - rec.prev_read + rec.pres_read) * rec.multiplier
            if computed != rec.kwh:
                errors.append(
                    f"kWh math: ({rec.pres_read}-{rec.prev_read})*{rec.multiplier}={computed} "
                    f"but bill says {rec.kwh}"
                )

    # 4. Energy charge math: kwh * rate ~= energy_charge
    if rec.kwh is not None and rec.energy_rate is not None and rec.energy_charge is not None:
        expected = round(rec.kwh * rec.energy_rate, 2)
        if not near(expected, rec.energy_charge, 0.05):
            errors.append(
                f"energy charge math: {rec.kwh}*{rec.energy_rate}={expected} "
                f"but bill says {rec.energy_charge}"
            )

    # 5. Total current charges = energy + demand + SAC + outdoor_lighting
    if rec.total_current_charges is not None:
        parts = [
            rec.energy_charge or 0,
            rec.demand_charge or 0,
            rec.service_availability or 0,
            rec.outdoor_lighting or 0,
        ]
        expected_total = round(sum(parts), 2)
        # Inland rounds some statement totals to the whole dollar (observed
        # $207.75 billed as $208.00), so allow up to a $0.50 rounding gap.
        if not near(expected_total, rec.total_current_charges, 0.50):
            errors.append(
                f"total current charges: {'+'.join(str(p) for p in parts)}={expected_total} "
                f"but bill says {rec.total_current_charges}"
            )

    return errors
