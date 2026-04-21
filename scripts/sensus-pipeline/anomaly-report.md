# Sensus AMR Data/Config Anomaly Report

Generated: 2026-04-21

Source files:
- **2026-02-09**: `C:\Users\john.slagboom\Downloads\Sensus Testbed\Output\AMRoutput20260209_copy.csv`
- **2026-04-03**: `C:\Users\john.slagboom\Downloads\Sensus Testbed\Output\AMRoutput20260403.csv`
- **2026-04-21**: `C:\Users\john.slagboom\Downloads\Sensus Testbed\Output\AMRoutput20260421.csv`

Unique accounts across all 3 runs: **156**

Scope: **data + configuration anomalies only**. Physical issues (leaks, continuous use) are out of scope.

Column mapping used (27 fields, 0-indexed): Account=0, Bldg#=5, SvcAddr=6, LocDesc=7, Meter#=8, SvcType=9, LastMo(dyn)=10, Current(dyn)=11, **RawRead=12**, ErrChk=13, BillEnd=14, MXU_ID=16, MeterID=17, MtrType=18, MXUType=19, ReadDate=20, ReadTime=21, High=22, Low=23, System=24, **Multiplier=25**.

Known valid codes — System: DW, IR.  Meter Type: B (SmartPoint), P (Pit), M (Manual).  Expected Multipliers: 1/10/100/1000.

**Findings summary:**

| Severity | Count |
|---|---|
| HIGH | 15 |
| MED | 12 |
| LOW | 1 |
| **Total** | **28** |

## Executive Summary — HIGH severity data/config issues

### Acct 200020

STEF CENTER small orchard (0180_DW_001) is a **manual-read meter (Meter Type = M)**, no MXU/Meter ID. Reading dropped by 1 unit (1,924,147 → 1,924,146) between 04/03 and 04/21 runs. Most likely a transcription error on manual entry, not an automated data issue. Note: the 04/03 file shows Read Date 02/27/2026 — the 04/03 export re-published a Feb manual value.

### Acct 200045

ENTOM SHOP (0111A, Meter ID 89124877) reads **exactly 0000** in all 3 runs with Multiplier=1000. An active building reading literally 0 across 2+ months is almost certainly a configuration or register problem: newly installed but uncommissioned, stalled register, bad MXU → meter coupling, or an export column misalignment. Verify with an on-site read before trusting usage billed on this account.

### Acct 200051

ENTOM GREENHOUSE 0111 is a manual meter (Meter Type = M, no MXU ID, Meter ID 1852844682). The 02/09 file records raw='118811.49' (with decimal), while 04/03 = '11891937' and 04/21 = '11931225' (integer). This is almost certainly a **unit/format change** — e.g., 02/09 recorded as ccf × 100 with decimals, later exports recorded as raw pulses without decimals. Differencing these runs for usage = 11,891,937 − 118,811.49 = +11.77M fake units. **Reconcile the format before computing any cross-run usage for 200051.**

### Acct 200083

Valley Crest Apts Main IR (0675, Meter ID 95260687) raw = **999999768 in all 3 runs**, Mult=1, System=IR. This is pinned within 232 units of the 9-digit (999,999,999) rollover boundary. Either the register has rolled over and the MXU is still reporting the pre-rollover snapshot, or the register is physically stuck at near-max. Either way the Usage calc will be wrong until it's resolved.

### Acct 200104

McEachern All Sites (0805, Meter ID 95236516) shows **9-digit readings that continuously DECREASE** (992,485,723 → 992,259,351 → 991,851,628) while Multiplier=1. Total drop = 634,095 units over ~2 months. Physical meters do not run backwards. Likely causes: (a) Multiplier should be 10 or 100 and the raw register wrapped, (b) wrong Meter ID is being read (identity crossed with a nearby meter), or (c) an encoder/BCT reversed on swap. THIS IS THE HIGHEST-VALUE DATA FINDING — it invalidates any usage calc on 200104.

### Acct 200105

Nez Perce Bldgs ABU (0677_DW_001, Meter ID 95260674) was present in 02/09 and 04/03 files but **DROPPED FROM 04/21**. Either the route was edited, MXU is offline, or the meter was removed. Verify — a DW meter vanishing mid-cycle is a data continuity issue.

### Acct 200148

Steptoe Village Bldg P (0665_DW_014, Meter ID 95260680) raw = **999992946 in all 3 runs**, Mult=1, System=DW. DW meter pinned near 9-digit rollover. Residential DW should have daily usage; this is a register or export-identity problem, not a real zero-use condition.

### Acct 200031 (MED)

ALBRK LAB (0071, Meter ID 91248976) raw=23 unchanged across all 3 runs, Multiplier=1000. Tablet IS physically polling (read dates 02/04, 02/25, 04/08) but register value is frozen. Either (a) meter truly registering 0 usage for 60+ days (physical), or (b) register/MXU stuck (data/config). Classify after walking meter — if flow is visible, this is a config issue.

### Acct 200112 (MED)

Marriot Residence Inn IR (0865_IR_001) irrigation raw=5540 unchanged across 3 runs, Mult=1000. For Pullman irrigation in Feb–Apr this is plausibly *legitimate* (winter shut-off). Flagged only because the multiplier of 1000 × zero delta means Usage is being reported as 0 consistently; confirm irrigation is physically off before dismissing.

### Acct 200095 (MED)

Terrace Apts IR Bldg A (0650A) **appears only in 04/21** — either newly commissioned, newly added to route, or previously dropped from the export. Raw reading = 294,620 with 9-digit leading-zero width ('000294620').

### Acct 200131 (MED)

USDA Machine Shop West (0195) **appears only in 04/21** — new to the route or newly commissioned. Raw = 00033 × Mult 100; verify historical baseline exists before billing.

---

## All findings by category

### [HIGH] Account missing in some runs — 2

- **Acct 200105** (bldg 0677): present in ['2026-02-09', '2026-04-03']; missing from ['2026-04-21']
- **Acct 200160** (bldg 0138): present in ['2026-02-09', '2026-04-03']; missing from ['2026-04-21']

### [HIGH] Raw reading contains decimal — 1

- **Acct 200051** (bldg 0111): [2026-02-09] line 46: raw reading '118811.49' contains a decimal point (other runs are integer); Usage calc will be wildly wrong when integer/decimal runs are differenced (Multiplier=1)

### [HIGH] Raw reading decreased (non-rollover) — 3

- **Acct 200020** (bldg 0180): 2026-04-03 read=1924147 (1924147) → 2026-04-21 read=1924146 (1924146); drop=1
- **Acct 200104** (bldg 0805): 2026-02-09 read=992485723 (992485723) → 2026-04-03 read=992259351 (992259351); drop=226372
- **Acct 200104** (bldg 0805): 2026-04-03 read=992259351 (992259351) → 2026-04-21 read=991851628 (991851628); drop=407723

### [HIGH] Raw reading is zero — 3

- **Acct 200045** (bldg 0111A): [2026-02-09] line 41: raw reading=0 literally (Multiplier=1000)
- **Acct 200045** (bldg 0111A): [2026-04-03] line 38: raw reading=0 literally (Multiplier=1000)
- **Acct 200045** (bldg 0111A): [2026-04-21] line 41: raw reading=0 literally (Multiplier=1000)

### [HIGH] Raw reading pinned near 9-digit max — 6

- **Acct 200083** (bldg 0675): [2026-02-09] line 76: raw reading=999999768 ≥ 999,990,000 (System=IR, Multiplier=1) — likely rolled over but AMR still reports pre-rollover value
- **Acct 200083** (bldg 0675): [2026-04-03] line 73: raw reading=999999768 ≥ 999,990,000 (System=IR, Multiplier=1) — likely rolled over but AMR still reports pre-rollover value
- **Acct 200083** (bldg 0675): [2026-04-21] line 76: raw reading=999999768 ≥ 999,990,000 (System=IR, Multiplier=1) — likely rolled over but AMR still reports pre-rollover value
- **Acct 200148** (bldg 0665): [2026-02-09] line 137: raw reading=999992946 ≥ 999,990,000 (System=DW, Multiplier=1) — likely rolled over but AMR still reports pre-rollover value
- **Acct 200148** (bldg 0665): [2026-04-03] line 134: raw reading=999992946 ≥ 999,990,000 (System=DW, Multiplier=1) — likely rolled over but AMR still reports pre-rollover value
- **Acct 200148** (bldg 0665): [2026-04-21] line 138: raw reading=999992946 ≥ 999,990,000 (System=DW, Multiplier=1) — likely rolled over but AMR still reports pre-rollover value

### [MED] Account missing in some runs — 5

- **Acct 200015** (bldg 0141H): present in ['2026-02-09', '2026-04-21']; missing from ['2026-04-03']
- **Acct 200022** (bldg 0182): present in ['2026-02-09', '2026-04-21']; missing from ['2026-04-03']
- **Acct 200027** (bldg 0057): present in ['2026-02-09', '2026-04-21']; missing from ['2026-04-03']
- **Acct 200095** (bldg 0650A): present in ['2026-04-21']; missing from ['2026-02-09', '2026-04-03']
- **Acct 200131** (bldg 0195): present in ['2026-04-21']; missing from ['2026-02-09', '2026-04-03']

### [MED] DW meter raw reading stuck across all 3 runs — 5

- **Acct 200014** (bldg 0141G): raw=213780 unchanged across ['2026-02-09', '2026-04-03', '2026-04-21']; Mult=1, System=DW (ongoing DW usage would normally cause the register to advance)
- **Acct 200084** (bldg 0679): raw=231 unchanged across ['2026-02-09', '2026-04-03', '2026-04-21']; Mult=1, System=DW (ongoing DW usage would normally cause the register to advance)
- **Acct 200121** (bldg 0678): raw=743 unchanged across ['2026-02-09', '2026-04-03', '2026-04-21']; Mult=1, System=DW (ongoing DW usage would normally cause the register to advance)
- **Acct 200146** (bldg 0665): raw=73 unchanged across ['2026-02-09', '2026-04-03', '2026-04-21']; Mult=1, System=DW (ongoing DW usage would normally cause the register to advance)
- **Acct 200148** (bldg 0665): raw=999992946 unchanged across ['2026-02-09', '2026-04-03', '2026-04-21']; Mult=1, System=DW (ongoing DW usage would normally cause the register to advance)

### [MED] Raw reading stuck across all 3 runs — 2

- **Acct 200031** (bldg 0071): raw=23 unchanged across ['2026-02-09', '2026-04-03', '2026-04-21']; Mult=1000, System=DW
- **Acct 200112** (bldg 0865): raw=5540 unchanged across ['2026-02-09', '2026-04-03', '2026-04-21']; Mult=1000, System=IR

### [LOW] Raw reading digit-count changed — 1

- **Acct 200051** (bldg 0111): widths over time: 2026-02-09=9; 2026-04-03=8; 2026-04-21=8 (raws: 118811.49 / 11891937 / 11931225)

