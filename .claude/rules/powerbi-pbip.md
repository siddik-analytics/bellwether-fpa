---
paths:
  - "powerbi/**"
---

# Power BI (PBIP)

## Format

PBIP only. The semantic model serialises to TMDL and the report to JSON, both of which diff
properly in git. Never save or commit a `.pbix` — a binary here defeats the point of the repo
being reviewable.

DAX arriving in a pull request as reviewable text is uncommon in a finance portfolio. It is a
deliberate differentiator; protect it.

## Semantic layer

The semantic layer is defined in `src/bellwether/transform/`, with Power BI as a thin consumer.
Power BI does not invent business logic. See the ADR for why this direction was chosen — it is
the position a Financial Systems audience will expect and the one that survives a tool change.

In practice: if a metric definition needs to change, it changes in the transformation layer
first, and Power BI follows.

## Model conventions

- Star schema. Facts narrow, dimensions wide. No snowflaking without an ADR.
- A dedicated date table, marked as the date table. Never rely on auto date/time — disable it.
- All measures live in a single dedicated measures table, organised into display folders.
- Single-direction filters. Bi-directional filtering requires an ADR explaining the
  ambiguity it introduces and why it is acceptable.
- Prefer a measure to a calculated column. A calculated column needs a stated reason.
- Scenario (actual / budget / forecast) is a dimension, not three parallel fact tables.

## DAX conventions

- Base measures first, then variants built on them. Do not repeat a filter expression across
  measures — factor it.
- Use variables (`VAR`) for anything referenced twice or for readability of nested logic.
- Time intelligence goes through the date table, never through raw date arithmetic.
- Variance measures are explicit about direction and sign convention. Document the convention
  once, at the top of the measures file, and follow it everywhere: favourable variance is
  positive, regardless of whether the line is revenue or cost.
- Format strings set on the measure, not on the visual.

## Naming

- Measures: business language, title case — `Gross Margin %`, `Revenue vs Budget`.
- Columns: business language, no `_` and no source-system names surfaced to the user.
- Internal/helper measures prefixed `_` and hidden.

## Report pages

Four pages, in this order: executive summary, P&L detail, cash and working capital,
unit economics. Drillthrough to transaction level from every summary visual.

## Verification

Key measures must reconcile to the oracle. Export the relevant figures and assert agreement —
a dashboard that disagrees with the model is worse than no dashboard, and this is exactly the
failure a reviewer will probe for.
