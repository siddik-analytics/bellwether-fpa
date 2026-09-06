# ADR 0013 — Gross margin and EBITDA amended to the generated figures

- **Status:** Accepted
- **Date:** 2026-09-06
- **Phase:** 2 (generator)
- **Supersedes:** the margin, EBITDA and equity-raise figures in data contract §1.1, §7.1, §7.2,
  §7.3, §7.6 and §6.10

## Context

Data contract §7 was calibrated during phase 1 from a hand-built monthly model. Phase 2 spec
criteria 2.31–2.34 marked those figures **expected values rather than tolerances**, precisely
because a transaction-level simulation might disagree, and recorded that where it did, the
generator would be treated as the more reliable source and the contract amended.

It disagreed. The gap traces to a single superseded input: the contract's landed COGS of $4.587M
was derived from inventory turns of 3.3x on average inventory of $1.39M. ADR 0011 relaxed turns
to 2.40x on $2.08M, because 3.3x and the 4% service target are not jointly reachable. Landed COGS
follows inventory, so it moved with it — and gross margin follows landed COGS.

## Scratch model against generated output

Recorded side by side, because the delta between a hand-built monthly model and a
transaction-level simulation is itself worth showing: it is the difference between an FP&A
analyst's estimate and the system that replaces it.

| FY2025 | Phase 1 scratch model | Phase 2 generator | Delta |
|---|---|---|---|
| Inventory turns | 3.3x | 2.40x | −0.90x |
| Average inventory | $1.39M | $2.08M | +$0.69M |
| Landed COGS | $4.587M | $4.98M | +$0.39M |
| Blended gross margin | 46.7% | **43.6%** | −3.1pt |
| EBITDA | $(859)k, −8.1% | **$(1,310)k, −12.35%** | −4.25pt |
| DTC gross margin | 53.9% | — | |
| Wholesale gross margin | 37.1% | — | |

| Gross margin by year | Scratch | Generated | Delta |
|---|---|---|---|
| FY2023 | 50.1% | **53.0%** | +2.9pt |
| FY2024 | 50.0% | **47.3%** | −2.7pt |
| FY2025 | 47.0% | **43.6%** | −3.4pt |

| Financing | Scratch | Generated | |
|---|---|---|---|
| FY2024 equity raise | $3.50M | **$5.50M** | |
| Balanced Base minimum availability | $445k (Jul-2028) | **$741k (Jul-2028)** | |
| Wholesale Acceleration breach | Feb-2028 | **Apr-2028** | |
| DTC Recovery minimum availability | $678k | **$997k** | |

**The year-on-year pattern is a finding, not noise.** The scratch model held gross margin roughly
flat across FY2023–24 at ~50%; the generator has it falling from 53.0% to 47.3% to 43.6%. The
difference is that the generator computes COGS from units, and units per revenue dollar rise as
the channel mix shifts — wholesale realises $25.10 a unit against DTC's $46, so 41% wholesale
revenue is a much larger share of *units* than of dollars. A ratio-based model cannot see that;
a unit-level one cannot avoid it.

This makes the margin decline steeper and more clearly attributable to channel mix than the
contract described, which strengthens rather than weakens the board pack's central argument.

## Decision

**Amend the contract to the generated figures.** Gross margin 53.0% / 47.3% / 43.6%; FY2025
EBITDA −12.35%; FY2024 equity raise $5.50M.

The generator is preferred because its COGS is derived rather than assumed: units sold ×
effective-dated landed cost, plus the delivery costs §6.3 places in cost of sales, cross-checked
against the ledger's own trial balance. The scratch figure was an assumption about a ratio.

## Alternatives considered

**Keep the contract figures and tune the generator to match.** Rejected, and it is worth being
explicit about why: the only way to reach 47.0% would be to hold less inventory, which ADR 0011
already established is not possible at 4% service. Tuning to the number would mean breaking the
service target to preserve a margin figure derived from an inventory position that cannot exist.

**Treat the divergence as within tolerance.** Rejected on size. 4.25 points of EBITDA is not a
tolerance question; it moves the required equity raise by $2M.

## Consequences

**The equity raise rises from $3.50M to $5.50M**, and this is the consequential change. At $3.50M
Balanced Base breaches in April 2027; at $4.50M in April 2028; it holds only from $5.50M. That is
59% of FY2024 revenue raised in a single round, which is a large but not implausible Series B for
a DTC brand with a wholesale expansion story — and it sharpens the board question rather than
softening it, because the money is visibly funding inventory rather than growth.

$5.50M is also the point at which the scenarios still **discriminate**: Balanced Base holds at
$741k, Wholesale Acceleration breaches in April 2028, DTC Recovery holds at $997k. At $6.50M all
three hold and the comparison stops being informative.

**None of the three scenarios reaches profitability, and the gap widened.** FY2028 EBITDA is
−4.96% under Balanced Base, −4.20% under Acceleration, −4.58% under DTC Recovery. Each needs
roughly $600–700k of cost out to break even in the final year. The charter already records that
non-profitability is deliberate; at these margins it is starker, and it raises a scope question
for phase 5 noted below.

**A fourth scenario is probably warranted.** All three current scenarios are growth variants —
they differ in *where* growth comes from, not in whether the cost base changes. At −12.35% EBITDA
the board's first question is not which growth path to take but whether breakeven is reachable at
all, and no modelled scenario answers it. A cost-reduction case would. That is a change to §3.2
and is not made here.
