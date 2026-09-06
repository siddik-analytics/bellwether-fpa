# ADR 0009 — Supplier contracts denominated in USD; FX out of scope

- **Status:** Accepted
- **Date:** 2026-09-05
- **Phase:** 1 (data contract)

## Context

Northlake sources most finished goods from overseas contract manufacturers, primarily in Asia. The
phase 1 interview asked that foreign exchange exposure be retained where relevant to purchasing and
landed cost.

`docs/charter.md` places multi-entity and multi-currency logic explicitly out of scope.

These are in direct conflict and the conflict cannot be resolved by implementation. Either the
model gains a currency dimension, rate tables and payables revaluation, or the charter is amended,
or supplier contracts are USD-denominated and the question does not arise.

## Decision

**Supplier contracts are denominated in USD.**

Foreign exchange surfaces only as supplier price movement, which the purchase price variance
established in ADR 0003 already captures. There is no rate dimension, no revaluation of
foreign-denominated payables, and no FX gain or loss line.

The `currency` field on the purchase-order line is retained for shape and is USD-only. It is not a
live dimension.

`docs/charter.md` stands unamended.

## Rationale

USD-denominated contracts with Asian contract manufacturers are common practice, not a modelling
convenience, so this resolves the conflict without making the business less realistic.

More importantly, nothing the model needs to demonstrate depends on FX. The April 2025 supplier
cost increase — the most consequential cost event in the dataset — works exactly as described
whether the underlying cause was input costs, labour, packaging or currency. It arrives as an 8%
step in product cost either way.

The charter exists to settle scope arguments. Amending it in week four of a seven-phase build, for
a second-order effect, is the failure mode the charter was written to prevent.

## Alternatives considered

**Model FX explicitly on purchase-order lines.** A currency and rate per line, with revaluation of
foreign-denominated payables and an FX gain/loss line. More realistic for some supplier
relationships. Rejected: it adds a rate dimension, revaluation logic, a new income statement line
and a new class of period-end adjustment, in exchange for an effect that is immaterial to every
argument the board pack makes. The charter would need amending to permit it, which is the correct
process and also a signal that the change does not belong in this phase.

**Retain the currency field as a live dimension with a single member.** Rejected as worse than
either alternative: it carries the cost of the machinery — joins, validation, the appearance of
multi-currency support — while delivering none of the capability, and it invites a future
contributor to assume the model handles FX when it does not.

## Consequences

Purchase price variance now absorbs any effect that would have been FX, which means PPV is not a
pure measure of supplier negotiation. This should be stated where PPV is reported rather than left
for a reader to discover.

If Northlake ever needs genuine FX modelling, the path is a charter amendment and a new ADR
superseding this one — not quietly adding a rate table. The `currency` field's presence makes that
extension mechanically straightforward without implying it already works.
