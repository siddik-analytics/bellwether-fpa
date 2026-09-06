# Phase 4 — Code-generated Excel model

Goal: a driver-based three-statement model in Excel, generated from code, whose every number
originates in the semantic layer. Three statements tie, scenarios switch, sensitivity grids flex,
and the whole thing rebuilds from `python -m bellwether.build` on a machine with no Excel
installed.

Tag on completion: `v0.5-model`. **The repository flips public at this tag** (`phase-00-spec.md`
§5), so this is the first phase whose output a stranger reads without being invited.

---

## The central design problem

Two project rules pull against each other here, and the resolution has to be designed in rather
than discovered halfway through.

**The oracle rule** (`CLAUDE.md` §1): every financial value originates in Python. The workbook
consumes and presents.

**"Driver-based model with scenario switching"**: a workbook of hardcoded numbers is a *report*,
not a model. A reviewer opening it will change an assumption, see nothing move, and conclude the
Excel work is a dump of a Python result. That is the opposite of the impression this phase exists
to create.

### The resolution: every formula carries its oracle value as a cached result

`xlsxwriter.write_formula(row, col, formula, cell_format, value)` accepts a **cached result**
alongside the formula. So each modelled cell is written twice over: the formula that a user can
read, trace and flex, and the value the oracle computed, stored as the cell's cached result.

This makes both rules true at once:

- **Headless parity holds.** A workbook built on Linux with no Excel is complete and correct.
  Every cell already shows the right number; opening it in a viewer that cannot calculate still
  shows the model, not a grid of zeros.
- **The oracle still originates.** Excel does not compute the reported figures — it *reproduces*
  them. Recalculation is a verification step, not a completion step.
- **The reconciliation test becomes meaningful.** `CalculateFullRebuild` then read the values
  back: agreement to 0.01 means two independent implementations of the same specification agree.
  That test is the strongest single artifact in the repository for the hiring-manager audience,
  and it only means something because the formulas are real.

A formula written without its cached value is a defect, not a shortcut. Criterion 4.1 asserts it.

### Sensitivity grids

A native Excel Data Table computes values Excel-side, which would make Excel originate them. So
**the oracle computes the grid and the Data Table reproduces it**: the oracle evaluates the model
across the axis, those values are written as the grid's cached results, and the COM stage adds the
native Data Table over the same range. The reconciliation test then covers the grid as well.

---

## The xlsxwriter / COM boundary

Stated up front so headless parity is designed rather than discovered. Everything in the left
column runs in CI on Linux. Nothing in the right column may affect a reported number.

| Built headless by xlsxwriter | Added by the COM stage (Windows only) |
|---|---|
| Every sheet, every value, every formula **with cached results** | `CalculateFullRebuild` — recompute and prove the formulas agree |
| Number formats, conditional formats, cell styles | **Native what-if Data Tables** over the pre-computed grids |
| Named ranges and defined names | Pivot tables and slicers |
| Data validation — the scenario and version selectors | `ExportAsFixedFormat` → board pack PDF |
| Charts | `CopyPicture` → PNG exports for README and case study |
| Sheet protection, freeze panes, print setup | Reading values back for the reconciliation test |
| Documentation and assumptions sheets | |

**The test of the boundary:** delete the COM stage entirely and the workbook is still a complete,
correct, usable financial model. It loses native Data Tables, pivots, the PDF and the PNGs — it
loses nothing a reader needs to trust the numbers.

---

## Reskinnable in a day

The workbook must be re-liveried for a real client without touching model logic. Three layers,
separated at the type level so the separation cannot quietly erode:

| Layer | Owns | Changes per client |
|---|---|---|
| **Content** | Values and formulas from the semantic layer | Never — it is the model |
| **Structure** | Which sheets exist, what sits in which cell, the statement layouts | Rarely |
| **Skin** | Fonts, colours, number formats, logo, sheet order, tab colours, cover page | **Always** |

The skin is a **declarative specification** — a dataclass of tokens, not a scatter of format
objects. `xlsxwriter` binds formats to a workbook instance, so the theme is resolved into concrete
formats once at build time from a theme that is otherwise plain data.

A reskin is then editing one theme object, or supplying a second one. Criterion 4.18 asserts it
by building the whole workbook twice under two themes and checking every value is identical while
the formats differ.

---

## Order of work

### 1. Semantic layer extensions

The workbook needs three things the semantic layer does not yet expose (see W-1 and W-3 below).
These are built in `transform/`, not in the workbook, because Power BI needs the same:

- **Time series evaluation.** Metrics over a month axis by version and scenario, not a scalar for
  a filtered frame.
- **Statement assembly.** Balance sheet and cash flow, structured, from ledger accounts.
- **Sensitivity evaluation.** A metric across a driver axis, which is what the grids consume.

### 2. Workbook skeleton and theme

Sheet inventory, the theme dataclass, the format resolver, and the cover and documentation sheets.

### 3. Statements

P&L, balance sheet, cash flow — monthly and annual, with the tying relationships as real formulas
carrying cached values.

### 4. Drivers, scenarios and sensitivities

The assumptions sheet, the scenario and version selectors, and the pre-computed grids.

### 5. Reconciliation harness

The `requires_excel` test that recalculates and compares. Built now even though it only runs
locally, because it is what makes the formulas trustworthy.

---

## Acceptance criteria

| # | Criterion | How it is checked |
|---|---|---|
| **The oracle rule** | | |
| 4.1 | Every formula cell is written with a cached result from the semantic layer. A formula without one fails the build. | `tests/workbook/test_oracle_rule.py` — inspect the generated XML |
| 4.2 | No reported figure is computed only by an Excel formula. Every value exists in the semantic layer first. | `tests/workbook/test_oracle_rule.py` |
| 4.3 | The workbook is complete and correct with no Excel present — every cell shows its value | CI on ubuntu |
| 4.4 | Excel recalculation reproduces every value within 0.01 | `tests/workbook/test_reconciliation.py`, `requires_excel` |
| 4.5 | Sensitivity grid values are computed by the oracle; the Data Table reproduces them within 0.01 | `tests/workbook/test_reconciliation.py`, `requires_excel` |
| **Three statements** | | |
| 4.6 | Balance sheet balances in all 36 forecast periods, tolerance 0.01 | `tests/workbook/test_statements.py` |
| 4.7 | Cash flow closing cash equals balance sheet cash, every period | `tests/workbook/test_statements.py` |
| 4.8 | Net income flows to retained earnings; the roll-forward ties | `tests/workbook/test_statements.py` |
| 4.9 | Revenue disaggregated by channel sums to total revenue at every grain | `tests/workbook/test_statements.py` |
| 4.10 | Statements tie to the semantic layer, not merely to each other | `tests/workbook/test_statements.py` |
| 4.11 | Interest accrues on the beginning-of-period balance; iterative calculation is **off** | Inspect the workbook's calculation settings; ADR 0001 |
| **Drivers and scenarios** | | |
| 4.12 | Changing a driver cell changes downstream figures on recalculation — the model is live, not a dump | `tests/workbook/test_workbook.py` resolves the lookup by hand; the Excel recalculation is phase 5 |
| 4.13 | The scenario selector switches all four scenarios; the version selector switches Budget, Prior and Latest Forecast, with Actual always shown as history | `tests/workbook/test_workbook.py` — all nine live combinations resolved against the written file |
| 4.14 | Budget exists only under Balanced Base, and the selector handles that asymmetry without showing an empty statement as if it were a zero one | `tests/workbook/test_selectors.py` |
| 4.15 | Every driver in contract §7.5 and §7.6 appears on the assumptions sheet, sourced from config rather than typed | `tests/workbook/test_drivers.py` |
| 4.16 | Sensitivity grids cover the drivers §7.6 names as sensitivities — CAC, DSO, landed cost, wholesale share | `tests/workbook/test_sensitivity.py` |
| **Structure and skin** | | |
| 4.17 | Content, structure and skin are separate modules; the skin imports no semantic-layer symbol | `tests/workbook/test_layers.py` — import-graph assertion |
| 4.18 | Building under two themes produces identical values and different formats | `tests/workbook/test_theme.py` |
| 4.19 | No hardcoded colour, font or number format outside the theme module | grep assertion |
| 4.20 | Every sheet carries the "illustrative company, synthetic data" note | `tests/workbook/test_disclosure.py` |
| **Build** | | |
| 4.21 | `python -m bellwether.build` produces the workbook headless, exits 0, leaves a clean tree | CI on ubuntu |
| 4.22 | Workbook generation completes within 60 seconds | Timed in CI |
| 4.23 | Two runs with the same seed produce a byte-identical workbook | `tests/workbook/test_workbook.py` — SHA-256 of the file, not of extracted values |
| 4.24 | The workbook opens without repair warnings in Excel | `requires_excel` |
| 4.25 | Deleting the COM stage leaves a complete, usable model | The headless build is the deliverable CI tests |

---

## What the workbook layer makes newly problematic

Same exercise as phases 2 and 3. Each needs a decision; none is resolved here.

### W-1 · The semantic layer returns scalars, not series

`evaluate_ladder` takes a filtered frame and returns a dict of floats. A workbook column is a
**month**, so it needs 72 monthly values per metric per version per scenario — and there is no
API for that. Calling `evaluate_ladder` in a loop over 72 months × 9 combinations × 10 metrics is
6,480 filtered aggregations, which is both slow and the wrong shape.

Power BI needs exactly the same thing in phase 5, so this belongs in `transform/`, not in the
workbook.

### W-2 · There is no balance sheet or cash flow assembly

The ledger has the accounts and the forecast now balances, but nothing assembles them into
statements. Criteria 4.6–4.8 cannot be written against anything today: there is no object that
says which accounts are current assets, what order they present in, or how the cash flow is
derived — directly from cash movements, or indirectly from net income and working capital.

That last one is a **financial convention, not an implementation detail**. Direct and indirect
methods present different statements, and the contract does not state which.

### W-3 · Actuals are daily, forecast is monthly, and the boundary needs a convention

A workbook column is a month. Actual periods post daily and must be aggregated; forecast periods
are already monthly. The FY2025/FY2026 boundary is where a reader's eye goes first, and three
things need stating: whether a column can mix actual and forecast (it should not), how the model
presents the transition, and what "FY2026" means when Budget, Prior Forecast and Latest Forecast
all have an opinion about it.

### W-4 · Nine version × scenario combinations, one workbook

Budget exists only under Balanced Base (§8). A scenario selector that switches all four therefore
cannot switch Budget, so selecting Wholesale Acceleration with version Budget is a valid
selection with no data. Showing that as zeros is wrong and showing it as an error is unfriendly.

The related question is whether one workbook carries all nine combinations — nine sets of 72
monthly columns for every statement line, which is large — or whether the workbook is generated
per scenario. That is a size and usability trade-off, and it interacts with reskinnability:
a client reskin probably wants one workbook.

### W-5 · Iterative calculation must be provably off

ADR 0001 chose beginning-of-period interest specifically so the model is acyclic. A workbook is
where that could silently regress: one formula referencing a closing balance and Excel raises a
circular-reference warning, or worse, someone enables iteration to make it go away. The
calculation setting needs asserting, not assuming.

### W-6 · Contract §9 has no workbook checks

The standing acceptance checks in `CLAUDE.md` include the Excel reconciliation, but §9's
validation suite stops at the data. The workbook criteria above should be reflected there, or §9
stops being the complete list it presents itself as.

---

## Decisions needed before code

| # | Decision | Why it cannot be defaulted |
|---|---|---|
| E-a | **`xlsxwriter` as a dependency** — required, not yet installed | `CLAUDE.md` makes adding a dependency a stop-and-ask |
| E-b | W-2: direct or indirect cash flow method | A financial convention; the two present different statements |
| E-c | W-4: one workbook with all nine combinations, or one per scenario | Size and usability, and it interacts with reskinnability |
| E-d | W-3: how the actual/forecast boundary is presented | Affects every statement layout |
| E-e | Whether the COM stage lands in this phase or phase 5 | The spec is written so either works; phase 5 needs the PDF regardless |

**On E-a:** `xlsxwriter` is pure Python, cross-platform, has no compiled dependencies and is
available on Linux CI. It is the library `CLAUDE.md` already names for this layer. The
cached-result mechanism the whole design rests on — `write_formula(..., value=...)` — should be
confirmed on install before anything else is built, because if it does not work as expected the
oracle rule and a live model cannot both hold and the phase needs redesigning.

---

## Not in this phase

No Power BI, no board pack, no variance commentary. The workbook presents the model; interpreting
it is phases 5 and 6.

No new business logic. A figure the workbook needs that the semantic layer cannot produce is a
gap in the semantic layer, and the fix goes there — not into a worksheet formula, which is how a
second source of truth starts.
