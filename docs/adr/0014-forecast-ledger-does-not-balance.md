# ADR 0014 — The forecast ledger does not balance (resolved in phase 3)

- **Status:** Resolved in phase 3
- **Date:** 2026-09-06
- **Phase:** raised in 2 (generator), **owned by phase 3 (transformation layer)**

## The defect

Actual periods post as double entry. `ledger.Journal.post` refuses an unbalanced journal, so the
trial balance nets to zero for every actual month, and `test_trial_balance_is_zero_every_period`
asserts it.

Forecast periods do not. `forecast.to_ledger` maps seven P&L lines and a COGS line onto GL
accounts and stops there. There are no balance-sheet postings — no cash, no receivables, no
inventory, no payables, no revolver — so the forecast portion of `fact_gl` carries only one side
of each entry and cannot net to zero.

The test scopes to `version_name == "Actual"` and says so, but contract §9 check 11 does not
make that distinction. As it stands the contract claims something the data does not support.

## Decision

**Fix it in phase 3. Do not narrow check 11 to actuals.**

Narrowing the check is the cheap option and it was rejected. The reason is not tidiness:

A forecast that does not produce a balance sheet cannot derive cash flow, working capital or the
borrowing base **from the ledger**. Those figures have to come from somewhere, and today they
come from `financing.py`, which computes working capital and the borrowing base from its own
inputs. That makes `financing.py` a **second source of truth** for quantities the ledger should
own — precisely the failure the project's first non-negotiable rule exists to prevent. The two
agree today because the same drivers feed both. They will not agree the first time one changes.

There is also an audience argument. "Does your forecast balance?" is a standard interview
question for a financial model, and "only the actuals do" is a weak answer that invites exactly
the follow-up it deserves. This project's premise is that the repository is the artifact.

## Why phase 3 and not now

The forecast is currently monthly aggregates computed directly from scenario drivers. Balancing
it means posting the balance-sheet side of every movement — a receivable when revenue is
recognised, inventory when purchases land, a payable against them, cash on settlement — which
means the forecast needs the same movement-level structure the actuals already have.

That structure is what the phase 3 transformation layer builds. Doing it now would mean writing
a second, throwaway version of it inside `forecast.py`, then deleting that in phase 3.

## What integrating actually caught

Recorded because it is the evidence that this decision was right, and because "we integrated and
it immediately found something" is a weaker claim when made in the abstract than when made with
the number attached.

Balancing the forecast meant deriving working capital from the ledger rather than from scenario
drivers. The first attempt to do that surfaced a defect that had been latent since phase 2:

| | |
|---|---|
| Inventory control account (GL 1200) | $7.578M |
| Inventory subledger (fact table) | $5.899M |
| Difference | **$1.679M** |

Two causes. Purchase-order receipts were valued at a flat $15 per unit while cost of sales was
relieved at effective-dated per-SKU cost, so every receipt posted at the wrong amount. And the
simulation seeds day-one stock that the ledger never received, so the control account was short
by the value of the opening position.

**Neither was detectable while the forecast did not read the ledger.** Nothing else consumed the
inventory control account: the actuals' trial balance still netted to zero, because the error was
in the *amount* of a balanced pair rather than in the pairing. The covenant results looked
right because they came from `financing.py`, which never touched the ledger at all. A second
source of truth does not disagree with the first until something forces them to meet.

That is the argument for the decision, made concrete. Had check 11 been narrowed to actuals
instead — the cheap option this ADR rejected — the forecast would have kept computing a
borrowing base from drivers, the control account would have stayed $1.7M wrong, and the first
symptom would have appeared in phase 5 with a board pack attached to it.

The fix also produced a structural change rather than a third patch. This was the third instance
of the same bug shape — an aggregate standing in for a per-SKU lookup — so the lookup now has no
scalar path at all (`inventory.LandedCost`), and a caller has to say which SKU and which date.

## Scope of the fix

1. Forecast posts full double entry, including balance-sheet movements, per version and scenario.
2. `financing.py` derives receivables, inventory and payables **from the ledger** rather than
   from scenario drivers, leaving it responsible only for the facility rules.
3. Check 11 then applies to every period of every version and scenario, unamended.
4. A regression test asserts the forecast trial balance nets to zero, alongside the existing
   actuals test.

## Interim position

Until then, `financing.py` is the source of truth for forecast working capital and the borrowing
base, and this is stated where it matters rather than left to be discovered:

- `test_trial_balance_is_zero_every_period` filters to `Actual` and carries a comment saying why.
- Contract §9 check 11 is annotated with a pointer to this ADR.
- The phase 2 spec carries a known-defects section naming this and its owner phase.

The covenant results in §7.6 and the four-way scenario comparison are unaffected: they are
computed from the financing schedule, which is internally consistent. What is missing is that
the ledger cannot independently reproduce them.


## Resolution

Closed in phase 3, as owned. `transform/forecast_ledger.py` posts the forecast through the same
double-entry journal as the actuals, including an opening balance sheet, and check 11 was never
narrowed. `tests/transform/test_transform.py::test_forecast_ledger_balances_every_version_and_scenario`
holds it shut for all ten version and scenario combinations, and the balance sheet ties to
$0.000000 across all 360 rows.
