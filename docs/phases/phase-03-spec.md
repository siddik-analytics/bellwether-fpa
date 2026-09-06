# Phase 3 — Transformation layer, star schema and semantic definitions

Goal: turn the generated transaction ledger into a dimensional warehouse, and define every
financial metric **once**, in Python, where it can be tested without opening a BI tool. When
this phase is done, Power BI has nothing left to invent — it consumes definitions this layer
owns (ADR 0007), and a metric that disagrees between the two is a defect with one obvious side
to fix.

Tag on completion: `v0.4-warehouse`

---

## Carried defects — first-class deliverables, not cleanup

Two defects came out of phase 2 with this phase named as owner. They are listed first because
they are the reason parts of this phase exist, not items to sweep up at the end. Neither is
optional and neither should be the last thing built.

### D-1 · The forecast ledger does not balance — ADR 0014

Actual periods post double entry and the trial balance nets to zero. Forecast periods post one
side only: `forecast.to_ledger` maps seven P&L lines and a COGS line onto accounts and stops.

The consequence is not cosmetic. Because the forecast has no balance sheet, cash flow, working
capital and the borrowing base cannot be derived **from the ledger**, so `financing.py` computes
them from scenario drivers instead — making it a second source of truth for quantities the
ledger should own. They agree today only because the same drivers feed both.

Fixing it here rather than in phase 2 was deliberate: balancing the forecast means giving it the
same movement-level structure the actuals have, and that structure is what this phase builds.

### D-2 · `GM_CALIBRATION` is a 3.1pt plug — ADR 0015

A single constant is subtracted from every forecast gross margin in every scenario. It was
fitted against Balanced Base and is applied uniformly to four scenarios that differ in precisely
the channel mix that caused the discrepancy — Wholesale Acceleration reaches 45% wholesale,
Consolidation falls to 33%, and both receive the same adjustment. Acceleration's margin is
overstated and Consolidation's understated, narrowing the gap between the two scenarios that
bracket the whole comparison.

The fix is a units-based forecast sharing one definition of landed COGS with the actuals. The
constant is **deleted, not tuned**.

---

## Order of work

Conformance before facts, definitions before metrics, and the carried defects before the parts
that would otherwise be built on top of them.

### 1. Conformed dimensions and the bus matrix

Publish the bus matrix — every fact against every conformed dimension — before building either.
It is the artifact that shows whether the schema conforms, and writing it first is what surfaces
a dimension that two facts need and neither has.

Surrogate integer keys throughout. **No null foreign keys**: every dimension carries an explicit
"Not applicable" member for the facts that legitimately have no value for it, because a null
degrades silently in a BI tool while an explicit member is visible.

### 2. Fact tables

Seven operational facts plus the ledger, each at the grain the data contract declares, each
joined to conformed dimensions only. Facts do not carry descriptive attributes that belong on a
dimension.

### 3. Fix D-1: balance the forecast

Forecast posts full double entry including balance-sheet movements, per version and scenario.
`financing.py` then reads receivables, inventory and payables **from the ledger**, retaining
responsibility only for the facility rules — advance rates, eligibility, the covenant test.

### 4. Fix D-2: units-based forecast

Forecast derives units from drivers and costs them at effective-dated landed cost through the
same semantic definition the actuals use. Delete `GM_CALIBRATION`.

### 5. Semantic definitions

Every metric defined once, in `src/bellwether/transform/`, as a testable Python object carrying
its own grain, filter and format. Base measures first, then variants built on them — a filter
expression repeated across two metrics is a defect.

### 6. Reconciliation

The warehouse must reproduce the source. Revenue, gross profit and EBITDA computed from the star
schema tie to the same figures computed from the transaction facts and from the ledger, for
every version and scenario.

---

## Acceptance criteria

| # | Criterion | How it is checked |
|---|---|---|
| **Carried defects** | | |
| 3.1 | Trial balance nets to zero for **every period of every version and scenario**, not just actuals. Contract §9 check 11 applies unamended and its ADR 0014 annotation is removed. | `tests/transform/test_ledger_balance.py` |
| 3.2 | The forecast balance sheet balances: assets = liabilities + equity, every month, every version and scenario | `tests/transform/test_ledger_balance.py` |
| 3.3 | `financing.py` derives receivables, inventory and payables from the ledger. No working-capital figure is computed from scenario drivers. | `tests/transform/test_single_source.py` — assert the module imports no driver constants |
| 3.4 | Covenant results after D-1 match the phase 2 figures within tolerance, or the difference is explained and the contract amended | `tests/transform/test_covenants.py` |
| 3.5 | `GM_CALIBRATION` no longer exists anywhere in the source | grep assertion in `tests/transform/test_single_source.py` |
| 3.6 | Forecast COGS is derived from units × effective-dated landed cost, through the same definition the actuals use | `tests/transform/test_semantic.py` |
| 3.7 | **Product margin is continuous across the FY2025/FY2026 boundary at product-family × channel grain — all eight series, each within tolerance.** A uniform plug moves every series by the same amount; a genuine mix effect moves none of them, because mix is a reweighting across series rather than a shift within them. This is the assertion that would have caught D-2. | `tests/transform/test_continuity.py` |
| 3.7a | The delivery layer is continuous per DTC order and per wholesale unit — parcel, pick-and-pack and freight are per order or per unit, so they cannot be tested at product grain and are tested at theirs | `tests/transform/test_continuity.py` |
| 3.7b | Blended reported gross margin is continuous, and any step is explained by the mix change between the two periods | `tests/transform/test_continuity.py` |
| **Star schema** | | |
| 3.8 | A bus matrix exists in `docs/architecture.md` listing every fact against every conformed dimension | Read; and a test asserts the matrix matches the built schema |
| 3.9 | Every foreign key in every fact resolves to a dimension member. **Zero nulls in any key column.** | `tests/transform/test_conformance.py` |
| 3.10 | Every dimension that a fact legitimately lacks a value for carries an explicit "Not applicable" member | `tests/transform/test_conformance.py` |
| 3.11 | `dim_channel` exists and both revenue facts join to it | `tests/transform/test_conformance.py` |
| 3.12 | Type 2 dimensions have non-overlapping, gap-free validity ranges per natural key, and facts join on the version effective at the transaction date | `tests/transform/test_scd.py` |
| 3.13 | The date dimension is contiguous, marked as the date table, and no fact carries its own date attributes | `tests/transform/test_conformance.py` |
| 3.14 | No fact table carries a descriptive attribute available on a dimension | `tests/transform/test_conformance.py` |
| **Semantic layer** | | |
| 3.15 | Every metric is defined exactly once. A filter expression appearing in two definitions is a failure. | `tests/transform/test_single_source.py` |
| 3.16 | Every metric carries its grain, filter and format string in its definition, not at a call site | `tests/transform/test_semantic.py` |
| 3.17 | Every metric is computable in pure Python with no BI tool present | The suite runs in CI on Linux |
| 3.18 | Channel allocation is **data, not branching logic** — a mapping table from GL account and department to channel, with corporate explicitly unallocated (ADR 0010) | `tests/transform/test_allocation.py` |
| 3.19 | Contribution Profit is computable and the three-tier hierarchy holds: Gross Profit ≥ Contribution Profit ≥ EBITDA at every period | `tests/transform/test_semantic.py` |
| 3.20 | Gross-to-net ladders reconstruct from ledger accounts alone, both channels, every version and scenario | `tests/transform/test_gross_to_net.py` |
| 3.21 | All three variance decompositions are computable: performance (Actual vs Budget, same scenario), forecast revision (Latest vs Prior, same scenario), scenario difference (same version) | `tests/transform/test_variance.py` |
| 3.22 | Favourable variance is positive whether the line is revenue or cost, at every level | `tests/transform/test_variance.py` |
| **Drill path** | | |
| 3.23 | The §5 drill path resolves: board KPI → statement line → channel or department → product or account → underlying transaction | `tests/transform/test_drill.py` |
| 3.24 | Every GL amount in an actual period is traceable to the transaction facts that produced it | `tests/transform/test_drill.py` |
| **Reconciliation** | | |
| 3.25 | Revenue from the star schema equals revenue from the transaction facts, every period, every channel | `tests/transform/test_reconciliation.py` |
| 3.26 | EBITDA from the star schema equals EBITDA from the ledger, every period, every version and scenario | `tests/transform/test_reconciliation.py` |
| 3.27 | FY2023–25 calibration targets still hold after transformation — the warehouse does not quietly change a number | `tests/transform/test_reconciliation.py` |
| **Build** | | |
| 3.28 | `python -m bellwether.build` produces the warehouse headless, exits 0, leaves a clean tree | CI on ubuntu |
| 3.29 | Transformation completes within 60 seconds on CI hardware | Timed in CI |
| 3.30 | Two runs with the same seed produce byte-identical warehouse output | `tests/transform/test_determinism.py` |
| 3.31 | CSV samples regenerate for every new warehouse table | `tests/transform/test_conformance.py` |

---

## What the transform layer makes newly problematic

The same exercise as phase 2, where simulating inventory surfaced an infeasibility the
spreadsheet could not see. These are contract problems that conforming the schema exposes.
Each needs a decision before or during this phase; none is fixed here unilaterally.

### P-1 · Actual periods have no scenario, so the star cannot join

`generate.py` sets `scenario_name = ""` on actual ledger rows. An empty string is not a
dimension member, so `fact_gl` cannot join to `dim_scenario` for two thirds of its rows.

Worse, it makes the contract's own variance decomposition undefined. §3.3 requires *performance
variance = Actual vs Budget, same scenario* — but actuals have no scenario at all, so "same
scenario" cannot be evaluated. This is the sharpest instance of a problem that also affects
`dim_customer` (wholesale facts have no customer) and `dim_product` (the GL has no product).

**Options:** a "Not applicable" member in each dimension; or actuals mapped to the operating plan
scenario, which is defensible because Budget was approved under Balanced Base and comparing
actuals to it is what management does. These are not equivalent — the second makes
`Actual vs Budget` a same-scenario comparison and the first leaves it a cross-scenario one.

### P-2 · There is no conformed channel dimension

Channel is the most-used slicer in the whole model — §6.7 channel contribution, the §7.1 unit
economics, three of the four scenarios, and the board pack's central argument all cut by it. It
is currently **implicit in which fact table you are reading**: DTC lines are DTC because they are
in `fact_dtc_order_line`.

That works in Python and fails in a BI tool, where a user selecting "DTC" expects one slicer to
filter revenue, COGS, marketing and contribution together across facts. §4 lists Channel among
the management dimensions but the dimension table was never specified.

### P-3 · Channel allocation is stated as a principle, never as a mapping

ADR 0010 decides *contribution only, corporate unallocated*, and §6.7 names the direct costs.
Neither states which GL accounts and departments those are, so Contribution Profit is not
currently computable from the contract without someone inventing the mapping.

It has to be data rather than code, or it becomes a chain of conditionals nobody can audit — and
it is exactly the kind of rule a reviewer will ask to see.

### P-4 · The drill path is asserted but not supported

§5's data-retention principle requires drilling from board KPI to underlying transaction, and it
is a stated acceptance criterion. But `fact_gl` carries only account, department, date, version
and scenario. There is **no product key, no customer key, no order reference**, so a GL revenue
line cannot reach the order lines that produced it.

Closing this needs either extra keys on the ledger fact or an explicit bridge from
account × period to the transaction facts. It is a real design decision with a size cost, and it
should be made deliberately rather than discovered in phase 5 when the board pack needs it.

### P-5 · Consolidation's central mechanism is invisible in the data

The Consolidation scenario's drivers say the SKU count is cut to kill the class-C tail and
wholesale is pruned to the profitable tier. Both are real mechanisms with real effects on
inventory and DSO — and **neither appears in any fact**, because the forecast is monthly
aggregates with no product or account dimension.

So the scenario the board pack will argue for cannot be shown working. Power BI cannot display
which SKUs were cut, and no test can assert that the tail actually went away. Either the forecast
gains product and account grain for at least the near-term band (§8 already asks for SKU-level
planning in months 1–6), or the contract should stop describing a mechanism the model does not
represent.

### P-6 · "Returns" is ambiguous between the reserve and the receipt

The ledger books a refund liability at the point of sale (ADR 0002) and unwinds it when the
return arrives. Both hit account 4110. So "DTC returns for March" can mean the reserve booked on
March sales or the reserve released against March receipts, and the two differ by the lag.

§6.2's gross-to-net ladder says "less returns (7% of net merchandise sales)", which reads like
the first. The semantic layer must state which, once, or the ladder and the reserve
roll-forward will silently disagree.

---

## Decisions needed before code

All five are **resolved**. Each is a deliverable of this phase rather than an open question.

| # | Problem | Decision |
|---|---|---|
| D-a | P-1 · actuals have no scenario | **Actuals carry `Balanced Base`**, the operating plan — not a "Not applicable" member, which would make every performance variance a cross-scenario comparison and break §3.3. `dim_customer` and `dim_product` do get N/A members, because there the absence is real. **ADR 0016.** |
| D-b | P-3 · channel allocation | **A mapping table, as data.** Power BI needs the same mapping, and expressing it as code guarantees the two drift. This forces §6.7 to name which accounts and departments sit in unallocated corporate — vagueness that would otherwise have surfaced in phase 5, with a board pack attached. |
| D-c | P-4 · drill path | **A bridge table**, not extra keys on `fact_gl`. Widening the ledger breaks its declared grain, and most postings have no single product: a payroll journal, a fixed-cost accrual and an interest charge all have none. |
| D-d | P-5 · forecast grain | **Months 1–6 gain product and account grain.** §8 already commissions SKU-level inventory planning and known POs in that band, so monthly aggregates were under-delivery rather than a scoping choice. It also resolves P-5: Consolidation's SKU pruning becomes visible, and a scenario the board pack argues for whose mechanism cannot be shown is a claim rather than a model. |
| D-e | P-6 · returns ambiguity | **Reserve booked at sale**, per ADR 0002. The accounts are split — 4110/4120 contra-revenue for the reserve, 4111/4121 for the balance-sheet unwind — so the ladder reconstructs from ledger accounts alone. **ADR 0017.** |

### What D-b requires of the contract

§6.7 states the allocation principle and never the mapping. Producing the table means deciding,
explicitly, which GL accounts and departments are directly attributable and which are corporate.
The expected shape, to be confirmed against §6.7 when written:

| Attributable to DTC | Attributable to Wholesale | Unallocated corporate |
|---|---|---|
| Marketing / Ecommerce payroll and programme spend, payment processing, DTC parcel and pick-and-pack | Wholesale Sales payroll, wholesale freight and fulfilment, deductions, bad debt | Executive, Finance, People, Technology, Supply Chain / Operations |

Supply Chain sitting in corporate is the one worth arguing about: it serves both channels and
is large. ADR 0010 put it there deliberately, because splitting it needs a driver and every
candidate driver is contestable.

---

## Not in this phase

No oracle, no workbook, no Power BI. The semantic layer defines metrics and proves they are
computable and reconciled; consuming them is phases 4 and 5.

No new business logic. If a metric needs a convention the data contract does not state, that is
a stop-and-ask, not an implementation detail — the same rule that has produced every ADR in this
project so far.
