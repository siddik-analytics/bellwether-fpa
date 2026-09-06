# ADR 0002 — Returns recognised on an ASC 606 basis

- **Status:** Accepted
- **Date:** 2026-09-05
- **Phase:** 1 (data contract)

## Context

Northlake's DTC return rate is 7% of net merchandise sales, with most returns arriving inside 30
days and a mean lag of about 18 days. Wholesale returns are 1.5% of net wholesale sales at a 45-90
day lag.

A mean lag shorter than a reporting period is not a rounding problem. It means every month closes
with a known population of sales whose returns have not yet arrived. In a business with flat
month-on-month sales the effect roughly cancels. Northlake is not that business: Black Friday and
Cyber Monday alone are about 12% of annual DTC revenue, concentrated in November, with the
resulting returns landing in December.

Recording returns only as they are processed would therefore make November look materially better
than it was and December materially worse, in the two months the board pays most attention to. The
distortion is largest exactly where the reader is least tolerant of it.

## Decision

**Revenue is recognised net of expected returns.** A **refund liability** and a corresponding
**right-of-return asset** (recoverable inventory at cost) are carried on the balance sheet and
unwind as returns arrive.

Expected returns are estimated from the product-category return rates in the data contract, which
vary from 3-4% on accessories to 9-10% on seasonal and limited-edition items, so category mix moves
the blended rate without any assumption changing.

Refunds reduce revenue. They are never presented as an operating expense.

Recoverable units return to inventory at original cost — 80% of DTC returns, 50% of wholesale. The
non-recoverable remainder is written off through shrink and obsolescence.

## Alternatives considered

**Record returns as they are processed.** Simplest to build and to explain, and it is what a
surprising number of small companies actually do. Rejected: it overstates revenue and margin in
every growing or seasonally peaking month, systematically rather than randomly, and a finance
reviewer would identify it immediately as a departure from GAAP. For a project whose audience
includes people assessing financial judgement, that is an expensive simplification.

**Reserve only at year-end.** Monthly reporting on an as-processed basis with a December true-up.
This is a genuinely common mid-market practice and has the merit of realism. Rejected because it
puts a large visible distortion into December — the month the annual board pack reports on — and
makes monthly gross margin non-comparable across the year, which undermines the variance
commentary that phase 5 is built to produce.

## Consequences

Two additional balance sheet lines and a reserve roll-forward that the board pack has to explain.
That is a real cost, and it is the point: the roll-forward is where reserve adequacy becomes
visible, and a reserve that is consistently too low is a finding the model can surface.

The return fact must preserve its originating sale line and period, so return lag and reserve
adequacy are testable rather than assumed. This is asserted in the validation suite: returns must
arrive after their originating sale in every case, with the stated lag distribution by channel.

Because the refund liability is estimated from category-level rates, a shift toward seasonal and
limited-edition product raises the reserve without anyone changing an assumption. That is the
correct behaviour and it is worth stating, because it will look like an error the first time it
appears in a variance.
