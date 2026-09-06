# ADR 0017 — The returns reserve and its unwind are separate accounts

- **Status:** Accepted
- **Date:** 2026-09-06
- **Phase:** 3 (transformation layer)
- **Extends:** ADR 0002 (returns recognised on an ASC 606 basis)

## Context

ADR 0002 recognises revenue net of expected returns: a refund liability is booked when the sale
is recognised and unwound when the return arrives. Phase 2 posts both movements to the **same**
contra-revenue account — 4110 for DTC, 4120 for wholesale.

That makes "returns for March" ambiguous. It can mean the reserve booked against March sales, or
the reserve released against returns physically received in March. The two differ by the return
lag, which is 18 days on average for DTC and 45–90 days for wholesale — so in November, when
Black Friday concentrates sales, they differ a great deal.

Contract §6.2's gross-to-net ladder reads:

```
Net merchandise revenue
  less returns (7% of net merchandise sales)
```

"7% of net merchandise sales" is unambiguously the **reserve**, computed on the period's sales.
But nothing in the ledger distinguishes it from the unwind, so a measure summing account 4110
returns the net of the two and the ladder silently stops reconciling in any month where sales
are growing or seasonal.

## Decision

**Split the accounts. The reserve is contra-revenue; the unwind is a separate movement.**

| Account | Meaning | Statement position |
|---|---|---|
| 4110 | DTC returns reserve — booked at sale, on the period's sales | Contra-revenue |
| 4111 | DTC refund liability utilisation — released when the return is received | Balance sheet movement |
| 4120 | Wholesale returns reserve — booked at sale | Contra-revenue |
| 4121 | Wholesale refund liability utilisation | Balance sheet movement |

**"Returns" in the §6.2 gross-to-net ladder means the reserve booked at sale**, per ADR 0002.
Only 4110 and 4120 reduce revenue. The utilisation accounts move the refund liability against
cash and never touch the income statement.

## Rationale

Revenue is recognised net of *expected* returns, so the amount that reduces revenue must be the
expectation formed at the point of sale. The later arrival of the physical return is the
settlement of a liability already recorded — it changes the balance sheet, not the period's
revenue. Posting both to one account mixes an income-statement estimate with a balance-sheet
settlement, which is the error the ASC 606 treatment exists to avoid.

The split also makes **reserve adequacy visible**, which is the point of carrying a reserve at
all. With separate accounts, the roll-forward is readable directly from the ledger — opening
liability, plus reserve booked, less utilisation, equals closing — and a reserve consistently
too low or too high shows up as a drift between the two. Netted into one account, that drift is
invisible.

## Alternatives considered

**Keep one account and define the measure to mean the reserve.** Cheaper, and it fails the
contract's own §9 check that the gross-to-net ladder must be reconstructable **from ledger
accounts alone**. If the ledger cannot distinguish the two, the ladder needs a management
adjustment, which the check exists to prohibit.

**Define "returns" as the unwind instead.** Rejected: it would recognise revenue gross and reduce
it when returns arrive, which is the as-processed basis ADR 0002 explicitly rejected for
overstating revenue in every growing or seasonally peaking month.

## Consequences

Two additional GL accounts per channel, and the refund liability roll-forward becomes a reported
schedule rather than a derivation.

The semantic layer defines `Returns` once, as the reserve accounts only. A measure that sums all
four is a defect, and criterion 3.20 — the gross-to-net ladder reconstructing from ledger
accounts alone — is what catches it.

Comparing the reserve booked against the utilisation over a rolling window gives a reserve
adequacy measure the board pack can carry. That was not previously computable and is a small
gain that came free with the split.
