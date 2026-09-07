# Power BI Desktop's visual containers, as a fixture

A report saved by Power BI Desktop containing one visual of each of **24 types**, kept so the
project's generated visuals can be checked against the real shape rather than an imagined one.

The companion to `../powerbi-desktop-blank/`. That one settled the project and report file
layout; this one settles what a visual is.

## What it proves

Every one of the 24 visuals has the same envelope:

```json
{
  "$schema": ".../visualContainer/2.12.0/schema.json",
  "name": "1af60d5e5ac0204c9d49",
  "position": { "x", "y", "z", "height", "width", "tabOrder" },
  "visual": { "visualType": "cardVisual", "drillFilterOtherVisuals": true }
}
```

That uniformity across 24 types is what makes it safe to generate from. It also settled a name
that would otherwise have been guessed: the modern card is **`cardVisual`**, not `card` — the
name the earlier invented report format used, which Power BI does not recognise.

## What it does **not** contain — and what therefore is not generated

Every visual in this reference is an **unbound placeholder**. There is no `query`, no
`projections`, no `queryRef`, no field reference of any kind. Dropping a visual on the canvas
without assigning a field produces exactly this, so:

- **The container shape is authoritative. The field binding is still unknown.**
- There is **no textbox** among the 24 types.

So the generator emits real, correctly shaped visual containers with no measure bound, and
`tests/powerbi/test_visual_fixture.py` asserts that a binding has *not* appeared. Two tests
there assert the absence deliberately, and both are written to **fail** if a future reference
carries a binding or a textbox — that failure is the signal that the gap can be closed, not a
regression.

Criteria 5.27 (drillthrough from every summary visual) and 5.28 (a disclosure textbox on every
page) stay open for this reason. The disclosure currently lives on the semantic model's own
description, where Microsoft's parser confirms it.

## To close the remaining gap

In Desktop, on one page: drop a **card** and assign a measure to it, add a **textbox** with any
text, and set a page as a **drillthrough target** with a field in the drillthrough well. Save to
a scratch directory and hand over the path. Three visuals is enough — the shapes are what matter,
not the content.

## Exclusions and one alteration

`.pbi/` (a machine-bound DPAPI credential signature and a binary cache) and
`StaticResources/` (99 KB of Microsoft's stock theme) are not copied, for the same reasons as
the blank fixture. Line endings were normalised to LF by this repository's own hooks; nothing
else was touched.
