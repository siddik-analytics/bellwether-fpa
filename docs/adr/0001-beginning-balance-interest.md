# ADR 0001 — Interest accrues on the beginning-of-period debt balance

- **Status:** Accepted
- **Date:** 2026-09-05
- **Phase:** 0 (scaffold); binds from phase 3 onward

## Context

A three-statement model contains a natural circular reference. Interest expense depends on
the debt balance; the debt balance depends on the cash position; the cash position depends on
net income; net income depends on interest expense. Left alone, that loop does not resolve.

Spreadsheet practice usually resolves it by enabling iterative calculation, so Excel converges
on a fixed point over successive passes. That works, and it is what most models do.

It does not work *here*, because of a constraint this project has and a typical model does
not: `python -m bellwether.build` must produce a complete and correct workbook on Linux with
no Excel installed, and the Excel stage may only add to what the headless build produced. A
model whose values are only correct after Excel iterates is a model whose correctness depends
on Excel.

It also breaks the strongest test in the repository. The reconciliation test opens the
generated workbook, forces a full rebuild, reads the values back and asserts agreement with
the Python oracle to 0.01. If the workbook resolves a circular reference by iterating to a
convergence tolerance while the oracle does not, the two implementations are no longer
computing the same thing, and any disagreement is ambiguous: a real defect and a convergence
artifact look identical.

## Decision

**Interest is calculated on the debt balance at the beginning of the period.**

Draws and repayments within a period do not accrue interest until the following period. The
same rule applies to interest income on cash balances. The convention is stated once, in the
data contract, and applied identically in the oracle, the workbook and Power BI.

Consequently:

- The model is acyclic. Each period is computed in a single forward pass.
- Iterative calculation stays **off** in the workbook. A change that would require enabling
  it is a change that must be raised, not made.
- The headless build and the Excel-recalculated build are arithmetically identical, which is
  the precondition for the reconciliation test meaning anything.

## Alternatives considered

**Enable iterative calculation in Excel.** The conventional answer. Rejected: it makes
correctness depend on Excel, which contradicts the headless parity rule, and it converts the
reconciliation test from an exact comparison into a comparison against a convergence
tolerance — weakening the one artifact the project most relies on.

**Solve the circularity numerically in Python and write the converged results as values.**
This keeps the headless build authoritative and the workbook exact. Rejected for phase 3 as
disproportionate: it adds a solver, a convergence policy and a failure mode (non-convergence
under a stress scenario) to buy an accuracy improvement that is immaterial at this company's
scale. Worth revisiting only if the model later carries a revolver sized such that
within-period interest genuinely moves the answer.

**Average of opening and closing balances.** More accurate than opening balance, and it is
what a careful analyst would reach for. Rejected: closing balance depends on interest, so
this reintroduces exactly the circularity being removed. It is only available with a solver,
which puts it behind the alternative above.

## Consequences

Interest expense is slightly understated in periods of rising debt and slightly overstated in
periods of falling debt. At the debt levels this business carries the effect is immaterial to
every reported metric, and it is a *systematic* bias rather than noise — the same direction
in every period, which makes it easy to reason about and easy to disclose.

The convention is documented in the data contract and stated in the board pack's basis of
preparation. A reviewer who spots it should find that it was chosen rather than defaulted
into, which is the substance of this record.

If the model later needs within-period accuracy, the path is the solver alternative above,
with a new ADR superseding this one — not switching on iterative calculation.
