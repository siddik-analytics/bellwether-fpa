# ADR 0020 — The star is the consumer boundary: dollars, allocations resolved

- **Status:** Accepted
- **Date:** 2026-09-06
- **Phase:** 5 (Excel/COM stage and Power BI)

## Context

Two apparently unrelated problems came out of specifying the Power BI layer, and they turned out
to be the same problem asked twice.

**The channel split was applied after the star.** `star.channel_key_for_ledger` resolved every
row the §6.7 mapping sent to `BY_UNITS` — shared cost of goods, accounts 5000 to 5320 — to the
**corporate** channel member, and `semantic.channel_contribution` split it by units afterwards,
"in the semantic layer, where the unit counts live". Power BI reads the star. It would have seen
$205M of product cost sitting on corporate, and to reproduce the channel contribution the board
pack turns on it would have had to re-implement the units allocation in DAX. That is a second
definition of the §6.7 mapping, which is the failure ADR 0010 exists to prevent.

**Money was stored in cents.** §2.1 stores monetary values as integer minor units in fact tables,
for a good reason: floats accumulate error a ledger cannot afford. But a consumer reading those
facts gets cents, and every money measure would have carried a `/ 100` — a transformation the
semantic layer never authorised, repeated in every consumer, in a project that had already
published a discount **rate** as `49` because a suffix rule could not tell a rate from an amount.

Both are the same question: **what does a consumer have to know, and what does it have to
compute for itself?**

## Decision

**The star schema is the boundary. Everything downstream reads it and nothing else.**

Two consequences follow, and they are the whole decision:

1. **The `BY_UNITS` split is materialised in the star.** Each shared-cost row becomes one row per
   channel, pro-rated by the units that channel shipped in that month. Channel contribution
   becomes a group-by rather than a calculation, in every consumer.
2. **The star exposes dollars.** `data/parquet/` remains the generator's own output in integer
   minor units per §2.1. `data/star/` is what the workbook, Power BI and the board pack read, and
   it holds dollars.

The rule for anything else that comes up: if a consumer would otherwise have to compute it, the
star computes it first.

## Rationale

A boundary is only useful if it is the *same* boundary for everyone. The previous arrangement had
the workbook reading in-memory frames through the semantic layer, Power BI reading Parquet, and
the two seeing different things — one with the split applied and dollars, one without and cents.
Two consumers of "the same" model that disagree about what a row means are not consuming the same
model.

**Monthly rather than annual.** Materialising the split forced the basis to become monthly,
because the star is at transaction grain and there is no annual row to attach a ratio to. That is
a real improvement rather than an incidental one: the DTC share of units swings from **17% to
62% across the months of FY2025**, so an annual ratio applied to a monthly grain is the same
class of error as the flat landed cost phase 2 removed. The net FY2025 effect is small — about
$1.5k moves from DTC to wholesale — which is worth stating precisely because it shows the
correction was needed for a structural reason and not because the old answer was visibly wrong.

**Cents are a storage decision, not a modelling one.** §2.1's argument is about accumulating
float error through a ledger. That argument is entirely about the write path and says nothing
about what a reader should receive. Making every consumer learn which of two directories holds
which unit is exactly the trap the `msrp_discount` defect already sprang once.

## Alternatives considered

**A units bridge table the consumer filters through.** Emit units by channel by month and let
each consumer join to it. Rejected: it preserves the current shape, but it leaves the allocation
as something each consumer performs, which is the property being removed. It also puts the ratio
in the model as data a report author can accidentally filter, silently changing an allocation.

**Convert cents to dollars in DAX.** One expression per measure. Rejected: it is a
transformation Power BI would own, repeated in every money measure, and it makes the DAX
generator's output depend on where the data came from rather than only on the metric definition.

**Leave the split in the semantic layer and give Power BI a summary table.** Rejected: it turns
Power BI into a consumer of a pre-aggregated extract rather than of the model, which loses
drillthrough to transaction level — criterion 5.27 — and makes the tool a picture of the answer
instead of a way to interrogate it.

## Consequences

The star's `fact_gl` has **more rows than the source ledger** — 39,626 against 35,988 — because
shared-cost rows are split. Totals are preserved exactly and the trial balance still nets to zero
for every period of every version and scenario; the split redistributes an amount, it never
changes one. A test asserts both.

**The forecast has no measured units, so its shared costs stay unallocated.** Units are measured
from transaction facts and the transaction facts cover actual periods only. Those rows keep the
corporate member and carry `split_basis = "none"` rather than being allocated on a chosen basis.
This is deliberate: §6.7's argument for splitting by units is that units are *measured rather
than chosen*, and that argument does not survive being applied to a period where nothing was
measured. It means channel contribution is an **actuals-only** report, which is what every
exhibit that uses it already is.

A `split_basis` column now travels with every GL row — `direct`, `units shipped`, or `none` — so
a reader can see which costs were attributed and how, rather than inferring it.

FY2025 channel contribution restates slightly, to DTC **+$767k** and Wholesale **+$734k** against
the previously documented +$774k and +$732k. The corporate block is unchanged at −$2,810k and so
is the conclusion. §1.2 and the README are updated to the generated figures on the same principle
as ADR 0013.
