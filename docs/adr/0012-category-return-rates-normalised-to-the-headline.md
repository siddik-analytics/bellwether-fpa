# ADR 0012 — Category return rates are normalised to the headline 7%

- **Status:** Accepted
- **Date:** 2026-09-05
- **Phase:** 2 (generator)

## Context

The data contract states the DTC return rate twice, at different grains, and both statements come
from the same interview answer (Q10).

§5.3 gives the headline: DTC returns are **7% of net merchandise sales**.

§4.1 gives return rate as a product-category attribute, so that category mix moves the blended
rate without any assumption changing:

| Category | Rate |
|---|---|
| Core drinkware | 5–6% |
| Food storage | 7–8% |
| Seasonal / limited edition | 9–10% |
| Accessories | 3–4% |

These cannot both be free. Applied literally against Northlake's revenue mix — which is
drinkware-heavy by construction, since the hero SKUs are drinkware and the top ten SKUs are 55%
of revenue — the category rates produce a revenue-weighted return rate of **5.9%**, not 7%.

The gap is not cosmetic. Returns are contra-revenue (§6.2), so a 1.1 point error in the blended
return rate moves reported DTC revenue by roughly $70k a year, and it moves it in the direction
that makes the business look better. It was found because FY2023–25 revenue came out 0.5–0.7%
above the contract targets and the excess had to be explained.

## Decision

**The headline 7% binds. Category rates are scaled to satisfy it.**

Each category's rate is multiplied by a single factor chosen so that the revenue-weighted mean of
the category rates equals 7.0%. The relative ordering and spacing between categories is
preserved — seasonal still returns roughly three times as often as accessories — but the absolute
level is set by the headline.

## Rationale

The headline is the more reliable of the two figures, for a specific reason rather than a general
preference for round numbers. A finance team measures blended return rate directly: it is
returns divided by sales, both of which are in the ledger. Category-level rates are an analytical
breakdown, more likely to be quoted from memory, more likely to be stated as a range, and in this
case *were* stated as ranges while the headline was stated as a point estimate.

Normalising the categories to the headline also keeps the mechanism the contract asks for. §4.1
exists so that a shift in category mix moves the blended rate on its own, and scaling all
categories by one factor preserves that behaviour exactly — the mix effect is unchanged, only the
level is pinned.

The reverse choice would let the headline float with mix, which sounds more principled and is
worse in practice: the headline is what every downstream calibration check tests against, so a
drifting headline turns one assertion into an untestable range.

## Alternatives considered

**Let the headline float and treat the category rates as binding.** Rejected. It would put the
blended rate at 5.9% against a contract that says 7%, requiring §5.3 to be rewritten as an output
rather than an input, and leaving validation check 25 (returns arrive after their originating sale
with the stated rates) with no rate to assert.

**Reweight the product mix until the category rates produce 7%.** This would mean making the
catalogue more seasonal and less drinkware-heavy. Rejected because product mix is pinned by four
other constraints — the §4.1 concentration bands, the SKU class split, the family counts, and the
hero-SKU definition — and bending all of them to fix a return rate would be solving the wrong
problem with the wrong variable.

**Widen the category rates to the top of their stated ranges.** Drinkware 6%, food storage 8%,
seasonal 10%, accessories 4% still gives a weighted mean of 6.5%, so the gap narrows but does not
close. Rejected as insufficient, and it would exhaust the interview's stated ranges to get there.

## Consequences

The category rates in `config.RETURN_RATE_BY_CATEGORY` are the *shape*; the effective rates the
generator applies are those values scaled at build time. Anyone reading the config and expecting
those literals to appear in the data will not find them, so the scaling is applied in one place,
in `dimensions.build_products`, with the reason stated at the point of use.

Realised DTC return rates after normalisation are 6.96% / 6.93% / 7.02% across FY2023–25, and
revenue lands within 0.2% of the contract targets in all three years.

If a future change makes the catalogue materially less drinkware-weighted, the scaling factor
moves toward 1.0 on its own. It is a normalisation, not a constant, so it does not need
maintaining.
