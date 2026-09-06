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
| Total media spend / all new customers | ~$24 |
| Adding acquisition-attributable payroll, agencies, creative and tools | ~$32-34 |

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

**Paid media CAC** — performance media spend divided by paid-acquired new customers. FY2025: ~$34.
The measure of media efficiency, and the one against which the $30-33 target and $38 intervention
threshold are set.

**Blended media CAC** — total media spend divided by all new customers. FY2025: ~$24. The measure
of overall acquisition economics, sensitive to the organic mix by design.

**Fully loaded acquisition CAC** — adds acquisition-attributable payroll, agencies, creative and
tools. FY2025 target: ~$32-34.

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
programmes to customer acquisition, which overstates acquisition cost and, worse, penalises the
shift toward owned channels that management is explicitly trying to make. A measure that worsens
when the strategy succeeds is the wrong measure.

## Consequences

Every chart, measure and commentary line must name which CAC it means. Power BI measure names carry
the qualifier; an unqualified "CAC" is a defect.

The gap between paid CAC and blended CAC becomes a reported metric in its own right, because it
*is* the organic contribution. Narrowing that gap is the quantitative form of "reduce dependence on
paid acquisition".

The fully loaded measure requires an allocation rule for marketing payroll and agency cost between
acquisition and retention. That rule is an assumption and must be stated in the contract rather
than embedded in a calculation.
