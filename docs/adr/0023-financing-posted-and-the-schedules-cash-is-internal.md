# ADR 0023 — The forecast's financing is posted, and the schedule's cash is internal only

- **Status:** Accepted
- **Date:** 2026-09-06
- **Phase:** 6 (board pack), closing a defect carried from phase 5

## Context

`transform.forecast_ledger.post_financing` was written in phase 3, exported in `__all__`, and
**never called**. For three phases the forecast ledger carried no financing at all:

| | |
|---|---|
| `fact_financing_monthly` carried | $370,351 interest, $245,310 unused line fees, revolver drawn to $2.0M |
| `fact_gl` posted to accounts 7000, 7010, 2500 | nothing, in any period, in any scenario |

Four consequences followed, and the fourth is the one this ADR exists for:

1. **Net Income equalled EBITDA in every period of every scenario.** The metric was defined, the
   DAX measure was generated, and it was structurally zero.
2. **The balance sheet showed no debt** for a company whose central question is whether it can
   fund itself.
3. **The cash flow's interest line was zero** — in the statement ADR 0018 chose specifically for
   its ability to explain the covenant.
4. **`financing.py` remained a second source of truth**, which is precisely what ADR 0014 and
   phase 3's D-1 claimed to have removed.

The trial balance netted to zero throughout. It netted to zero *because the entries were absent*.

## Decision

**Post the schedule's interest, fees and revolver movements to the ledger**, seeded with the
opening drawn balance so the first month's movement is not lost.

**Stop publishing the schedule's `cash` column.**

The second decision needs stating precisely, because two very different things could be described
the same way. What happened is **not** that a disagreeing number was deleted:

- `financing.run` **still computes an internal cash roll-forward.** It has to: the decision to
  draw or repay in a given month depends on the cash position at that moment, so the roll-forward
  is how the debt gets priced at all. That code is unchanged and still runs.
- **The ledger is authoritative for cash.** Every consumer that needs a cash figure derives it
  from posted balances.
- **The schedule's cash is now internal to `financing.run` and reaches no published table.** It
  is a local variable in a loop, not a column anyone can read.
- **The divergence is unpublished, not resolved.** The two still model accrual-to-cash timing
  differently and would still disagree by between $250k and $1.7M depending on the combination
  if both were exposed. Nothing has reconciled them.

`tests/transform/test_financing_posted.py::test_the_schedules_cash_column_has_no_consumers`
asserts the column is absent from the published fact and that no module reads it, so a future
caller cannot quietly reintroduce it.

## Rationale

**Why post rather than reconcile the two.** Reconciling would mean maintaining accrual-to-cash
timing in two places — the ledger's posted movements and the schedule's roll-forward — and
keeping them equal forever. That is the arrangement D-1 exists to end. One authority, and the
other computes only what it needs internally to do its own job.

**Why the covenant figures did not move, and why that is the interesting part.**

The phase 6 spec predicted that fixing D-1 would move cash, the borrowing base and every covenant
figure. It said so in bold, and it was **wrong**. Every figure is unchanged:

| Scenario | Min excess availability | First breach |
|---|---:|---|
| Balanced Base | $745,892 | — |
| Wholesale Acceleration | $0 | 2028-05 |
| Consolidation | $1,556,475 | — |
| DTC Recovery / Margin | $1,181,021 | — |

`financing.run` had **always** deducted interest and unused fees from its own cash roll-forward.
The schedule priced the debt correctly from the day it was written. Only the ledger did not know
about it, so posting adds entries the schedule had already assumed and cannot change anything the
schedule produced.

**That is a subtler failure than the usual second source of truth, and it deserves recording
next to phase 3's.** Phase 3's D-1 (ADR 0014) was the familiar shape: two computations that
*could* disagree, and the fix was to make one of them the only one. This is the shape where the
second source is **right** — and it is still a problem, because:

- **Nothing forced the two to meet.** They agreed by construction and by nobody's checking. A
  change to either would have broken the agreement silently, and no test would have failed,
  because no test compared them.
- **The disagreement that did exist was invisible.** The ledger was missing $615,661 of expense
  and an entire liability, and every balance check passed. Absence does not fail a tie test; it
  fails a completeness test, and there was none.
- **Correctness is not the property being protected.** The reason to have one source of truth is
  not that two sources are wrong — often neither is — but that two sources have no mechanism
  keeping them equal. "It happens to agree today" is the state a second source of truth is
  always in, right up until it is not.

So the value of D-1 was never a corrected number. It was converting an agreement that held by
luck into one that holds by construction, and adding the test that would notice if it stopped.

## Alternatives considered

**Leave it, since the covenant figures were right anyway.** Tempting once the figures turned out
not to move, and it was the wrong instinct for the reason above: the figures were right and
nothing was keeping them right. It would also have left Net Income structurally equal to EBITDA
and a funding-constrained company showing no debt, which is a defect a reader would find in the
board pack rather than in a test.

**Reconcile the ledger's cash to the schedule's.** Rejected: two implementations of accrual-to-cash
timing, kept equal by hand, is what this ADR ends.

**Publish the schedule's cash with a caveat in the column description.** Rejected. A caveat is
not a mechanism, and a published column is read by whoever finds it convenient regardless of what
its description says.

## Consequences

The P&L carries $615,661 of financing cost it could not previously see, so Net Income differs
from EBITDA in 324 of 360 period/version/scenario rows. Anything quoting Net Income for a
forecast period now shows a different figure from EBITDA — correctly, for the first time.

**No document needed restating.** The covenant figures the contract, README, charter, ADR 0008,
ADR 0018 and `phase-06-carried.md` quote are unchanged, and criterion 6.8's sweep found nothing
to fix. That is a better outcome than the spec expected and a worse one to assume next time.

`post_financing` now takes `opening_drawn`. Without it the first month's draw was dropped
entirely — a movement is a difference, and the first row had nothing to differ from — which
understated the revolver balance for the whole horizon.

The revolver test compares a **completed monthly grid**, not the months that happened to post. A
balance checked only where it changed is not a balance that has been checked, and 236 of the 324
forecast months have no revolver movement in them.
