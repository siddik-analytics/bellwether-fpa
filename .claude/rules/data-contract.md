---
paths:
  - "src/bellwether/data/**"
  - "src/bellwether/transform/**"
  - "tests/data/**"
---

# Data layer

The entity list, grain declarations and business rules live in `docs/data-contract.md`.
Read it before changing anything here. This file holds the conventions that document assumes.

Everything downstream inherits from the data contract. Getting a grain wrong means rebuilding
the oracle, the workbook and the Power BI model — so a change to the contract is a documented
decision, not an implementation detail.

## Determinism

The generator is seeded and reproducible. Running it twice with the same seed produces
byte-identical output. This is what makes acceptance criteria testable at all.

- The seed lives in config, not hardcoded at a call site
- No `datetime.now()`, no unseeded RNG, no dependence on dict ordering or filesystem order
- Regenerating data must never change a committed test expectation

## Realism

The point of synthetic data is that it behaves like a real business, not that it exists.
Generated activity should carry the structure a real ledger has: seasonality, month-end and
quarter-end concentration, returns arriving after the originating sale, credit terms producing
a real receivables ageing profile, occasional corrections and reversals, headcount changing in
steps rather than smoothly.

Data that is too clean is worse than no data — it makes the dashboards look fabricated, which
is precisely the impression the project exists to avoid.

Do not, however, invent business rules. If realistic behaviour requires a convention that
`docs/data-contract.md` does not state, stop and ask. That convention is domain expertise and
it belongs in the contract, decided deliberately.

## Grain and keys

- Every fact table declares its grain in a module docstring, in one sentence, and a test
  asserts uniqueness at that grain
- Surrogate integer keys on dimensions; natural keys retained as attributes
- Dimension changes follow the SCD type stated in the contract — do not silently overwrite
- One date spine covering the full actual and forecast horizon, contiguous, no gaps

## Conventions

- Currency: single reporting currency, minor units stored as integers where precision matters
- Rounding applied at presentation, never in intermediate calculation
- Version (actual / budget / prior forecast / latest forecast) and Scenario (the strategic
  alternatives) are two separate dimensions, never a separate table or column suffix, and never
  collapsed into one dimension — see ADR 0007
- Periods are closed-open date ranges; document the convention once and hold to it

## Validation suite

The generator is not done until validation passes. These run in CI:

- Grain uniqueness on every fact table
- Referential integrity — zero orphan keys across every fact-to-dimension join
- Date spine contiguous and covering every fact date
- Trial balance sums to zero by period
- Subledger totals tie to the corresponding control account
- Value ranges and sign conventions are plausible per column, not just non-null

Add a validation before adding the feature that needs it.
