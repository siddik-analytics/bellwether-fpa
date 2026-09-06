# ADR 0006 — Three explicit CAC definitions

- **Status:** Accepted
- **Date:** 2026-09-05
- **Phase:** 1 (data contract)

## Context

Customer acquisition cost is quoted constantly and defined inconsistently. At Northlake three
different quantities all reasonably answer "what does a customer cost", and they differ by more
than 40%:

| Measure | FY2025 |
|---|---|
| Performance media spend / paid-acquired new customers | ~$34 |
| Performance media spend / all new customers | ~$24 |
| Adding acquisition-attributable payroll, agencies, creative and tools | ~$32-34 |

A fourth quantity exists and is routinely mistaken for a CAC: total marketing spend divided by all
new customers, which is ~$35. It is not an acquisition cost, because the numerator includes brand,
retention and owned-channel programme spend that acquires no customers.

Reporting a single number invites two failures. If the blended figure is quoted, the business looks
more efficient than it is, and the deterioration in paid efficiency is hidden by organic customers
who were never bought. If only the paid figure is quoted, the value of the owned and referral base
is invisible, and the strategic objective of shifting toward it has no measure attached.

Both failures matter here because the underlying trend is unfavourable and partly concealed: the
non-paid share of new customers fell from 38% to 34% to 30% across the three years, while paid CAC
rose from $29 to $34. The business became more dependent on paid acquisition *and* paid acquisition
became more expensive. A single blended number understates both movements, because a falling
organic share drags the blend upward for reasons that have nothing to do with media efficiency.

## Decision

Three named measures, defined once and never used interchangeably.

**Paid media CAC** — performance media spend divided by **paid-acquired** new customers. FY2025:
~$34. The measure of media efficiency, and the one against which the $30-33 target and $38
intervention threshold are set.

**Blended acquisition CAC** — performance media spend divided by **all** new customers. FY2025:
~$24. The measure of overall acquisition economics, sensitive to the organic mix by design.

**Fully loaded acquisition CAC** — blended acquisition CAC plus acquisition-attributable payroll,
agencies, creative and tools. FY2025 target: ~$32-34.

All three share the same numerator base — **performance media spend of $986k**, being 68% of the
$1.45M total. Only the denominator changes, and for the third, what is added. Holding the numerator
base constant is what makes the three comparable; a measure that switched to total marketing spend
would not be measuring acquisition at all.

Reported alongside, and **explicitly not a CAC**: **total marketing spend per new customer**,
$1,450k / 41,400 = **~$35**. This is a marketing-intensity ratio and is labelled as one.

Arithmetic: $986k / 29,000 = $34.00; $986k / 41,400 = $23.82; $1,450k / 41,400 = $35.02.

**Not all marketing payroll and not all brand and retention spend is allocated to acquisition.**
Only the acquisition-attributable portion enters the fully loaded measure. Retention, brand and
owned-channel programme costs are excluded from it.

FY2025 volumes: ~29,000 paid-acquired new customers, ~12,400 organic, referral and owned, ~41,400
total.

## Alternatives considered

**A single blended CAC.** Simplest to report and common in board decks. Rejected: it moves for two
unrelated reasons — media efficiency and organic mix — and cannot distinguish them, which is
precisely the distinction the FY2023-25 trend requires.

**A fully loaded measure that absorbs all marketing cost.** Superficially the most conservative and
therefore the most defensible-sounding. Rejected because it charges brand-building and retention
programmes to customer acquisition, which overstates acquisition cost by 46% ($35 against $24) and,
worse, penalises the shift toward owned channels that management is explicitly trying to make. A
measure that worsens when the strategy succeeds is the wrong measure.

**Defining the blended measure on total media spend rather than performance spend.** This was the
original formulation and it was wrong: total media divided by all new customers is $35.02, not the
$24 quoted alongside it, so the definition and the figure disagreed. Correcting the figure to $35
would have been the other available fix, and was rejected because it changes what the measure means
— the blended measure exists to show acquisition economics improving as the organic share rises,
which requires a numerator confined to acquisition spend.

## Consequences

Every chart, measure and commentary line must name which CAC it means. Power BI measure names carry
the qualifier; an unqualified "CAC" is a defect.

The gap between paid CAC and blended CAC becomes a reported metric in its own right, because it
*is* the organic contribution. Narrowing that gap is the quantitative form of "reduce dependence on
paid acquisition".

The fully loaded measure requires an allocation rule for marketing payroll and agency cost between
acquisition and retention. That rule is an assumption and must be stated in the contract rather
than embedded in a calculation.
