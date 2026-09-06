# ADR 0015 — `GM_CALIBRATION` is a plug (known defect, owned by phase 3)

- **Status:** Accepted as a known defect
- **Date:** 2026-09-06
- **Phase:** raised in 2 (generator), **owned by phase 3 (transformation layer)**

## The defect

`forecast.GM_CALIBRATION` is a hardcoded 3.1 percentage points subtracted from every forecast
gross margin, in every scenario and every year:

```python
blended = d["dtc_share"] * dtc_gm + (1 - d["dtc_share"]) * ws_gm - GM_CALIBRATION
```

It exists because `forecast._unit_economics` computes margin from *representative* per-unit
economics — one DTC order at the average AOV, one wholesale unit at the average price — while
the actuals compute COGS from *actual* units at effective-dated per-SKU cost. The two disagree
by about three points, for reasons ADR 0013 sets out: units per revenue dollar rise with the
wholesale mix, and recovered returns are reshipped and so consume cost twice.

Without the adjustment the forecast would step upward by three points at the FY2025/FY2026
boundary, which would be a visible discontinuity in the margin bridge and obviously wrong.

So the constant produces the right answer. It is still a plug: a single number, fitted once
against one year, applied uniformly to four scenarios that differ precisely in the channel mix
that caused the discrepancy. **Wholesale Acceleration reaches 45% wholesale by FY2028 and
Consolidation falls to 33%, and both currently receive the same 3.1 point adjustment.** The
adjustment should be larger for the first and smaller for the second, because it is a
consequence of mix. Being wrong in opposite directions on the two scenarios that bracket the
comparison is the worst place for this error to sit.

## Decision

**Replace it with a units-based forecast in phase 3.** Do not tune the constant per scenario in
the meantime — that would make the plug harder to see while leaving it a plug.

## Why phase 3

The correct forecast computes units from demand drivers, applies effective-dated landed cost per
product family, and derives COGS the same way the actuals do. That requires the semantic
definitions the phase 3 transformation layer builds: a single definition of landed COGS that
both actuals and forecast consume, rather than two implementations that need reconciling with a
constant.

Building it inside `forecast.py` now would mean writing that definition twice.

## Scope of the fix

1. The forecast derives units from drivers and costs them at effective-dated per-SKU landed cost.
2. `GM_CALIBRATION` is deleted, not tuned.
3. Forecast and actual gross margin come from one shared definition in the transform layer.
4. A test asserts continuity across the FY2025/FY2026 boundary — no step in blended gross margin
   larger than the change in channel mix accounts for — which is the assertion that would have
   caught this had it existed.

## Consequences of leaving it in place until then

Forecast gross margins in contract §7.6 are approximately right for Balanced Base, which is the
scenario the constant was fitted against, and drift for the others in proportion to how far
their channel mix moves from Balanced Base's. The direction is knowable: Acceleration's margin
is **overstated** and Consolidation's is **understated**, so the gap between the two scenarios is
narrower in the model than it should be.

That is worth stating plainly because it understates the case Consolidation makes. The scenario
comparison is therefore conservative rather than flattering, which is the better direction for
an error to run, but it is still an error and it is not left implicit.
