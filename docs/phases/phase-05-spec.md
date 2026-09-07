# Phase 5 — Excel/COM stage and Power BI

Goal: finish the two consumers. The COM stage recalculates the workbook and proves Excel agrees
with the oracle; Power BI presents the same semantic layer to a different audience. Neither
originates a value.

The phase has one governing test, and it is not a Power BI test. **Both consumers must be
deletable.** Remove `excel_stage/` and the headless build still produces a complete, correct
workbook. Remove `powerbi/` and nothing in the model changes. If either turns out to be
load-bearing, the oracle rule was never true — it was only untested.

Tag on completion: `v0.6-bi`

---

## Carried criteria — first-class deliverables, not cleanup

Three phase 4 criteria were written, specified and left unverified because no Excel automation
existed. They are listed first for the same reason phase 3 listed its carried defects first:
they are the reason parts of this phase exist, and they are not items to sweep up at the end.

### C-1 · 4.4 — Excel recalculation reproduces every value within 0.01

The whole phase 4 design rests on a claim that has never been executed: that
`write_formula(..., value=...)` writes a formula whose Excel-computed result equals the cached
value it was written with. Every formula in the workbook carries an oracle value, 1,877 of them,
and no Excel has ever recalculated one.

This is **the reconciliation test the architecture is built around** — two independent
implementations of the same specification, disagreeing loudly when either drifts. Until it runs,
the project has one implementation and a stored assertion about a second.

Open the built workbook, `CalculateFullRebuild`, read every formula cell back, and assert
agreement with the oracle to 0.01. Not a sample. Not the totals. Every cell that carries a
formula, because the failure mode this catches — a formula that is subtly wrong but whose cached
value is right — is invisible in any aggregate.

### C-2 · 4.5 — A native Data Table over the sensitivity grid

`transform/sensitivity.py` computes the grids and the workbook writes them as static numbers.
The COM stage lays a native Excel Data Table (`Range.Table`) over the same range, so the grid is
live for a reader who wants to change an input — without Excel having originated any of the
values it currently shows.

The reconciliation applies here too, and it is the sharper case: after the Data Table is
attached and the book recalculates, the grid must still equal what the oracle computed. A Data
Table that disagrees is Excel silently taking ownership of a figure.

### C-3 · 4.24 — The workbook opens without repair warnings

A repair warning means the file was structurally invalid and Excel rewrote it. Every value could
be correct and the deliverable would still be unusable, because the first thing a board member
sees is a dialog saying the file is damaged.

Open the workbook through COM and assert that Excel raised no repair. This is cheap and it is
the single check that protects the artifact a client actually receives.

### And the criterion those three exist to protect

**4.25 — deleting the COM stage leaves a complete, usable model.** It passed trivially in phase 4
because the stage was empty. It stops being trivial the moment the stage does something, which is
why it is restated here as 5.6 and given a real test rather than an argument.

---

## The central design problem: proving a negative without the tool

Phase 4's guarantee was strong because Excel could be driven from Python. Two implementations,
one harness, an exact comparison. Power BI has no equivalent. There is no supported way to
evaluate a DAX measure from a script in CI, and Power BI Desktop is Windows-only, interactive,
and not automatable the way Excel COM is.

So the question this phase has to answer is: **how do you prove Power BI has not redefined a
metric, when you cannot run its metrics?**

The answer is not to run them. It is to make redefinition structurally impossible:

**Every measure in the semantic model is generated from a `Metric` object in
`src/bellwether/transform/semantic.py`.** No DAX is hand-authored. The build emits the TMDL, a
test asserts that regenerating it reproduces the committed file byte for byte, and a second test
asserts that every measure in the model traces to a `Metric` and that every `Metric` appears as a
measure. A hand-edited measure fails the build. A metric that exists only in DAX cannot exist.

This is a **weaker guarantee than phase 4's and should be stated as weaker**: it proves the DAX
was generated from the definition, not that the DAX evaluates correctly. A translation bug would
be reproduced faithfully by both the generator and the test. Two things narrow the gap:

- A **local, marked reconciliation** (`requires_powerbi`) for anyone with Power BI Desktop:
  export the key measures against the same grain and assert agreement to 0.01. Run manually, at
  the phase gate, and recorded in the phase notes — not in CI, and not claimed as CI.
- **The translation surface is kept small.** If every derived measure is arithmetic over base
  measures, and every base measure is one filter over one column, the number of distinct DAX
  shapes is about four. Four shapes can be read and checked by eye once; a hundred hand-written
  measures cannot.

That second point is what B-1 below is about, and it is the precondition for the whole approach.

---

## The thin-consumer test

ADR 0007 positions Power BI as a consumer of the semantic layer, and W-1 reshaped that layer to
return series so the workbook and Power BI consume the identical thing. This phase tests the
positioning rather than assuming it.

The test is stated as a prohibition, because that is how it can fail loudly:

> **No DAX expression in `powerbi/` may contain business logic that does not appear in
> `src/bellwether/transform/`.** Concretely: no measure may reference an account code, an account
> type, a department, a channel-allocation rule, or a hardcoded rate. Those are the semantic
> layer's vocabulary, and their appearance in DAX means the definition now exists twice.

A grep-based assertion over the generated TMDL enforces it. It is crude and it is exactly right:
if a reviewer can find an account code in the DAX, the positioning failed.

**Three findings below say the positioning does not currently hold** — B-1, B-2 and B-4. Each is
a place where Power BI would be forced to invent something. They are the substance of this
phase, not caveats on it, and the honest outcome would be to fix them in the semantic layer
rather than to write DAX that happens to agree.

---

## Order of work

Carried criteria first, because the COM stage retires phase 4's outstanding risk and because
everything after it benefits from knowing the workbook survives a recalculation.

### 1. The COM stage

`pywin32`, a recalculation harness, and the three carried criteria. Additive only. The stage
opens what the headless build produced and never writes a financial value.

### 2. Headless parity, tested rather than asserted

An import-graph assertion that nothing outside `excel_stage/` imports it, plus a build that runs
with the package absent. CI on Linux is the standing proof.

### 3. Semantic layer extensions

B-1, B-2 and B-4 — whatever the decisions below settle. This is where the phase's real work is,
and it is in `transform/`, not in `powerbi/`.

### 4. TMDL generation

Star schema, date table, two separate dimensions per ADR 0007, measures generated from `Metric`.

### 5. Report pages

Four pages in the order `.claude/rules/powerbi-pbip.md` fixes: executive summary, P&L detail,
cash and working capital, unit economics. Drillthrough to transaction level from every summary
visual, through the GL bridge phase 3 built.

### 6. Reconciliation

The generated-not-authored assertions in CI, and the local `requires_powerbi` numeric check.

---

## Acceptance criteria

| # | Criterion | How it is checked |
|---|---|---|
| **Carried from phase 4** | | |
| 5.1 | Excel recalculation reproduces **every** formula cell within 0.01 — not a sample, not the totals | `tests/excel/test_reconciliation.py`, `requires_excel` — **1,879 of 1,879 cells, 0 differences** |
| 5.2 | A native Data Table covers each sensitivity grid range | `tests/excel/test_reconciliation.py`, `requires_excel` — 3 tables, `HasArray` asserted |
| 5.3 | After the Data Table is attached and the book recalculates, every grid value still equals the oracle within 0.01 | `tests/excel/test_reconciliation.py`, `requires_excel` — 16 grid cells, 0 differences |
| 5.4 | The workbook opens through COM with no repair warning | `tests/excel/test_reconciliation.py`, `requires_excel` — `Workbook.Saved` on open |
| 5.5 | The COM stage writes no financial value — it only recalculates, formats, attaches and exports | `tests/excel/test_reconciliation.py` — source assertion over `excel_stage/` |
| **Headless parity** | | |
| 5.6 | With `excel_stage/` absent, `python -m bellwether.build` produces the same workbook, byte for byte | `tests/test_headless_parity.py` — SHA-256 against a fresh headless build, twice |
| 5.7 | No module outside `excel_stage/` imports `bellwether.excel_stage` | `tests/test_headless_parity.py` — import-graph assertion |
| 5.8 | Every phase 4 statement and tie assertion passes against the headless workbook, with no Excel installed | CI on ubuntu, with `pywin32` unresolvable |
| 5.9 | The COM stage is idempotent: running it twice leaves the workbook in the same state | `tests/excel/test_reconciliation.py`, `requires_excel` — second run attaches nothing |
| **Power BI is a thin consumer** | | |
| 5.10 | Every measure in the TMDL is generated from a `Metric` in `transform/semantic.py`; regeneration reproduces the committed file byte for byte | `tests/powerbi/test_generated.py` |
| 5.11 | Every `Metric` in `ALL_METRICS` appears as a measure, and every measure traces to a `Metric` — the mapping is total in both directions | `tests/powerbi/test_generated.py` |
| 5.12 | No DAX expression references an account code, account type, department, allocation rule or hardcoded rate | `tests/powerbi/test_generated.py` — greps every account code, type and department |
| 5.13 | No metric is defined in DAX that does not exist in the semantic layer | `tests/powerbi/test_generated.py` |
| 5.14 | Channel contribution in Power BI resolves through the same allocation mapping table, with no DAX conditional deciding which cost belongs where | `tests/powerbi/test_generated.py` + `tests/transform/test_star_boundary.py` — ADR 0020 |
| 5.15 | Key measures reconcile to the oracle within 0.01, **evaluated by Power BI's own engine** | `tests/powerbi/test_xmla_reconciliation.py`, `requires_powerbi` — XMLA against the live instance; skips when Desktop is closed |
| **Model conventions** | | |
| 5.16 | PBIP text format only; no `.pbix` or `.pbit` anywhere in the tree | `tests/powerbi/test_generated.py` and the existing pre-commit hook |
| 5.17 | Version and Scenario are two separate dimensions, never combined and never parallel fact tables — ADR 0007 | `tests/powerbi/test_generated.py` |
| 5.18 | A dedicated date table, marked as the date table; auto date/time disabled | `tests/powerbi/test_generated.py` |
| 5.19 | All measures live in one measures table, organised into display folders from `Metric.display_folder` | `tests/powerbi/test_generated.py` |
| 5.20 | All relationships are single-direction | `tests/powerbi/test_generated.py` |
| 5.21 | No calculated columns without a stated reason in the TMDL comment | `tests/powerbi/test_generated.py` |
| 5.22 | Format strings come from `Metric.format_string`, set on the measure and never on a visual | `tests/powerbi/test_generated.py` |
| 5.23 | Favourable variance is positive for both revenue and cost lines, and the convention is stated once at the top of the measures file | `tests/powerbi/test_generated.py` |
| 5.24 | Scenarios carry no ordinal sort column and no diverging colour ramp — they are not upside/base/downside | `tests/powerbi/test_generated.py` |
| 5.25 | Budget under a non-Balanced-Base scenario renders as an explicit "not applicable", never as blank or zero | `tests/powerbi/test_generated.py` |
| **Report** | | |
| 5.26 | Four pages, in the order the rules file fixes | `tests/powerbi/test_generated.py` |
| 5.27 | Every summary visual has drillthrough to transaction level, through the phase 3 GL bridge | `tests/powerbi/test_bound_fixture.py` — cards bound, drillthrough target declared as Desktop declares it. **Rendering still manual (5.30)** |
| 5.28 | Every page carries the "illustrative company, synthetic data" note | `tests/powerbi/test_bound_fixture.py` — a real textbox on every page, plus the model description |
| **Build** | | |
| 5.29 | `python -m bellwether.build` regenerates the TMDL; a hand-edited measure fails the build | `tests/powerbi/test_generated.py` + the CI clean-tree step |
| 5.30 | The PBIP project is valid enough to open in Power BI Desktop without error | **Met** — opens in Desktop, five pages, all visuals rendering |
| 5.31 | The generated TMDL is structurally valid: tab indentation, legal nesting, and every object property before its first child | `tests/powerbi/test_validate.py` — added after Desktop rejected the first project |
| 5.32 | The **emitted** DAX text, evaluated against the star, reproduces the semantic layer within 0.01 | `tests/powerbi/test_dax_semantics.py` — not Power BI's engine; see the note there |
| 5.33 | The semantic model parses under **Microsoft's own TMDL deserializer** (Tabular Object Model), with its conventions read back from the parsed model | `tests/powerbi/test_tom_authority.py`, `requires_tom` — **parsing only**; Desktop applies further rules, see 5.36 |
| 5.34 | Every generated `$schema` and metadata version equals Power BI Desktop's own, and the validator accepts Desktop's TMDL | `tests/powerbi/test_schema_fixture.py` — oracle is `tests/fixtures/powerbi-desktop-blank/`, not a transcribed constant |
| 5.35 | Every generated visual container matches Power BI Desktop's own shape — schema, key set and visualType vocabulary | `tests/powerbi/test_visual_fixture.py` — oracle is `tests/fixtures/powerbi-desktop-visuals/` |
| 5.36 | Every object name passes **Power BI Desktop's own `NameValidator`**, not only TMDL parsing | `tests/powerbi/test_tom_authority.py`, `requires_tom` — caught `Measures`, which TOM accepted and Desktop refused |
| 5.37 | Every `Entity` and `Property` in the report resolves against the model as TOM parsed it | `tests/powerbi/test_bound_fixture.py`, `requires_tom` — 14 references, 0 unresolved |

---

## What the BI layer makes newly problematic

### B-1 · `Metric` declares dependencies but not derivations — Power BI would have to invent the arithmetic

This is the finding the phase turns on, and it says the thin-consumer positioning **does not
currently hold**.

`Metric` carries `depends_on`, and nothing else about how the dependency is used:

```python
"Net Revenue":    depends_on=("Gross Revenue", "Contra Revenue")   # subtract
"Gross Margin %": depends_on=("Gross Profit", "Net Revenue")       # divide
"EBITDA":         depends_on=("Contribution Profit",)              # ...less corporate
```

Nothing in the definition says subtract, divide, or less-corporate. The arithmetic lives in
`evaluate_ladder()`, and again in `statements.metric_series()`, which computes the same ladder a
second time with the operations written out longhand. **It is already duplicated inside Python.**
Generated DAX would be the third copy, and hand-written DAX would be a third copy that drifts.

So a `Metric` cannot currently be translated into a measure. Any generator would have to carry a
lookup table of "which operation goes with which dependency pair", which is the definition living
in the generator rather than in the semantic layer.

**The fix belongs in `transform/`, not in `powerbi/`:** give `Metric` an explicit derivation —
an expression over named dependencies — and generate the Python evaluation *and* the DAX from
the same field. That collapses three copies of the ladder into one, and it is the precondition
for the small translation surface the whole verification approach depends on.

It is also a change to how §6 metrics are expressed, so it needs a decision and an ADR.

### B-2 · The BY_UNITS split happens after the star, so Power BI cannot see it

`star.channel_key_for_ledger` resolves BY_UNITS rows — shared cost of goods, accounts 5000
through 5320 — to the **corporate** channel member, and `semantic.channel_contribution` splits
them by units afterwards, "in the semantic layer, where the unit counts live".

Power BI reads the star. It sees those costs as corporate. To reproduce the channel contribution
the board pack turns on — the $774k / $732k / −$2,810k table — it would have to re-implement the
units-based allocation in DAX. That is business logic Power BI would own, and it is the specific
failure ADR 0010 and the allocation mapping table were built to prevent.

Two ways out, both in `transform/`:

1. **Resolve the split at star-build time.** Emit the allocated rows into the fact, so channel
   contribution in Power BI is a group-by rather than a calculation. Costs a row multiplication
   on shared COGS and makes the fact table the single place the allocation is expressed.
2. **Emit a units-by-channel-by-month bridge** the model filters through, so the ratio is data
   rather than DAX.

Option 1 is cleaner and arguably where the allocation always belonged; option 2 preserves the
current shape. Either way §6.7 currently says the split happens in the semantic layer, so
changing it is a contract amendment rather than an implementation detail.

### B-3 · The workbook already reports metrics the semantic layer does not define

`statements.metric_series` returns **Net Income** and **Other Income and Expense**. Neither is in
`ALL_METRICS`. The workbook renders them; `definitions_frame()` — documented as "what Power BI's
measure table is generated from" — does not know they exist.

So criterion 5.11's mapping is not total today, and the gap is on the Python side. Either they
become `Metric` objects or the statements stop reporting them, and the first is obviously right.
Small, but it is the same class of defect as B-1: a value that exists without a definition.

### B-4 · Variance direction is an argument, not metric metadata

`semantic.variance(actual, comparison, is_cost)` takes the sign convention as a parameter.
`Metric` has no `is_cost` field, so a generated variance measure cannot know whether favourable
is higher or lower — the generator would have to hold its own list of which measures are costs.
Same shape as B-1, same fix: the property belongs on the definition.

Criterion 5.23 cannot be satisfied honestly without this.

### B-5 · Facts are stored in integer cents

§2.1 stores monetary values in fact tables as integer minor units. Power BI reading the Parquet
gets cents. Dividing by 100 in DAX is Power BI transforming values — small, but it is a
transformation the semantic layer did not authorise, and it would appear in every money measure.

Cleanest is a conversion at the model boundary, so DAX never scales anything. Where that boundary
sits is a decision.

### B-6 · Budget exists only under Balanced Base, and a slicer will produce blanks

The workbook solved this with a guard cell and a visible "not applicable", because a blank cell
reads as zero. Power BI has the same asymmetry and a worse default: an empty visual looks like a
rendering failure, and a blank in a variance measure silently becomes the full value of the other
side.

This needs an explicit measure that states the combination was never approved — the same answer
as phase 4, in a different tool. Criterion 5.25.

### B-7 · There is no way to run DAX in CI, so this phase's guarantee is weaker than phase 4's

Stated in full above, and repeated here so it is not lost in the design section: the CI-level
proof is that measures are **generated** from the semantic layer, not that they **evaluate**
correctly. The numeric reconciliation is local and marked.

This is a real reduction in assurance between phase 4 and phase 5, and the spec should not
pretend otherwise. It is also the strongest available option short of shipping a DAX interpreter,
and the generation approach removes the failure mode that actually occurs in practice — someone
editing a measure in the tool and forgetting to change the model.

### B-8 · Scenario non-monotonicity is a convention no assertion currently protects

`.claude/rules/powerbi-pbip.md` forbids ordering or colouring scenarios as upside/base/downside,
because Wholesale Acceleration carries higher revenue and worse cash. That is a real trap: it is
the natural thing for a report author to do, it looks correct, and it inverts the central finding.

Criterion 5.24 turns it into a test — no ordinal sort column on `dim_scenario`, no sequential or
diverging colour ramp bound to scenario. Worth stating that this is the first report-level
convention in the project with a test behind it, and that the test is necessarily shallow: it
catches the mechanism, not every way a chart could mislead.

---

## Decisions needed before code

| # | Decision | Why it cannot be defaulted |
|---|---|---|
| F-a | **`pywin32` as a dependency** — Windows-only, required for COM | `CLAUDE.md` makes a dependency, especially a Windows-only one, a stop-and-ask |
| F-b | B-1: give `Metric` an explicit derivation, and generate both the Python evaluation and the DAX from it | Changes how §6 metrics are expressed; collapses three copies of the ladder into one; needs an ADR |
| F-c | B-2: where the BY_UNITS split resolves — in the star, or as a units bridge | §6.7 currently says the semantic layer, so either answer amends the contract |
| F-d | B-5: where cents become dollars for the BI model | Affects every money measure; the wrong answer puts a transformation in DAX |
| F-e | Whether 5.15's numeric reconciliation is a phase gate requirement or best-effort | It cannot run in CI, so it depends on your access to Power BI Desktop |

**On F-a:** `pywin32` is the standard COM binding and the only realistic option. It must not be a
hard runtime dependency — the Linux build has to install and run without it — so it belongs in an
optional extra (`[project.optional-dependencies] excel`), imported lazily inside `excel_stage/`
and never at package import time. Criterion 5.6 fails if that is got wrong, which is the point of
5.6.

**On F-b:** this is the phase's real work and it is worth stating why it is worth doing rather
than routing around. The ladder currently exists three times in Python — `evaluate_ladder`,
`metric_series`, and the workbook's `DERIVATIONS` table. They agree today. A single definition
that all three are generated from is the thing ADR 0007 claimed the project already had.

---

## Not in this phase

No board pack, no variance commentary, no PDF composition beyond what the COM stage exports as a
packaging step. Interpreting the model is phase 6, and `docs/phases/phase-06-carried.md` already
holds three exhibits waiting for it.

No new financial logic. A figure Power BI needs that the semantic layer cannot produce is a gap
in the semantic layer, and the fix goes there — that is the entire content of B-1 through B-4,
and routing any of them into DAX would make this phase a demonstration that the architecture does
not hold.
