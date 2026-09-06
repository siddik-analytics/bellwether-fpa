# ADR 0003 — Standard landed cost with purchase price, freight and duty variances

- **Status:** Accepted
- **Date:** 2026-09-05
- **Phase:** 1 (data contract)

## Context

Landed cost at Northlake is 78% product cost, 12% inbound freight and 10% duty and customs, at a
FY2025 portfolio average of $15.00 per unit.

The FY2025 story requires those three components to move independently. The April 2025 supplier
increase raised **product cost** by about 8% and touched neither freight nor duty. Air freight,
used as an exception when a launch or a stockout justifies it, raises **freight** with no change in
product cost. If landed cost is carried as a single actual number per receipt, neither effect can
be isolated afterwards, and the gross margin bridge collapses into an unexplained "cost" bar.

That bar is the single most important explanatory element in the FY2025 board pack. A bridge that
cannot separate supplier price from freight volatility does not support the argument the pack
needs to make.

## Decision

**Inventory is carried at standard landed cost.** Purchase price variance, freight variance and
duty/customs variance are captured separately as they arise.

Standard landed cost is **effective-dated** at SKU or product-family level, built from supplier
unit cost, expected freight rate, duty rate, shipment mode and purchase volume. It is not a static
per-SKU constant.

Shipment mode (ocean or air) is an attribute of the purchase order. Air freight is a tracked
management exception and is never blended into the standard freight assumption.

## Alternatives considered

**Actual costing — carry each receipt at its own landed cost.** Arithmetically exact and
conceptually simpler, with no variance accounts to reconcile. Rejected because it makes the margin
bridge unattributable: the effect of a supplier price increase and the effect of an expedited
shipment arrive in the same number and cannot be separated after the fact. Exactness in the balance
is not worth losing the explanation.

**Weighted average cost across the portfolio.** Cheapest to implement. Rejected for the same reason
and one more: it obscures the difference between hero SKUs, which are ordered in large runs with
efficient freight, and seasonal SKUs, which carry 5-15% higher landed cost precisely because they
are not. That difference is part of why the long tail is unprofitable, which is a conclusion the
model is supposed to be able to reach.

## Consequences

Variance accounts must be reconciled, and the disposition of variances has to be stated: they are
expensed to COGS in the period they arise rather than being capitalised back into inventory. At
Northlake's scale the difference is immaterial and the simpler treatment is more legible.

Standard cost must be revised on a stated cadence, and revisions are themselves an event the model
carries. A standard that drifts far from actual makes the variance meaningless — which is a real
failure mode of standard costing and worth watching for rather than assuming away.

The reward is that the FY2025 margin bridge separates channel mix, promotional discount, supplier
price and freight into distinct, defensible bars. That decomposition is most of what makes the
board pack an argument rather than a report.
