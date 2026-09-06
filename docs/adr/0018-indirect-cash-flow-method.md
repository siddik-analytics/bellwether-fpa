# ADR 0018 — The cash flow statement uses the indirect method

- **Status:** Accepted
- **Date:** 2026-09-06
- **Phase:** 4 (Excel model)

## Context

The data contract requires a cash flow statement — §9 check 5 asserts that closing cash on the
cash flow equals balance sheet cash in every period — but never states which method produces it.
That gap survived three phases because nothing had assembled a cash flow statement yet. Building
the workbook is what forced the question.

The two methods present genuinely different statements from identical data. The **direct** method
lists gross cash flows: receipts from customers, payments to suppliers, payments to employees.
The **indirect** method starts from an earnings figure and reconciles to cash through non-cash
items and working capital movements.

## Decision

**Indirect, starting from EBITDA.**

```
EBITDA
  less  increase in inventory
  less  increase in receivables
  less  increase in supplier advances
  plus  increase in payables
  plus  increase in refund liability
= Cash generated from operations
  less  interest paid
  less  capital expenditure
= Free cash flow
  plus  equity raised
  plus/less  revolver drawings and repayments
= Movement in cash
```

## Rationale

The choice follows from Northlake's financing structure rather than from convention.

**It is the statement the lender reads.** The facility is asset-based (ADR 0008): the borrowing
base advances 85% against eligible receivables and 50% against eligible inventory, and the
covenant tests availability monthly. Those are precisely the balances the indirect method
itemises, line by line, as the movements that consumed or released cash. A cash flow built this
way reconciles directly to the availability calculation — a reader can trace an inventory build
from the statement into the borrowing base and out into the covenant headroom. The direct method
shares no line with the facility documentation at all.

That matters more here than in most models, because the covenant is what makes the scenarios
discriminate. Wholesale Acceleration reaches the highest revenue of the four and the best EBITDA
of the three that grow, and it is the one that breaches. The explanation is entirely in
receivables and inventory. A statement that does not show those movements cannot explain the
model's central result.

**Working capital is also the story.** A channel shift consumed cash faster than it produced
earnings — $720k absorbed into inventory and receivables in FY2025 against a $1.3M loss. The
indirect method puts that on its own lines where a reader meets it; the direct method buries an
inventory build in the difference between two gross flows nobody computes in their head.

**And EBITDA is the model's own measure.** Scenarios are compared on EBITDA margin, the board
pack's four judged outcomes include operating cash flow, and §1.2 now turns on the gap between
channel contribution and the corporate block. Starting the statement at EBITDA makes the bridge
from the metric management uses to the cash it produced a single readable statement rather than a
reconciliation the reader performs privately.

## Alternatives considered

**Direct method.** Gross receipts and payments. It is the method standard-setters prefer and the
one users generally find more intuitive, so the rejection is not because it is worse in general.
Rejected here because it obscures the single most important dynamic in this business: the reader
sees $X received and $Y paid and cannot tell that inventory grew by $400k. Northlake's entire
argument is about that number.

It is also more work for less: the direct method needs cash receipts and payments derived per
counterparty type, which the ledger supports but which adds a derivation whose only output is a
statement that says less.

**Both, with the indirect as a reconciliation note.** What many filers do. Rejected as
disproportionate for a management pack, and it would double the statement surface the
reconciliation test has to cover for no analytical gain.

## Consequences

The cash flow depends on **movements**, so it needs an opening balance sheet and cannot be
computed for the first period of any series in isolation. The forecast already posts an opening
balance sheet for exactly this reason (ADR 0014), so the requirement is met, but a cash flow
starting from a zero opening position would be silently wrong rather than obviously so.

Non-cash items must be identified as such and excluded. Shrink is a reserve movement rather than
a cash payment (§6.5), the returns reserve unwinds against the refund liability without cash
until the refund is paid (ADR 0017), and depreciation is non-cash. Each is added back explicitly.

**EBITDA becomes load-bearing in a second place.** It already drives the scenario comparison; it
now also opens the cash flow. A change to what EBITDA includes — reclassifying a cost between
COGS and opex, say — moves both, which is an argument for the classification being frozen across
periods as ADR 0004 requires.

The data contract gains an account classification (current/non-current, and cash/non-cash) that it
did not previously carry, because the indirect method needs to know which balance movements are
working capital and which are financing.
