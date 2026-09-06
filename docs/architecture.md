# Architecture

> Illustrative company, synthetic data.

## Shape

A one-way pipeline. Each layer consumes the one above it and never writes back.

```
   src/bellwether/data/          seeded synthetic generator
              |                  transaction ledger + master data
              v
   src/bellwether/transform/     star schema, semantic metric definitions
              |                  facts, dimensions, date spine
              v
   src/bellwether/oracle/        THE MODEL - every financial value originates here
              |
      +-------+--------+------------------+
      |                |                  |
      v                v                  v
  workbook/        powerbi/           board pack
  (xlsxwriter)     (PBIP/TMDL)        (phase 5)
      |
      v
  excel_stage/     COM: recalculate, verify, package  [Windows only, additive only]
```

Cycles are the failure mode this shape exists to prevent. Power BI does not define a metric
the transform layer does not have; the workbook does not compute a figure the oracle did not
produce; the Excel stage does not write a value at all.

## The oracle rule

`src/bellwether/oracle/` is the single source of truth for every financial value in the
project. It is pure Python, deterministic, and depends on nothing but the warehouse.

Everything downstream is a *consumer*. The workbook renders oracle output into cells. Power
BI aggregates warehouse facts using definitions the transform layer owns, and its key
measures are reconciled back to the oracle by test. The board pack is composed from oracle
output.

The practical test: if a number appears anywhere in a deliverable and you cannot point at the
oracle function that produced it, that is a defect — regardless of whether the number happens
to be correct. Correct-by-accident does not survive a change.

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
  data/           seeded synthetic generator                    phase 1
  transform/      star schema, semantic definitions             phase 2
  oracle/         model logic - source of truth                 phase 3
  workbook/       xlsxwriter generation, cross-platform         phase 3
  excel_stage/    COM: recalc, tables, PDF, PNG (Windows)       phases 3, 5, 6
powerbi/          PBIP project - TMDL + report JSON             phase 4
docs/             charter, architecture, data contract, ADRs, phase specs
tests/            acceptance assertions; Excel ones marked requires_excel
data/             generated - gitignored
build/            artifacts - gitignored except at release tags
```
