# Bellwether

*An FP&A reporting and planning stack for **Northlake, Inc.** — an illustrative company. Every
figure below is produced by a seeded simulator in this repository. No real company, no real
people, no scraped or proprietary data.*

---

## The finding

Northlake raised **$7.5M** in June 2024, at roughly breakeven, on a wholesale growth story. By
FY2025 it was doing **$10.6M** of net revenue and losing **$1.3M**.

The obvious reading is that wholesale margin does not cover its costs. The model says otherwise.

| | Net revenue | Contribution margin | Contribution |
|---|---:|---:|---:|
| DTC | $6.22M | 57.1% | **+$774k** |
| Wholesale | $4.38M | 24.4% | **+$732k** |
| Unallocated corporate | — | — | **−$2,810k** |
| **FY2025 total** | **$10.60M** | | **−$1,304k** |

**Both channels are contribution-positive. Neither is the loss.** The entire loss is a $2.81M
corporate block carried on $10.6M of revenue — and no defensible reallocation of it changes that
conclusion, which the model demonstrates rather than asserts ([ADR 0010][adr10]).

That block is not generically excessive. It was built for wholesale and grew with it —
**directionally, but not proportionally**:

| | FY2023 | FY2024 | FY2025 |
|---|---:|---:|---:|
| Corporate block | $1.81M | $2.18M | $2.81M |
| as % of revenue | 22.3% | 23.5% | **26.5%** |
| Wholesale revenue, indexed | 1.00x | 1.32x | 1.82x |
| Corporate cost, indexed | 1.00x | 1.20x | **1.55x** |

The weaker claim is the one the data supports, so it is the one stated.

### Where that leaves the board

Four scenarios, on two axes — growth versus profitability, and DTC versus wholesale:

| FY2028 | Net revenue | EBITDA | Margin | Covenant |
|---|---:|---:|---:|---|
| Wholesale Acceleration | $16.40M | −$680k | −4.1% | **breaches May-2028** |
| Balanced Base | $14.11M | −$693k | −4.9% | holds, $746k minimum headroom |
| DTC Recovery / Margin | $13.11M | −$592k | −4.5% | holds, $1,181k minimum headroom |
| **Consolidation** | $11.36M | **+$58k** | **+0.5%** | holds, **never draws** |

**The only scenario that reaches profitability is the one that shrinks** — on the lowest revenue
of the four, and only in the last two months of the horizon.

And the scenario with the strongest revenue and the best EBITDA of the three that grow is the one
that runs out of money. That is not a rounding artifact: extending the horizon twelve months
produces an identical first breach and availability that fails at every seasonal peak thereafter.
The explanation is entirely in working capital, which is why the cash flow statement is built by
the indirect method — the receivables and inventory movements it itemises are the same balances
the asset-based facility advances against, at 85% and 50% ([ADR 0018][adr18], [ADR 0008][adr8]).

A model where the most profitable-looking plan is the unfundable one is more interesting, and
more like real FP&A, than one where the rankings agree.

---

## What this is

Raw transactions → dimensional warehouse → driver-based three-statement model → Power BI →
board pack. Six years of monthly data: 36 actual, 36 forecast, four scenarios, four versions.

- **~707,000 rows** across 25 tables, generated from one seed and reproducible byte for byte
- A **double-entry ledger** — every value in the statements is posted, not assembled
- A **nine-sheet Excel model**, 72 months, with live version and scenario selectors
- **Balance sheet balances to $0.000000** and cash flow closing cash equals balance sheet cash to
  $0.000000, across all 360 period × version × scenario rows
- **135 tests**, every one traceable to a numbered acceptance criterion in a phase spec

### The architecture, in one line

**The Python oracle originates every number; Excel reproduces them; a reconciliation test proves
the two agree.**

Every formula cell in the workbook is written with *both* its formula and the oracle's value as
its cached result. That is what lets two rules hold at once: the workbook is complete and correct
on a Linux box with no Excel installed, and when Excel does open it, recalculation *reproduces*
the figures rather than computing them. A formula written without its cached value is a defect,
and the only function that writes one refuses to.

Excel is additive. It recalculates, adds native data tables and pivots, and exports the PDF. It
never originates a value. If a number appears there that the oracle did not compute, that is a
defect regardless of whether it happens to be right.

### Run it

```bash
python -m bellwether.build                    # headless: data, warehouse, workbook
python -m pytest -m "not requires_excel"      # what CI runs, on Linux
```

Excel is **not** required, and CI proves it by building on Linux with no Excel present. On
Windows with Excel installed there is an additional packaging stage:

```powershell
.venv\Scripts\python.exe -m bellwether.excel_stage   # recalc, data tables, PDF, PNG
.venv\Scripts\python.exe -m pytest                   # adds the Excel reconciliation
```

---

## The decision log

The ADRs are the most useful thing here for anyone assessing how the project was built. Several
exist because **constructing the thing disagreed with the document** — the inventory target and
the service level turned out to be jointly infeasible, two different return rates were both
"7%", and the forecast ledger did not balance. Each disagreement is recorded with the alternative
considered and why it lost.

**Accounting policy**
[0001][adr1] interest on the opening balance ·
[0002][adr2] ASC 606 returns ·
[0003][adr3] standard landed cost with variances ·
[0004][adr4] the COGS boundary ·
[0017][adr17] reserve and unwind as separate accounts ·
[0018][adr18] indirect cash flow

**Measurement and definitions**
[0005][adr5] marketing as a constrained driver ·
[0006][adr6] three explicit CAC definitions ·
[0010][adr10] channel contribution with corporate unallocated ·
[0012][adr12] category return rates normalised

**Model structure**
[0007][adr7] version and scenario as two dimensions ·
[0008][adr8] the revolver as a binding constraint ·
[0009][adr9] supplier contracts in USD ·
[0016][adr16] actuals carry the operating plan scenario

**Found by building it**
[0011][adr11] inventory turns relaxed to the achievable service frontier ·
[0013][adr13] margin amended to the generated figures ·
[0014][adr14] the forecast ledger did not balance — raised in phase 2, resolved in phase 3 ·
[0015][adr15] `GM_CALIBRATION` was a plug — raised in phase 2, resolved in phase 3

Supporting documents: [charter](docs/charter.md) (scope, and why no growth scenario turns
profitable), [architecture](docs/architecture.md) (layers and the COM boundary),
[data contract](docs/data-contract.md) (every entity, grain, key and calibration target),
[phase specs](docs/phases/) (numbered acceptance criteria, each mapped to a test).

A committed CSV sample of every table is in [`samples/`](samples/) — ~1,000 rows each, so the
warehouse can be inspected without running anything.

---

## Status

**Phase 4 complete.** Phases 5 to 7 remain.

| Phase | Output | Tag |
|---|---|---|
| 0 | Repo scaffold, docs, CI, pre-commit | `v0.1-scaffold` |
| 1 | Data contract: interview, contract, ADRs | `v0.2-contract` |
| 2 | Synthetic generator, validation suite | `v0.3-data` |
| 3 | Transformation layer, star schema, semantic definitions | `v0.4-warehouse` |
| 4 | Code-generated Excel model, three statements tying | `v0.5-model` |
| 5 | Power BI PBIP, DAX, four report pages | `v0.6-bi` |
| 6 | Board pack, automated variance commentary | `v0.7-reporting` |
| 7 | README, case study, video, distribution assets | `v1.0` |

No phase begins until the previous one is tagged, its tests are green and its docs are updated.

---

## Installation

Python 3.12.

```bash
git clone <this repo>
cd bellwether-fpa
python -m venv .venv

.venv/Scripts/python.exe -m pip install -e ".[dev]"     # Windows
.venv/bin/python -m pip install -e ".[dev]"             # Linux / macOS

.venv/Scripts/python.exe -m bellwether.build
.venv/Scripts/python.exe -m pytest -m "not requires_excel"
```

Runtime dependencies are `numpy`, `pandas`, `pyarrow` and `xlsxwriter`. The dev extra adds
`pytest`, `ruff` and `pre-commit`. There is no `make` target: the same commands run on every
platform, which is what keeps CI honest.

The Windows-only stage additionally needs Excel installed and a repo that is **not** inside a
OneDrive-synced folder — sync locks break COM automation in ways that look exactly like code
bugs.

### Layout

```
src/bellwether/
  data/          seeded synthetic transaction and master data generator
  transform/     star schema, semantic definitions, statement assembly
                 — the oracle: every financial value originates here
  workbook/      xlsxwriter generation; content, structure and skin kept separate
  excel_stage/   COM: recalc, data tables, PDF, PNG — Windows only, additive only
powerbi/         PBIP project, text format (phase 5)
docs/            charter, architecture, data contract, ADRs, phase specs
samples/         committed CSV sample of every table
tests/           acceptance assertions; Excel-dependent ones marked requires_excel
```

`data/` and `build/` are generated and gitignored. Workbooks, PDFs and PNGs are build artifacts:
never hand-edited, never committed outside a release tag. Power BI lives in PBIP text format, not
as a `.pbix` binary. Pre-commit enforces all of this.

The workbook is designed to be reskinned for a different client in a day — the theme is
declarative data that imports nothing from the model, and a test builds the entire workbook under
two themes and asserts identical values with different formats.

---

## Licence

MIT. The data is synthetic and free to use; the company is not real.

[adr1]: docs/adr/0001-beginning-balance-interest.md
[adr2]: docs/adr/0002-returns-recognised-on-an-asc-606-basis.md
[adr3]: docs/adr/0003-standard-landed-cost-with-variances.md
[adr4]: docs/adr/0004-cogs-boundary.md
[adr5]: docs/adr/0005-marketing-as-a-constrained-driver.md
[adr6]: docs/adr/0006-three-explicit-cac-definitions.md
[adr7]: docs/adr/0007-version-and-scenario-as-two-separate-dimensions.md
[adr8]: docs/adr/0008-abl-revolver-as-a-binding-constraint.md
[adr9]: docs/adr/0009-supplier-contracts-in-usd.md
[adr10]: docs/adr/0010-channel-contribution-reporting-with-corporate-costs-unallocated.md
[adr11]: docs/adr/0011-inventory-turns-relaxed-to-the-service-frontier.md
[adr12]: docs/adr/0012-category-return-rates-normalised-to-the-headline.md
[adr13]: docs/adr/0013-gross-margin-amended-to-the-generated-figures.md
[adr14]: docs/adr/0014-forecast-ledger-does-not-balance.md
[adr15]: docs/adr/0015-gm-calibration-is-a-plug.md
[adr16]: docs/adr/0016-actuals-carry-the-operating-plan-scenario.md
[adr17]: docs/adr/0017-returns-reserve-and-unwind-are-separate-accounts.md
[adr18]: docs/adr/0018-indirect-cash-flow-method.md
