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

## How to use this file

Add an entry when building an earlier phase surfaces something the board pack should carry.
Delete the file when phase 6 absorbs it into a real spec.
