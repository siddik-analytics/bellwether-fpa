# Carried requirements for phase 6 — board pack

A running list of board-pack exhibits identified while building earlier phases. They are
recorded here rather than in a phase 6 spec that does not exist yet, because the reason each one
is worth including is clearest at the moment it is discovered and gets lost otherwise.

Each entry states the exhibit, why it earns space, and where the data already exists.

---

## C-1 · The unallocated cost sensitivity

**Exhibit:** what Northlake deliberately did not allocate to channel, and what the choice would
have been worth.

Channel contribution reporting leaves Supply Chain / Operations unallocated (ADR 0010, §6.7).
The board pack should show why, with the numbers, rather than footnoting it — against FY2025
actuals and $420k of Supply Chain cost, three defensible drivers put between 3% and 64% of it on
wholesale:

| Driver | To DTC | To Wholesale | Wholesale share |
|---|---|---|---|
| Order and invoice lines | $405k | $15k | 3% |
| Net revenue | $252k | $168k | 40% |
| Units shipped | $153k | $267k | 64% |

A $253k spread on a $420k cost, landing in the exact comparison the pack turns on.

**Why it earns a slide.** Most FP&A functions never produce this. The normal choices are to
allocate on revenue and present the result as fact, or to leave the cost unallocated and say
nothing. Showing the range makes two claims a reader can check: that the team knows which of its
numbers are decided by judgement rather than measurement, and that it declined to manufacture
precision in the one comparison the decision rests on.

It is also the strongest available answer to the question a sceptical reader is already forming —
"how much of this channel comparison is an allocation artefact?" Answering it before it is asked
is worth more than the slide costs.

**Data:** `transform.allocation.supply_chain_sensitivity`, already built and tested in phase 3.
No new work beyond presentation.

---

## C-2 · Both channels contribute; the loss is the corporate block

**Exhibit:** channel contribution for FY2025 with the unallocated corporate cost shown as its own
block rather than pushed into the channels.

| | Net revenue | Contribution margin | Contribution |
|---|---|---|---|
| DTC | $6.22M | 57.1% | **+$774k** |
| Wholesale | $4.38M | 24.4% | **+$732k** |
| Unallocated corporate | - | - | **-$2,810k** |
| | | | **-$1,304k** |

**Why it earns a slide.** It reverses the conclusion the reader arrives with. A brand that shifted
toward wholesale and posted a loss looks like a brand whose wholesale margin does not cover its
costs. Both channels are contribution-positive; neither is the loss. The entire loss is a $2.81M
corporate block carried on $10.6M of revenue, and no plausible reallocation of it changes that,
which is exactly what C-1 demonstrates.

The pack should carry the second table with it, because without it the first invites the wrong
remedy - cut the corporate block - when the actual finding is narrower:

| | FY2023 | FY2024 | FY2025 |
|---|---|---|---|
| Corporate block | $1.81M | $2.18M | $2.81M |
| as % of revenue | 22.3% | 23.5% | **26.5%** |
| Wholesale revenue, indexed | 1.00x | 1.32x | 1.82x |
| Corporate cost, indexed | 1.00x | 1.20x | **1.55x** |

The cost base was built for wholesale and grew with it, **directionally but not proportionally**.
Stating it that precisely is the point: the weaker claim is the one the data supports, and a board
that is told the stronger one will discover the difference itself.

**Data:** `transform.allocation`, built and tested in phase 3. Contract section 1.2.

---

## C-3 · The cash flow, the borrowing base and the covenant, as one trace

**Exhibit:** a single page running EBITDA down to covenant headroom, for Balanced Base against
Wholesale Acceleration.

**Why it earns a slide.** It is the only exhibit that explains the model's central result, and the
result is counter-intuitive enough that assertion will not carry it: **Wholesale Acceleration
reaches the highest revenue of the four and the best EBITDA of the three that grow, and it is the
one that breaches.** Balanced Base holds $746k of minimum excess availability, DTC Recovery holds
$1,181k, Consolidation reaches breakeven and never draws at all, and the growth scenario with the
strongest earnings runs out of room in May-2028.

The explanation is entirely in working capital, and the indirect cash flow method was chosen so
that it would be legible on the face of the statement rather than derived by the reader (ADR
0018). The same receivables and inventory balances the statement itemises as movements are the
balances the facility advances against - 85% and 50% respectively (ADR 0008). One page can
therefore run: EBITDA, less the inventory and receivable build, to cash; the same two balances
into the borrowing base; the base less the drawn balance to availability; availability against
the covenant floor. Every number on it already exists and ties.

That trace is also the answer to the raise. $7.5M is not sized to fund losses, it is sized to fund
the working capital the growth scenario consumes, and the page shows why the scenario with the
best P&L needs the most of it.

**Data:** `transform.statements.cash_flow` and the covenant probe, phases 3 and 4. Contract
sections 6.10 and 9.

---

## How to use this file

Add an entry when building an earlier phase surfaces something the board pack should carry.
Delete the file when phase 6 absorbs it into a real spec.
