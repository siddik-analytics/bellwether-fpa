# ADR 0005 — Marketing as a constrained driver with a CAC response curve

- **Status:** Accepted
- **Date:** 2026-09-05
- **Phase:** 1 (data contract)

## Context

Marketing is 13.7% of Northlake's net revenue and 23% of DTC net revenue. How it is modelled
determines the shape of the entire forecast, not merely the size of one line.

Two conventional treatments exist. Marketing as a percentage of revenue makes it an output, which
is circular: revenue is what marketing is supposed to drive. Marketing as `spend x fixed ROAS`
makes it a linear input, which is false in a specific and consequential way — Northlake's own
history shows paid CAC rising from $29 to $34 while spend increased, and the non-paid share of new
customers falling from 38% to 30%. Marginal efficiency is deteriorating, and a linear model asserts
that it does not.

The failure mode of the linear version is worse than inaccuracy. Because revenue scales with spend
at a constant rate, the optimiser can always buy its way to a target, and marketing silently
becomes the plug that makes the forecast balance.

## Decision

Marketing is split into two behaviours that do not share a driver.

**Variable performance marketing** — paid social, paid search, affiliate, creator acquisition,
retargeting. Solved from a new-customer target against a **CAC response curve** in which marginal
acquisition cost rises with spend, subject to a management spending ceiling and a CAC efficiency
threshold.

**Semi-fixed programme marketing** — creative production, CRM and loyalty tools, PR, brand
partnerships, content, baseline agency costs. Budgeted directly and stepping periodically, not
flexing with revenue.

The governing constraint:

> **If required spend exceeds the approved CAC threshold, the model reduces assumed new-customer
> acquisition rather than silently increasing marketing efficiency.**

Management's thresholds are a $30-33 target range and a $38 intervention point, against FY2025
actual paid CAC of $34.

## Alternatives considered

**Marketing as a fixed percentage of revenue.** Universal in simple models. Rejected as circular
and because it cannot express the thing that is actually happening: efficiency deteriorating while
spend rises.

**Fixed ROAS.** Rejected as described above. It is not merely imprecise; it makes the forecast
unfalsifiable, because any revenue target becomes reachable with enough spend.

**A response curve with no ceiling.** Retains the diminishing returns but allows the model to keep
buying customers at any price. Rejected because it produces plans management would never approve,
and because the CAC threshold is a real governance mechanism at Northlake, not a modelling
convenience.

## Consequences

The constraint runs in the direction that makes the model less flattering, deliberately. When CAC
breaches threshold, the plan loses customers rather than gaining efficiency. This will produce
forecasts that miss revenue targets, and that is the correct behaviour.

Acquisition channel becomes a customer attribute carrying real weight: it drives repeat rate as
well as CAC, so the mix of how customers were acquired affects revenue years later.

Marketing is almost entirely a DTC cost and sits in the contribution tier by channel. It is the
main reason wholesale contribution margin is competitive with DTC despite the 18.5-point gross
margin gap — and therefore central to the Scenario 3 question of whether better DTC economics beat
more wholesale volume.

The response curve's shape is an assumption and should be visible as one. It is a driver in the
sensitivity set, not a constant buried in code.
