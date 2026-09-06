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

The choice follows from what this model is about rather than from convention.

**Working capital is the story.** Northlake's central tension is that a channel shift consumed
cash faster than it produced earnings — $720k absorbed into inventory and receivables in FY2025
alone, against a $1.3M loss. The indirect method puts that movement on its own lines, in the
statement, where a reader meets it. The direct method buries it: an inventory build appears only
as the difference between two gross flows nobody computes in their head.

**EBITDA is the model's own top line below revenue.** The scenarios are compared on EBITDA
margin, the covenant springs on TTM EBITDA, and the board pack's four judged outcomes include
operating cash flow. Starting the cash flow at EBITDA makes the bridge from the metric management
uses to the cash it produced a single readable statement rather than a reconciliation the reader
performs privately.

**It is what a lender reads.** The facility is asset-based (ADR 0008), and the borrowing base is
built from the same receivables and inventory the indirect method itemises. A cash flow that
shows those movements explicitly is the one that reconciles to the availability calculation.

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
