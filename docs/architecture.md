# Architecture

> Illustrative company, synthetic data.

## Shape

A one-way pipeline. Each layer consumes the one above it and never writes back.

```
   src/bellwether/data/          seeded synthetic generator
              |                  transactions, master data, financing, forecast
              v                  every value posted through a double-entry ledger
   src/bellwether/transform/     star schema, semantic definitions, statements
              |                  sensitivity grids, channel allocation
              |
              |    data/ + transform/ = THE ORACLE
              |    every financial value in the project originates in one of them
              |
      +-------+--------+------------------+
      |                |                  |
      v                v                  v
  workbook/        powerbi/           board pack
  (xlsxwriter)     (PBIP/TMDL)        (phase 6)
      |
      v
  excel_stage/     COM: recalculate, verify, package  [Windows only, additive only]
```

Cycles are the failure mode this shape exists to prevent. Power BI does not define a metric
the semantic layer does not have; the workbook does not compute a figure the oracle did not
produce; the Excel stage does not write a value at all.

## The oracle rule

**Python originates every number, Excel reproduces it, and the reconciliation test proves the
two agree.**

### The oracle is a property, not a package

This project originally reserved a directory, `src/bellwether/oracle/`, for "the model". It was
never populated, and the reason is worth recording rather than quietly deleting: **the model is
not separable from the thing that generates it.** A double-entry ledger that posts a returns
reserve is already computing a financial value. So is a borrowing-base calculation, a
landed-cost standard, a forecast plan. Extracting "just the model" from those would have meant
either a package that re-derived what the generator already knew, or a generator demoted to a
data dump with the accounting pulled out of it. Both are worse than the system that emerged.

So the oracle is defined by *what a module does*, not where it sits. These modules originate
financial values, and together they are the oracle:

| Module | What it originates |
|---|---|
| `data/dimensions.py` | master data: salaries, discount rates, payment terms, MSRP |
| `data/actuals.py` | transactions: order lines, invoice lines, returns |
| `data/inventory.py` | landed cost standards, purchase orders, stock positions |
| `data/stockouts.py` | suppressed demand — revenue that did not happen |
| `data/forecast.py` | the 36-month plan, across four scenarios |
| `data/financing.py` | revolver drawings, borrowing base, covenant headroom |
| `data/ledger.py` | the double-entry journal every value above is posted through |
| `transform/near_term.py` | near-term cost of sales, derived from units |
| `transform/forecast_ledger.py` | the forecast, posted through the same journal |
| `transform/allocation.py` | the channel mapping behind contribution reporting |
| `transform/semantic.py` | the metric ladder, channel contribution, variance |
| `transform/statements.py` | the three statements, and the ties between them |
| `transform/sensitivity.py` | driver sensitivity grids |

`transform/star.py` is the exception inside those two packages: it assigns keys, conforms
dimensions and joins. It restructures values, it does not originate them.

Everything else is a *consumer*. `workbook/` renders oracle output into cells. Power BI
aggregates warehouse facts using definitions the semantic layer owns, and its key measures are
reconciled back by test. `excel_stage/` verifies and packages. The board pack is composed from
oracle output.

### What makes the rule testable

Not the directory structure — a rule enforced only by where files live is enforced by nothing.
What makes it testable is that **a second implementation exists to disagree with it**. The
workbook carries every reported figure twice: as an Excel formula a reader can trace, and as
the oracle's value, stored in the same cell as its cached result. The headless build writes
both. Excel recalculation then either reproduces the cached value or it does not, and the
`requires_excel` tests assert agreement to 0.01.

The practical test for a human: if a number appears anywhere in a deliverable and you cannot
point at the Python that produced it, that is a defect — regardless of whether the number
happens to be correct. Correct-by-accident does not survive a change.

A sensitivity grid is the easiest place to break this by accident, because it looks like
presentation. It is not: every cell is a modelled EBITDA outcome. `transform/sensitivity.py`
computes the grids, and the Excel stage lays a native Data Table over the same range — so the
reader gets a live table over numbers Excel did not originate.

### Why this direction

The alternative — the common one — is to let each tool own its own logic: formulas in the
workbook, DAX in Power BI, a spreadsheet somewhere for the board pack. It is faster to start
and it fails in a specific, well-known way: the three disagree, nobody can say which is
right, and the disagreement is discovered by a board member rather than by a test.

Centralising in Python costs more up front and buys three things: the definitions are
testable, they survive a tool change, and any two consumers can be cross-checked
mechanically.

## The Windows / COM boundary

This is the only platform-specific part of the system, and the boundary is drawn hard.

| | Headless build | Excel stage |
|---|---|---|
| Command | `python -m bellwether.build` | `python -m bellwether.excel_stage` |
| Platform | Any. CI runs it on Linux. | Windows, with Excel installed |
| Runs in CI | Yes | No |
| May originate a value | Yes — this is where they come from | **Never** |
| May be required for correctness | Yes | **Never** |

The headless build must produce a **complete and correct** workbook on Linux with no Excel
present. Everything the Excel stage does is additive: native data tables, pivot tables and
slicers, full recalculation, `ExportAsFixedFormat` to PDF, `CopyPicture` to PNG.

CI enforces this mechanically rather than by discipline. Because the Linux job has no Excel,
any change that makes correctness depend on the COM stage fails there — which is the point of
running CI on Linux for a Windows-authored project.

Detailed COM conventions — instance hygiene, absolute paths, `CalculateFullRebuild`, retry on
transient RPC errors — live in `.claude/rules/excel-com.md`.

## The bus matrix

Every fact against every conformed dimension. Publishing it is what shows whether the schema
actually conforms — a dimension two facts need and neither has is invisible in code and obvious
here.

| Fact | channel | customer | date | department | gl_account | location | product | promotion | scenario | supplier | version | wholesale_account |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `fact_dtc_order_line` | x | x | x |  |  |  | x | x | x |  | x |  |
| `fact_wholesale_invoice_line` | x |  | x |  |  |  | x |  | x |  | x | x |
| `fact_return_line` | x | x | x |  |  |  | x |  |  |  |  | x |
| `fact_inventory_daily` |  |  | x |  |  | x | x |  |  |  |  |  |
| `fact_purchase_order_line` |  |  | x |  |  |  | x |  |  | x |  |  |
| `fact_stockout` |  |  | x |  |  |  | x |  |  |  |  |  |
| `fact_gl` | x |  | x | x | x |  |  |  | x |  | x |  |
| `fact_forecast_monthly` | x |  | x |  |  |  |  |  | x |  | x |  |
| `fact_financing_monthly` |  |  | x |  |  |  |  |  | x |  |  |  |

The matrix is generated from `transform.star.BUS_MATRIX`, and a test asserts the built schema
matches it, so the document cannot drift from the code.

Two conventions hold throughout.

**No null foreign keys.** Every dimension carries an explicit "Not applicable" member at key 0
for facts that legitimately lack a value — a wholesale invoice has no customer, a payroll journal
has no product. A null degrades silently in a BI tool; an explicit member is countable, and a
count of it is a data-quality measure.

**Actuals carry the operating plan scenario**, not "Not applicable" (ADR 0016). Contract §3.3
defines performance variance as a same-scenario comparison, and an N/A member would make every
variance in the model cross a dimension boundary the contract says to hold fixed.

`fact_gl` reaches product and customer through a **bridge**, not through keys of its own. Most
postings have no single product — payroll, accruals and interest each have none — so widening the
ledger would break its declared grain to serve the minority of rows that do.

## Verification strategy

Three independent checks, in increasing strength:

1. **Data validation** (CI). Grain uniqueness, referential integrity, contiguous date spine,
   trial balance summing to zero, subledger tying to control account.
2. **Model invariants** (CI). Balance sheet balances every period; cash flow closing cash
   equals balance sheet cash; disaggregated revenue sums to total at every grain.
3. **Cross-implementation reconciliation** (local Windows only, marked `requires_excel`).
   Open the generated workbook, force a full rebuild, read the values back, and assert
   agreement with the oracle to 0.01.

The third is the one that carries weight. It is two independent implementations of the same
specification disagreeing loudly when either drifts, which no amount of single-implementation
testing gives you.

## Determinism

The generator is seeded; the seed lives in config, not at a call site. No `datetime.now()`,
no unseeded RNG, no reliance on dict or filesystem ordering. Running the build twice with the
same seed produces byte-identical data.

This is not tidiness. Without it, no acceptance criterion in the project is testable, because
every expected value would be a moving target.

## Circularity

Interest is computed on the **beginning-of-period** debt balance, so the model has no
circular reference and needs no iterative calculation. This keeps the headless build exactly
equivalent to the Excel-recalculated build — which is what makes the reconciliation test
meaningful in the first place. See `docs/adr/0001-beginning-balance-interest.md`.

Enabling iterative calculation is not a change to be made quietly; it invalidates the parity
guarantee above.

## Repository layout

```
src/bellwether/
  paths.py        absolute path constants - COM does not resolve relative paths
  build.py        headless build entry point
  data/           seeded synthetic generator                    phase 2
  transform/      star schema, semantic definitions,            phase 3
                  statements, sensitivity
  workbook/       xlsxwriter generation, cross-platform         phase 4
  excel_stage/    COM: recalc, tables, PDF, PNG (Windows)       phases 5, 6
powerbi/          PBIP project - TMDL + report JSON             phase 5
docs/             charter, architecture, data contract, ADRs, phase specs
tests/            acceptance assertions; Excel ones marked requires_excel
data/             generated - gitignored
build/            artifacts - gitignored except at release tags
```
