# ADR 0016 — Actual periods carry the operating plan scenario, not "Not applicable"

- **Status:** Accepted
- **Date:** 2026-09-06
- **Phase:** 3 (transformation layer)

## Context

`dim_scenario` and `dim_version` are separate dimensions (ADR 0007). Every planning fact carries
both. Actual periods carry `version = Actual` and, as generated in phase 2, an **empty**
scenario — which is not a dimension member, so roughly 27,000 of the ledger's 30,000 rows cannot
join to `dim_scenario` at all.

Something has to fill it. The obvious answer is a "Not applicable" member, and that answer is
wrong for a specific reason.

Contract §3.3 defines the three variance decompositions, and the first one is:

> **Performance variance** — Actual vs Budget, **same scenario**. *Did we do what we said?*

If actuals sit under a "Not applicable" scenario and Budget sits under Balanced Base, then
comparing them is a **cross-scenario** comparison. Every performance variance in the model would
be computed by crossing a dimension boundary the contract says to hold fixed, and the
decomposition §3.3 exists to support would be structurally impossible — not merely awkward.

## Decision

**Actual periods carry `scenario = Balanced Base`.**

Balanced Base is the operating plan (`dim_scenario.is_operating_plan`). Budget was approved under
it, management reports against it, and the reforecast that replaces it is prepared under it.
Actuals are the realisation of that plan, so recording them under it is not a convenience — it is
what the scenario dimension means for a period that has already happened.

Performance variance is then `Actual vs Budget` within Balanced Base: a same-scenario comparison,
exactly as §3.3 specifies.

The same reasoning does **not** extend to `dim_customer` and `dim_product`, where a wholesale
invoice genuinely has no customer and a payroll journal genuinely has no product. Those get
explicit "Not applicable" members, because there the absence is real rather than unrecorded.

## Alternatives considered

**A "Not applicable" scenario member.** The intuitive answer, and the one a reviewer is most
likely to expect — which is why this ADR exists rather than the decision being made silently.

Rejected because it breaks §3.3. It also encodes a claim that is not true: actuals are not
scenario-less, they are the outcome of one particular scenario, and the model has a member for
precisely that scenario. Recording "not applicable" would assert that the question does not
apply, when in fact the answer is known.

There is a second-order cost too. With actuals under N/A, any measure comparing actual to plan
must special-case the scenario filter, and that special case would appear in both the Python
semantic layer and the DAX — two places, guaranteed to drift.

**Duplicating actuals under every scenario.** Makes every comparison same-scenario and is
strictly worse: it multiplies the ledger by four, and it asserts that the same actual result
occurred under four different strategies, which is false.

## Consequences

Scenario is no longer a purely forward-looking dimension. Filtering to Balanced Base returns both
history and plan, which is what a variance report wants and may surprise someone expecting
scenario to mean "hypothetical".

The other three scenarios have **no actual periods**, which is correct and needs stating in the
semantic layer: a measure filtered to Wholesale Acceleration and version Actual returns nothing,
and that is a true answer rather than a missing-data bug. Any visual comparing scenarios over
history is comparing one real series against three empty ones, and the Power BI report must not
present that as four comparable lines.

A reviewer who expects "Not applicable" and finds Balanced Base should find this ADR first: the
contract's §3.3 annotation points here.
