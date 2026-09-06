# Phase 2 — Synthetic data generator and validation suite

Goal: a seeded, deterministic generator that produces the complete Northlake dataset described by
`docs/data-contract.md`, and a validation suite that proves it. When this phase is done, every
number the rest of the project consumes exists, and every claim the data contract makes about that
data is asserted by a test rather than asserted by a document.

Tag on completion: `v0.3-data`

> **Numbering.** Phase 1 was the interview, data contract and ADRs; phase 2 is the generator and
> validation suite. `CLAUDE.md`, `README.md` and `phase-00-spec.md` were renumbered to match, which
> shifted every subsequent phase and tag by one. No tag was renamed after being cut.

---

## Scope boundary: what is generated at transaction grain

The contract requires seven operational fact grains (§5) but does **not** require them across the
whole 72-month spine, and generating them everywhere would be both wasteful and dishonest — §8
states explicitly that months 19–36 of the forecast "do not require artificial order-line
precision."

| Period | Grain generated |
|---|---|
| FY2023–FY2025 (actuals, 36 months) | Full transaction detail — every fact table in §5 at its declared grain |
| FY2026–FY2028 (forecast, 36 months) | Monthly driver and ledger grain only, by version × scenario |

Forecast facts therefore land at `GL account × department × month × version × scenario` plus the
monthly operating schedules that feed them. No synthetic order lines are invented for 2028.

**Version and scenario coverage.** Actuals carry version `Actual` and no scenario. Forecast carries
the version × scenario combinations that actually exist — `Budget` under Balanced Base only,
`Prior Forecast` and `Latest Forecast` under all three scenarios. Generating the full cross-product
would fabricate versions the business never produced.

Expected volume, for sizing rather than as a target: roughly 330k DTC order lines, 30k wholesale
invoice lines, 24k returns, 96k daily inventory rows, ~1k PO lines with ~2k payments, 13k marketing
rows, ~900 headcount rows, and ~120k ledger rows. Order of half a million rows in total.

---

## Order of work

The order matters. Dimensions before facts, actuals before forecast, and the financing module
before the forecast that depends on it.

### 1. Decisions and configuration

Three dependencies are required and need sign-off before any code (`CLAUDE.md`: adding a dependency
is a stop-and-ask):

| Package | Purpose | Notes |
|---|---|---|
| `numpy` | Seeded RNG, vectorised generation | `default_rng(seed)`, never the legacy global RNG |
| `pandas` | Dataframe assembly and the validation suite | |
| `pyarrow` | Parquet output | Preserves dtypes; CSV would lose integer minor units and dates |

All three are cross-platform and available on Linux CI. None is Windows-only.

Configuration lives in one module with the seed, the spine bounds, and every calibration target
from contract §7. **No literal from §7 is written at a call site.**

### 2. Date spine and calendars

Daily spine 2023-01-01 to 2028-12-31, contiguous, with fiscal month/quarter/year, a banking-day
flag (§2.2), and a promotional-period flag driven by the §7.4 calendar.

### 3. Dimensions

All thirteen from §4, with the SCD behaviour each declares — Type 2 with effective dating for
product, wholesale account, supplier and employee; Type 1 for the rest. Surrogate integer keys,
natural keys retained as attributes.

Product must satisfy the §4.1 concentration constraints (top 5 ≈ 38%, top 10 ≈ 55% of revenue) and
carry SKU class A/B/C at the 55/30/15 revenue split. Wholesale accounts must satisfy §4.3
(largest 24%, top 5 62%).

### 4. Actuals, FY2023–FY2025

Generated in dependency order: demand → stockout suppression → orders → returns → inventory
movements → purchase orders → payments → ledger.

Two mechanics are the ones most likely to be got wrong and are called out here because they are
where a naive generator produces data that looks right and is not:

- **Stockouts are a suppression layer over demand (§6.6), not weak demand.** Underlying demand and
  realised revenue are both carried. 50% of suppressed demand is lost, 50% substituted or deferred.
- **Purchase orders are lumpy and constrained (§5.5), not a balancing figure.** MOQ rounding, the
  90-day lead time and the cancellation cut-off all bind. The February 2025 launch failure must
  emerge from POs placed October–December 2024 continuing to arrive, not from a hand-placed
  inventory adjustment.

Calibration to §7.1–7.5 is part of this step, not a later correction.

### 5. Financing module

Borrowing base from eligibility rules at monthly grain, revolver, interest on the
beginning-of-period balance (ADR 0001), and the single availability covenant (§6.10). The
$3.25M June 2024 equity raise sits in the FY2024 actuals.

Debt is never a balancing plug: where the base is exhausted the model reports the funding-gap month
and the additional capital required.

### 6. Forecast, FY2026–FY2028

Three scenarios from the §7.6 bounded drivers, at the grain set out above.

### 7. Validation suite

All twenty-nine checks in contract §9, plus the phase-specific criteria below. Each check is a
named test, not a notebook assertion.

### 8. Wire into `bellwether.build`

`python -m bellwether.build` generates the full dataset into `data/` and exits 0 on Linux with no
Excel present. The stage list in `build.py` loses its "not yet implemented" marker for phase 2.

---

## Acceptance criteria

Numbered to match the test module that asserts each. Criteria 2.9–2.31 correspond to the
contract's §9 check of the same subject; where a criterion restates a contract check it is the
contract's tolerance that governs.

| # | Criterion | How it is checked |
|---|---|---|
| **Determinism and build** | | |
| 2.1 | Two runs with the same seed produce byte-identical Parquet output | `tests/data/test_determinism.py` — hash every output file across two runs |
| 2.2 | No `datetime.now()`, no unseeded RNG, no reliance on dict or filesystem ordering | AST scan over `src/bellwether/data/` plus a run under a shuffled `PYTHONHASHSEED` |
| 2.3 | `python -m bellwether.build` exits 0 on Linux with no Excel and writes the full dataset | CI on ubuntu |
| 2.4 | Generation completes within 120 seconds on CI hardware | Timed in CI; fails the build if exceeded |
| 2.5 | `git status` is clean after a generation run | CI working-tree check, already in `ci.yml` |
| **Structure** | | |
| 2.6 | Every fact table is unique at its declared grain, and the grain is stated in the module docstring | `tests/data/test_grain.py`, parametrised over all fact tables |
| 2.7 | Zero orphan keys on every fact-to-dimension join | `tests/data/test_referential_integrity.py` |
| 2.8 | Date spine contiguous 2023-01-01 to 2028-12-31, no gaps, covering every fact date | `tests/data/test_spine.py` |
| 2.9 | No PII field in any customer record; customer keys stable across transactions | `tests/data/test_no_pii.py` — field-name denylist plus a key-stability assertion |
| 2.10 | SCD Type 2 dimensions have non-overlapping, gap-free effective ranges per natural key | `tests/data/test_scd.py` |
| **Accounting** | | |
| 2.11 | Trial balance sums to zero for every period | `tests/data/test_accounting.py` |
| 2.12 | Subledger totals tie to control accounts — AR, AP, inventory, refund liability | `tests/data/test_accounting.py` |
| 2.13 | Gross-to-net ladders reconstructable from ledger accounts alone, both channels, no management adjustment | `tests/data/test_gross_to_net.py` |
| 2.14 | Inventory roll-forward ties every SKU every day: opening + receipts − shipments + returns − write-offs = closing | `tests/data/test_inventory.py` |
| 2.15 | Return write-offs and shrink are separately reported and never netted; FY2025 ≈ $49k and ≈ $35k | `tests/data/test_inventory.py` |
| **Calibration** | | |
| 2.16 | Net revenue FY2023/24/25 within tolerance of $8.10M / $9.30M / $10.60M | `tests/data/test_calibration.py` |
| 2.17 | Channel mix within tolerance of 72/28, 66/34, 59/41 | `tests/data/test_calibration.py` |
| 2.18 | FY2025 blended gross margin 46.7% ±0.5pt; DTC 53.9% ±0.5pt; wholesale 37.1% ±0.5pt; gap 16.8pt ±1pt | `tests/data/test_calibration.py` |
| 2.19 | FY2025 EBITDA −8.1% ±0.5pt; FY2023 positive; FY2024 within ±1pt of zero | `tests/data/test_calibration.py` |
| 2.20 | FY2023/24 driver bounds respected and derived outputs within §7.5 tolerances | `tests/data/test_calibration.py` |
| 2.21 | Inventory turns 4.1x FY2024, 3.3x FY2025, each ±0.2x | `tests/data/test_calibration.py` |
| 2.22 | Wholesale DSO 52 days ±3 | `tests/data/test_calibration.py` |
| 2.23 | SKU concentration top 5 ≈ 38%, top 10 ≈ 55%, each ±2pt | `tests/data/test_concentration.py` |
| 2.24 | Account concentration largest 24%, top 5 62%, each ±2pt | `tests/data/test_concentration.py` |
| **Behaviour** | | |
| 2.25 | Every return arrives after its originating sale, with the stated lag distribution by channel | `tests/data/test_returns.py` |
| 2.26 | Every PO deposit precedes its receipt date; effective DPO is negative | `tests/data/test_purchasing.py` |
| 2.27 | November and December show revenue above trend and gross margin below trend, every year | `tests/data/test_seasonality.py` |
| 2.28 | Underlying demand exceeds realised revenue in stockout periods on hero SKUs, and both are carried | `tests/data/test_stockouts.py` |
| 2.29 | April 2025 onward shows an ~8% product-cost step, isolated from freight and duty | `tests/data/test_events.py` |
| 2.30 | The February 2025 launch cohort shows sell-through materially below the core range and ages into the H2 2025 buckets, driven by POs placed Oct–Dec 2024 | `tests/data/test_events.py` |
| **Financing** | | |
| 2.31 | Balanced Base holds the covenant in every forecast month; minimum excess availability ≈ $264k in Jul-2028 | `tests/data/test_covenants.py` |
| 2.32 | Wholesale Acceleration falls below $250k in Mar-2028 and reaches zero by May-2028; the breach month and additional capital required are reported | `tests/data/test_covenants.py` |
| 2.33 | DTC Recovery holds with minimum excess availability ≈ $555k, never below $500k | `tests/data/test_covenants.py` |
| 2.34 | TTM EBITDA is negative in every month of every scenario; no coverage covenant is evaluated | `tests/data/test_covenants.py` |
| 2.35 | The revolver never draws beyond the borrowing base in any scenario | `tests/data/test_covenants.py` |
| **Sign and range** | | |
| 2.36 | Value ranges and sign conventions plausible per column, not merely non-null | `tests/data/test_ranges.py` |
| 2.37 | Favourable variance is positive regardless of whether the line is revenue or cost | `tests/data/test_ranges.py` |

Criteria 2.31–2.34 carry figures produced by a scratch model during phase 1 review. They are
**expected values, not tolerances yet** — the first generator run pins them, and the tolerance is
set at that point and frozen as a regression. If the generator disagrees materially with the
scratch model, the generator is more likely to be right and the contract figure is amended with an
ADR; what is not acceptable is silently loosening the tolerance until it passes.

**When the first real run lands, the ADR records both figures side by side** — the phase 1
scratch calculation and the full simulation. The delta between a hand-built monthly model and a
transaction-level simulation is itself worth showing: it is the difference between an FP&A
analyst's estimate and the system that replaces it, and a reviewer learns more from seeing the
two agree (or not) than from either alone.

---

## Decisions needed before code

| # | Decision | Why it cannot be defaulted |
|---|---|---|
| D-1 | Approve `numpy`, `pandas`, `pyarrow` | `CLAUDE.md` makes adding a dependency a stop-and-ask |
| D-2 | Parquet as the on-disk format, **plus a ~1,000-row CSV sample per fact table in `samples/`** | CSV loses integer minor units and date types, so Parquet is right for the pipeline — but Parquet is opaque on GitHub, and the browsing reviewer is half the audience |
| D-3 | Confirm the transaction-grain boundary above — full detail for actuals, monthly for forecast | It halves the dataset and it is an interpretation of §8, not a statement of it |
| D-4 | Confirm the version × scenario coverage above | Generating the full cross-product would fabricate versions the business never produced |
| D-5 | Phase renumbering in `CLAUDE.md` and `README.md` | Renames tags; a tag is the maintainer's claim to make |

---

## Known defects carried out of this phase

Both are recorded rather than worked around, and both are owned by phase 3 because the fix needs
the transformation layer. Neither is a reason to hold the phase 2 tag: the generator meets its
acceptance criteria, and these are limits on what the forecast can currently do rather than
errors in what it reports.

| # | Defect | Owner | ADR |
|---|---|---|---|
| D-1 | The forecast ledger does not balance. Only actual periods post double entry, so `financing.py` is a second source of truth for forecast working capital and the borrowing base. Check 11 is **not** narrowed to actuals — the fix is to make the forecast balance. | Phase 3 | [0014](../adr/0014-forecast-ledger-does-not-balance.md) |
| D-2 | `forecast.GM_CALIBRATION` is a hardcoded 3.1pt plug applied uniformly across four scenarios that differ in the channel mix that caused it. Acceleration's margin is overstated and Consolidation's understated. | Phase 3 | [0015](../adr/0015-gm-calibration-is-a-plug.md) |

## Not in this phase

No star schema build, no semantic metric layer, no oracle, no workbook. The generator produces the
transaction ledger and master data the contract describes; turning that into conformed dimensions
and facts for consumption is the next phase.

Nor does this phase produce any financial *presentation* — no statements, no bridges, no board
pack. The validation suite asserts that the data ties, not that it is beautiful.
