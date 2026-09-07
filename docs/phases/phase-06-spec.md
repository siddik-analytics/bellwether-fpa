# Phase 6 — Board pack and automated variance commentary

Goal: the artifact the client-facing audience actually sees. A PDF that states Northlake's
position, argues a case, and explains its own variances in sentences a person would write.

This is the first phase whose deliverable is **prose**. Every phase so far produced numbers that
could be reconciled against the oracle; a sentence cannot be reconciled, only constrained. Most
of the design below is about what constraints make an automated sentence trustworthy.

Tag on completion: `v0.7-reporting`

---

## Carried defect — a first-class deliverable, not cleanup

### D-1 · The forecast ledger posts no financing

`forecast_ledger.post_financing` exists, is exported, and **is never called**.

| | |
|---|---|
| `fact_financing_monthly` carries | $370,351 interest, $245,310 unused line fees, revolver drawn to $2.0M |
| `fact_gl` posts to accounts 7000, 7010, 2500 | **nothing, in any period, in any scenario** |

Four consequences, and none is cosmetic:

1. **Net Income equals EBITDA in every period of every scenario**, because Other Income and
   Expense is structurally zero. The metric exists, the measure exists, and it is always 0.
2. **The balance sheet carries no revolver liability.** A company whose central question is
   whether it can fund itself shows no debt.
3. **The cash flow's interest line is zero**, so the statement ADR 0018 chose for its ability to
   explain the covenant does not contain the cost of the facility.
4. **`financing.py` remains a second source of truth** in exactly this respect — the thing ADR
   0014 and phase 3's D-1 claimed to have removed. The trial balance nets to zero *because the
   entries are absent*, not because they net.

Fixing it **moves cash, the borrowing base and every covenant figure.** The probe must be re-run
and the scenario table will move. That is the point: the covenant figures currently omit the cost
of the debt they are measuring headroom against.

It comes first because everything downstream reports these numbers. Writing the board pack on
figures that are about to change would mean writing it twice.

---

## The central design problem: commentary that explains rather than describes

The charter's success criterion is specific:

> Variance commentary reads as though a person wrote it. Specific, quantified, and attributed to
> a driver — *"gross margin fell 240bp, of which 180bp is channel mix"* — not *"revenue was below
> budget."*

The failure mode is templated prose with numbers substituted. `f"Revenue was {delta} versus
budget"` is not commentary; it is a table read aloud, and it is worse than a table because it
implies an analyst looked at it.

**The rule this phase is built on: a sentence may only make a causal claim the data can
support.** Concretely:

- Every **number** in the commentary comes from the semantic layer and is asserted equal to it.
- Every **causal claim** — "of which X is channel mix" — comes from a decomposition that
  computes X. If the decomposition cannot attribute the movement, the sentence does not claim to.
- A movement the model cannot explain is reported as **unexplained, with its size**. "Gross
  margin fell 240bp, of which 180bp is channel mix and 60bp is not attributable at this grain" is
  a true sentence and a more useful one than a confident guess.

That last point is the design. Most automated commentary is untrustworthy because it never says
"I don't know", so a reader cannot tell the explained from the asserted.

### What the decomposition can and cannot do

`semantic.decompose` returns three **magnitudes** — performance variance, forecast revision,
scenario difference — and no causes. A magnitude is not an explanation. Attribution needs a
bridge: price, volume, mix and rate effects that sum to the movement.

The transaction facts support a real bridge for **actual periods**: units, realised price and
channel mix are all measured per order line and invoice line. That is where the honest causal
claims come from, and R-1 below explains why it is also the only place they can come from.

---

## The COM export path

The pack is the client-facing artifact per the charter, so it goes through Excel:

| Step | API | Output |
|---|---|---|
| Compose | xlsxwriter, headless | exhibit sheets in the workbook |
| Recalculate and verify | `CalculateFullRebuild` + phase 5 reconciliation | agreement to 0.01 |
| PDF | `ExportAsFixedFormat` | `build/northlake-board-pack.pdf` |
| PNGs | `Range.CopyPicture` over **named ranges** | `build/exhibits/*.png` |

Additive only, as always. The COM stage composes nothing and computes nothing — every figure and
every sentence is produced headless, and Excel renders what it is given.

The workbook currently defines **no named ranges** (`define_name` is never called). PNG export
needs them, so phase 4's builder gains named ranges for each exhibit — a small change in the
layer that owns layout, not a COM-side workaround.

---

## The three carried exhibits

`docs/phases/phase-06-carried.md` holds three, recorded when each was discovered because the
reason it matters is clearest then. All three are first-class content, not appendices:

- **C-1 · the unallocated cost sensitivity** — what Supply Chain allocation would have been
  worth, as a range rather than a number. Answers the sceptical reader before they ask.
- **C-2 · both channels contribute; the loss is the corporate block** — reverses the conclusion
  a reader arrives with, and pairs it with the weaker, accurate claim about how the block grew.
- **C-3 · the EBITDA to borrowing base to covenant trace** — the only exhibit that explains why
  the strongest-revenue scenario is the one that breaches.

---

## Order of work

### 1. D-1, and the restatement it forces

Post financing through the ledger. Re-run the covenant probe. Re-check every figure the contract,
the README, the charter and the carried exhibits quote, because several will move.

### 2. The variance bridge

Price, volume, mix and rate attribution from the transaction facts, with an explicit unexplained
residual. This is the semantic-layer work the commentary depends on.

### 3. The commentary generator

Sentences composed from the bridge, in `transform/` — not in the workbook and not in the COM
stage, because commentary is an originated value like any other.

### 4. Exhibits and layout

The three carried exhibits plus the statements, as workbook sheets with named ranges.

### 5. The COM export

PDF and PNGs. Additive.

---

## Acceptance criteria

| # | Criterion | How it is checked |
|---|---|---|
| **D-1 — the carried defect** | | |
| 6.1 | Interest, unused line fees and revolver movements post to the ledger in every forecast period of every scenario | `tests/transform/test_financing_posted.py` |
| 6.2 | The trial balance still nets to zero for every period of every version and scenario | existing check, unamended |
| 6.3 | Net Income differs from EBITDA wherever the facility was drawn or a fee accrued | `tests/transform/test_financing_posted.py` |
| 6.4 | The balance sheet carries a revolver liability whose closing balance equals `fact_financing_monthly.revolver_drawn` every month | `tests/transform/test_financing_posted.py` |
| 6.5 | The cash flow's interest line equals posted interest, and closing cash still ties to balance sheet cash at 0.00 | existing tie, re-run |
| 6.6 | `financing.py` no longer computes any quantity the ledger also computes | import and call-graph assertion |
| 6.7 | The covenant probe is re-run and every figure it produces is recorded, including any that moved | `docs/adr/` entry + `samples/_verdicts.csv` regenerated |
| 6.8 | Every figure quoted in the contract, README, charter and carried exhibits is re-checked against the rebuilt model | script that greps quoted figures and asserts each |
| **The bridge** | | |
| 6.9 | A variance decomposes into price, volume, mix and rate effects that sum to the total within 0.01 | `tests/transform/test_bridge.py` |
| 6.10 | The residual is reported explicitly and is never silently absorbed into a named effect | `tests/transform/test_bridge.py` |
| 6.11 | Each effect is computed from measured quantities, not inferred by subtraction — except the residual, which is defined as the remainder | `tests/transform/test_bridge.py` |
| 6.12 | The bridge reproduces a known movement: FY2024 to FY2025 gross margin, decomposed, ties to the reported change | `tests/transform/test_bridge.py` |
| **The commentary** | | |
| 6.13 | Every number appearing in generated commentary is equal to the semantic layer's value for it | `tests/reporting/test_commentary.py` — parse the numbers back out of the prose |
| 6.14 | Every causal claim maps to a bridge component that computes it; a claim with no component fails the build | `tests/reporting/test_commentary.py` |
| 6.15 | An unexplained residual above a stated threshold is named as unexplained, with its size | `tests/reporting/test_commentary.py` |
| 6.16 | Commentary is deterministic: same data, same sentences | `tests/reporting/test_commentary.py` |
| 6.17 | No sentence is emitted for a movement below the materiality threshold, and the threshold is stated in the pack | `tests/reporting/test_commentary.py` |
| 6.18 | Commentary is generated in `transform/`; neither the workbook nor the COM stage composes a sentence | import-graph assertion |
| 6.19 | Direction words match the sign convention — a favourable cost variance never reads as a shortfall | `tests/reporting/test_commentary.py` |
| **The pack** | | |
| 6.20 | The pack states a central tension, supports it with numbers, and says what should be done | structural assertion on the composed sections |
| 6.21 | All three carried exhibits appear | `tests/reporting/test_pack.py` |
| 6.22 | Every figure in the pack equals the workbook's and Power BI's figure for the same thing | `tests/reporting/test_pack.py` |
| 6.23 | Every page carries the "illustrative company, synthetic data" note | `tests/reporting/test_pack.py` |
| 6.24 | No jargon appears that is not defined on the page it appears on | glossary assertion against a term list |
| 6.25 | The pack is composed headless; deleting the COM stage leaves a complete pack definition | CI on ubuntu |
| **Export** | | |
| 6.26 | `ExportAsFixedFormat` produces a PDF with the expected page count | `requires_excel` |
| 6.27 | Named ranges exist for every exhibit the case study needs | `tests/workbook/` |
| 6.28 | `CopyPicture` exports each named range to PNG at readable resolution | `requires_excel` |
| 6.29 | The export stage originates no value and composes no sentence | source assertion over `excel_stage/` |
| 6.30 | A human has opened the PDF and confirmed it renders | **manual gate**, named as manual — ADR 0022 |

---

## What the reporting layer makes newly problematic

### R-1 · Performance variance cannot be computed — Budget and Actual share no month

This is the largest finding and it invalidates part of §3.3 as written.

| Version | Periods |
|---|---|
| Actual | FY2023–FY2025 |
| Budget | FY2026–FY2028 |
| Prior / Latest Forecast | FY2026–FY2028 |

**There is no month in which both an Actual and a Budget figure exist.** §3.3's first
decomposition — "Performance variance: Actual vs Budget, same scenario" — is uncomputable on the
generated data, and `semantic.decompose` takes `actual` and `budget` arguments that can never
both be populated for the same period.

The other two decompositions are fine: forecast revision (Latest vs Prior) and scenario
difference both live entirely in the forecast years.

The charter's own example — *"gross margin fell 240bp, of which 180bp is channel mix"* — is a
**period-over-period actual** claim, not a variance against budget. That comparison is
computable, from the richest data in the project, and is arguably what a board pack for a company
with three years of history should lead on anyway.

Three ways out, and the choice changes what the pack argues:

1. **Generate a Budget for the actual years.** A FY2025 budget, frozen at the start of FY2025,
   against which FY2025 actuals vary. Most faithful to how planning works and the only option
   that makes §3.3 true as written. Costs a generator change and a contract amendment.
2. **Restate §3.3** so performance variance is defined against the *first forecast year*: Budget
   vs Latest Forecast within FY2026. Cheap, and it is a real comparison a board makes — but it is
   forecast-against-forecast, not performance.
3. **Lead the commentary on period-over-period actuals** and treat budget variance as a
   forecast-years-only section. Honest, uses the best data, and leaves §3.3 partly aspirational.

This needs deciding before the bridge is built, because the bridge's grain follows from it.

### R-2 · The forecast posts 18 accounts and 5 departments; actuals post 43 and 9

A variance can only be decomposed to the coarser of the two sides. Commentary attributing a
movement to a department can name five of the nine that exist, and the account sets are not
nested — actuals post `4020`, `4100`, `4110`, `4111`; the forecast posts `3900`, which actuals
never touch.

So a bridge between an actual and a forecast figure has a structural floor on how far it can
attribute, and the residual R-1's option 1 or 2 would produce is partly this, not analysis
failure. Whatever the pack says about attribution grain has to be true at both grains.

### R-3 · A magnitude is not an explanation, and nothing yet computes causes

`semantic.decompose` gives three numbers. The charter asks for *"of which 180bp is channel mix"*,
which requires effects that sum to a movement — price, volume, mix, rate.

For actual periods the transaction facts support this properly: quantity, realised price and
channel are all on the order and invoice lines. For forecast periods they do not exist, because
the forecast is posted at account grain with no units behind it except in the six near-term
months `near_term.units_and_cogs` covers.

**So the bridge is rich for actuals and thin for the forecast**, which points the same way R-1
does. It also means criterion 6.11 — effects computed rather than inferred by subtraction — is
achievable for actuals and only partly achievable for the forecast, and the spec should not
pretend otherwise.

### R-4 · Prose is the first deliverable with no reconciliation

Every artifact so far could be checked against the oracle by comparing numbers. A sentence
cannot. The criteria above constrain it in three ways — numbers parsed back out and asserted,
causal claims mapped to computing components, determinism — but none of that establishes the
sentence is *well written*, only that it is not lying.

That gap should be named rather than closed by a weaker test that appears to close it. Under
ADR 0022 the external authority for prose is a reader, and 6.30 is the manual gate.

### R-5 · The PDF is an artifact this project both writes and reads back

ADR 0022's third defect exactly. A test that opens our PDF and checks our own figures appear in
it proves the export ran, not that the pack is right — and a page-count assertion is close to
vacuous.

The external authority is a human opening it. That is 6.30, and it stays manual and named as
manual. Everything automatable is checked before the PDF exists, on the composed content.

### R-6 · Fixing D-1 moves figures that are quoted in seven places

The covenant figures appear in `docs/data-contract.md` §9, the README, `docs/charter.md`, ADR
0008, ADR 0018, `phase-06-carried.md` C-3 and `samples/_verdicts.csv`. Three of those are
prose that argues from the numbers, so a changed figure may change a sentence.

Criterion 6.8 exists because doing this by hand across seven documents is how one gets missed.

### R-7 · The pack will be the fourth consumer of the semantic layer

The workbook, Power BI and the sensitivity grids already consume it. The pack adds commentary,
which consumes the bridge. If the bridge lands anywhere but `transform/`, the project acquires a
second place financial logic lives — which is what ADR 0019 collapsed and what ADR 0020 drew a
boundary to prevent. 6.18 asserts it.

---

## Decisions needed before code

| # | Decision | Why it cannot be defaulted |
|---|---|---|
| G-a | **R-1: what performance variance means**, given Budget and Actual share no period | Changes §3.3, the bridge's grain and what the pack leads on |
| G-b | D-1: confirm the covenant figures are expected to move, and that the narrative may change with them | "Acceleration breaches May-2028" is the model's central result and it is computed without the cost of the debt |
| G-c | Whether the PDF is composed entirely through Excel, or a layout library is added | A PDF/layout dependency is a stop-and-ask; Excel-only needs no new dependency |
| G-d | Which exhibits get named ranges for PNG export | Phase 7 needs the case study and LinkedIn assets, and the list is easier to fix now |
| G-e | The materiality threshold for commentary, and whether it is stated in the pack | A financial convention, and the pack's credibility depends on it being visible |

**On G-a:** my recommendation is **option 1** — generate a Budget for FY2025. It is the only
answer that makes §3.3 true rather than restating it to fit the data, it produces the comparison
a board actually reviews, and it is the one a reviewer would expect to exist in a planning
system. It costs a generator change and a contract amendment, and it is the most work.

**On G-c:** Excel-only. `ExportAsFixedFormat` already produces the PDF, the workbook already
owns layout and theming, and a second layout engine would mean two places page composition is
decided.

---

## Not in this phase

No README rewrite, no case study, no video — phase 7. The PNGs are exported here because the COM
stage is already open; what is written around them is distribution work.

No new financial logic outside `transform/`. A figure or a sentence the pack needs that the
semantic layer cannot produce is a gap in the semantic layer, and the fix goes there.
