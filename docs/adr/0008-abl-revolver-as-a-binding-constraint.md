# ADR 0008 — ABL revolver with a borrowing base, treated as a binding constraint

- **Status:** Accepted
- **Date:** 2026-09-05
- **Phase:** 1 (data contract)

## Context

Northlake consumed roughly $1.5M of cash in FY2025 — an EBITDA loss of about $750k and an
incremental working capital absorption of about $720k, split between a $400k inventory build and a
$320k increase in receivables. That has to be funded, and how it is funded determines whether the
central question of the board pack can be answered at all.

That question, from the Wholesale Acceleration scenario, is: **how much wholesale growth can
Northlake finance before the incremental revenue creates an unacceptable cash requirement?**

A model in which debt is a balancing figure cannot answer it. The plug always balances, so the
answer is always "as much as you like", and the scenario silently becomes an argument for
unlimited expansion.

## Decision

**A $2.0M committed asset-based revolver**, alongside equity already raised.

**Borrowing base:** 85% of eligible wholesale accounts receivable, plus 50% of eligible
finished-goods inventory subject to a **$1.0M inventory advance sublimit**, less lender reserves.

**AR eligibility:** balances over 90 days past due are ineligible; a **25% single-account
concentration cap**; specific disputed amounts and known credits ineligible; a general **dilution
reserve of ~2%** of otherwise eligible AR, able to increase if trailing dilution deteriorates.

**Inventory eligibility** excludes or reserves against obsolete, damaged, aged and
weak-liquidation-value stock.

**Pricing:** SOFR + 3.50%, with a 0.50% unused-line fee. **SOFR is an explicit monthly model
input**, never an embedded all-in rate.

**Covenants — two, with different applicability:**

1. **Minimum excess availability of $250k**, tested monthly. The live financial covenant throughout
   the forecast horizon.
2. **Fixed charge coverage ratio of 1.10x** trailing twelve months, **springing: applicable only
   once TTM EBITDA is positive**.

Internal minimum cash of $500k is retained as a **management policy, not a covenant**.

### Why the FCCR springs on profitability rather than on availability

The first draft of this decision made the FCCR spring when excess availability fell below $300k,
which is the conventional structure and is wrong for this company at this point in its life.

Northlake's FY2025 EBITDA is **negative $859k**. A fixed charge coverage ratio compares EBITDA less
unfinanced capital expenditure and cash taxes against fixed charges — interest, scheduled principal,
and in most formulations distributions. With a negative numerator the ratio is negative, and no
denominator makes it reach 1.10x. The test therefore fails **in month one of the forecast, in every
scenario and every version**, and continues failing until the business turns profitable.

That is not a constraint. A covenant breached from inception forces one of two modelling
distortions: a permanent waiver assumption, which makes the covenant decorative, or a model in
which every scenario reports an event of default from the start, which destroys the covenant's
value as a signal precisely when the reader most needs one. Either way the FCCR stops discriminating
between good and bad outcomes, which is the only reason to model a covenant at all.

Making applicability conditional on TTM EBITDA turning positive resolves this and is also what a
lender would actually document for a borrower in this position. Coverage covenants are set against
a business that has fixed charges it can plausibly cover; before that point, the lender protects
itself through the borrowing base and an availability floor, not through a coverage ratio.

The availability covenant does the work in the meantime, and does it well: it is tested against the
borrowing base, which already contracts as inventory ages and receivables stretch.

**Consequence for the model:** the month the FCCR first becomes applicable is a reported output,
not an assumption. Under Balanced Base it is the first month TTM EBITDA turns positive, expected
within FY2027, and it is asserted as a frozen regression value once the model is built. From that
month onward the 1.10x test binds normally.

**Five separately reported lines:** facility commitment, borrowing base, revolver drawn, excess
availability, and minimum availability / covenant status.

**Capacity binds.** Where the borrowing base is exhausted, the model surfaces the **first
funding-gap month and the additional capital required**. It does not draw beyond availability.

## Rationale

The borrowing base is deliberately constructed from the same assets the central tension degrades.
Ageing inventory becomes ineligible. Stretched receivables and the concentration cap reduce
availability. The dilution reserve rises with the very deductions that already reduce wholesale
revenue.

Availability therefore contracts at precisely the moment the business most needs it, which is what
an asset-based facility actually does and what a term loan would not reproduce.

The concentration cap is the sharpest instance. Northlake's largest account is 24% of wholesale
revenue against a 25% cap. Growth in that account — the single biggest contributor to FY2025
wholesale growth — begins consuming borrowing availability rather than creating it. That is a
genuine, quantified strategic constraint arising from the data rather than from narrative.

## Alternatives considered

**Term loan or venture debt.** Fixed amortisation, simpler to model, still generates interest
expense. Rejected because debt capacity would be disconnected from working capital, losing the
feedback loop in which a bad inventory quarter also reduces borrowing availability. That loop is
the most interesting thing about the capital structure.

**Equity funding only, no debt.** Simplest of all. Rejected because it leaves ADR 0001 academic —
beginning-of-period interest on an empty debt line decides nothing — removes any financing
constraint on Scenario 2, and turns the board question from "can we fund this" into an
unconstrained preference.

**A revolver modelled as an uncapped plug.** Rejected for the reason given above: it makes the
scenario unfalsifiable.

## Consequences

This makes **ADR 0001 load-bearing**. Interest accrues on a real, moving revolver balance, so the
beginning-of-period convention has measurable consequences rather than being a technicality.

The model must compute a borrowing base from eligibility rules at period grain, which means AR
ageing and inventory ageing are required inputs to the financing module — not just to the working
capital note. Inventory ageing now affects the P&L twice: through the reserve, and through interest
on the borrowings that ageing makes unavailable.

The funding gap is a reported output with a **date**. "Northlake runs out of availability in month
14 of the acceleration case and needs $X" is a board-grade sentence that the model produces rather
than a human asserting.

Covenant status must be computed and reported even when comfortably met, because a springing test
only matters in the states where it is most likely to be breached.

Two covenants means two reported statuses, and they are not interchangeable. Availability binds
throughout; the FCCR binds only after profitability, and reporting it as "passing" during the loss
years would be misleading — it is *not applicable*, which is a different statement and must be
presented as one.

That the FCCR only becomes live once EBITDA turns positive has a slightly counter-intuitive
consequence worth stating in the board pack: recovering to profitability *introduces* a covenant
rather than removing one. The plan should not be surprised by it.
