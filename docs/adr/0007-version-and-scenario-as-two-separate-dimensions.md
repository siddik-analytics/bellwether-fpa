# ADR 0007 — Version and Scenario as two separate dimensions

- **Status:** Accepted
- **Date:** 2026-09-05
- **Phase:** 1 (data contract)

## Context

This project's standing convention, stated in `CLAUDE.md` and `.claude/rules/powerbi-pbip.md`, is
that scenario is a dimension rather than three parallel fact tables — with actual, budget and
forecast as its members. That convention is right about the important thing and wrong about a
detail that turns out to matter.

Northlake's planning process produces two independent classifications of the same fact.

The first is **what kind of number it is**: a posted actual, the frozen approved budget, the
immediately preceding formal reforecast, or management's current outlook. Northlake runs a monthly
rolling forecast with a formal quarterly reforecast, and explicitly retains prior forecasts rather
than overwriting them.

The second is **which strategic choice it represents**: the balanced base plan, wholesale
acceleration, or DTC recovery.

These are orthogonal. There is a Latest Forecast under Wholesale Acceleration and a Latest Forecast
under DTC Recovery; there is a Budget, which exists under exactly one scenario. Collapsing them
into a single dimension forces a member list that is the cross-product of the two, which is both
larger and unable to express "the same scenario, one forecast cycle apart".

## Decision

**Two dimensions.**

`dim_version` — Actual, Budget, Prior Forecast, Latest Forecast.

`dim_scenario` — Balanced Base, Wholesale Acceleration, DTC Recovery / Margin.

Budget is frozen on approval and never overwritten. Forecasts are retained rather than replaced.
The fact pattern is append-only.

Downside sensitivities — CAC above $38, a major account reducing orders, margin failing to recover,
sell-through below plan, DSO extending toward 60 days — are applied **to** scenarios rather than
being scenarios. They do not become dimension members.

`CLAUDE.md` and `.claude/rules/powerbi-pbip.md` are updated to match.

## Rationale

Variance reporting has to decompose into three distinct questions, and each holds one dimension
fixed while moving the other:

1. **Performance variance** — Actual against Budget, same scenario. *Did we do what we said?*
2. **Forecast revision** — Latest Forecast against Prior Forecast, same scenario. *What changed in
   our view?*
3. **Scenario difference** — Balanced Base against Wholesale Acceleration, same version. *What
   would a different strategy produce?*

A single dimension cannot express the second at all, because Prior Forecast and Latest Forecast
under the same strategy are indistinguishable once the two concepts are merged.

The automated variance commentary in phase 5 depends on this decomposition. Commentary that cannot
separate "we missed" from "we changed our mind" is commentary a CFO will not use.

## Alternatives considered

**One combined dimension**, the existing convention, with members such as Actual, Budget, Latest
Forecast Base, Latest Forecast Acceleration. Rejected: the member list is a cross-product that grows
multiplicatively, forecast revision cannot be expressed, and every measure needs string parsing of
member names to recover the two underlying concepts.

**Scenario as a dimension, version as a separate fact table per version.** Rejected as the parallel-
fact-table pattern the original rule exists to prevent, and correctly so.

## Consequences

Every planning fact carries both keys. Measures must be explicit about which dimension they hold
fixed, and a measure that filters neither is ambiguous rather than aggregate.

Scenario members are **not monotonic**, and this must be understood before any chart is designed.
Wholesale Acceleration has *higher* revenue and *worse* cash than the base case. Ordering scenarios
as upside/base/downside, or colouring them on a diverging scale, would misrepresent them.

Budget being frozen means a late budget correction is a new version, not an edit. This is more
work and it is the property that makes variance reporting trustworthy.
