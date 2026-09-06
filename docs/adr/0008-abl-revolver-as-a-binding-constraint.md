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

**One financial covenant: minimum excess availability of $250k**, tested monthly throughout the
horizon. Internal minimum cash of $500k is a management policy, not a covenant.

**Funding.** A **$3.50M equity raise in June 2024** sits behind the facility. Northlake therefore
enters the forecast with the revolver undrawn and roughly $1.5M of cash, having funded the FY2025
loss and working capital build from the raise rather than from debt.

*Sized at $3.25M when this ADR was first written. ADR 0011 relaxed inventory turns to the
achievable service frontier, which lifted FY2025 average inventory from $1.39M to $2.02M; the
extra cash that ties up exceeds the extra borrowing base it creates, because inventory advances at
50%. Balanced Base breached in June 2028 at $3.25M and holds at $3.50M.*

### Why there is no fixed charge coverage covenant

Two earlier drafts of this decision carried one, and both were wrong.

The first made the FCCR spring when excess availability fell below $300k — the conventional
structure, and wrong for this company at this point in its life.

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

The second draft made applicability conditional on TTM EBITDA turning positive, which fixes the
inception problem and is what a lender would actually document for a borrower in this position.
That draft was also removed, for a different reason: **it never becomes applicable.**

A 36-month projection of all three scenarios shows TTM EBITDA negative in every month of every
scenario. Balanced Base reaches −1.8% by FY2028, Wholesale Acceleration −1.0%, DTC Recovery −1.4%.
The best case in the best scenario in the final month of the horizon is still a loss. A springing
covenant that never springs is not a conservative safeguard; it is unexercised machinery that
implies a control the model does not actually apply, and a reviewer who traces it finds nothing
behind it.

So the coverage covenant is gone, and **minimum excess availability is the sole financial
covenant**. That is the right answer on the merits as well as the modelling: an asset-based lender
to a loss-making borrower protects itself through the borrowing base and an availability floor, and
tests coverage only when there is coverage to test.

If a future version of the plan reaches positive TTM EBITDA within the horizon, reintroducing a
coverage covenant becomes worth reconsidering — and validation check 26 exists to force that
conversation by asserting the condition that currently makes it unnecessary.

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
