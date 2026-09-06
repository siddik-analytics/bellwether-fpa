# ADR 0022 — A test whose oracle is derived from the thing under test cannot fail

- **Status:** Accepted
- **Date:** 2026-09-06
- **Phase:** 5 (Excel/COM stage and Power BI)

## Context

Phase 5 shipped three tests that passed while verifying nothing. They were not sloppy, they were
not skipped, and none of them was found by reading the code. Each was internally consistent and
externally wrong, and each needed an authority outside the project to expose.

They are worth recording together because they are one defect wearing three costumes.

### 1. The reconciliation compared Excel to itself

The Excel harness read every formula cell through COM, called `CalculateFullRebuild`, and read
every cell again. The two reads agreed, so the workbook was declared to reconcile.

Excel evaluates formulas **as it opens a workbook**. The "before" read was already Excel's
answer, not the oracle's. The comparison was a value against itself and could not produce a
difference. Given a workbook whose cached value had been deliberately set to 999 where the
formula computes 142, it reported **zero differences**.

This was the reconciliation the whole architecture is built around — the one
`.claude/rules/excel-com.md` calls the strongest single artifact in the repo.

### 2. The TMDL test compared a rejected file to itself

Criterion 5.29 generated the Power BI project twice and asserted the bytes matched. They did.
The test passed on every run.

Power BI Desktop refused to open the file:

```
Parsing error type - Indentation
Document - './tables/dim_date'
Line 75 - '\tdataCategory: Time'
```

Byte-identical regeneration proves a generator is deterministic. It says nothing whatsoever about
whether the thing generated is valid, and a deterministic generator of invalid files satisfies it
perfectly.

### 3. The report was tested against a schema invented for the occasion

`report.json` was emitted in a readable shape of this project's own design: a list of pages, each
with a display name and a list of measure names. Six tests asserted against that shape —
page order, drillthrough targets, the disclosure on every page — and all six passed.

Power BI's report format is not that. It uses `sections`, stringified visual `config` documents,
and explicit geometry. The tests confirmed the file matched the schema the same author had made
up, which is a tautology dressed as coverage. Nothing in the suite could have noticed, because
the specification and the implementation had the same source.

### 4. And the same failure at one more remove

The validator written to catch defect 2 reported **14 errors on its first run, 11 of them false**.
Its grammar was wrong about properties written with `=` rather than `:`, so it flagged
`source = let ... in ...` on every table. The one real finding was buried in ten invented ones.

A checker with a wrong grammar is worse than no checker: it trains the reader to discount its
output, and it would have been "fixed" by relaxing it until the noise stopped — which is exactly
how a validator ends up validating nothing.

## Decision

**Name the general form and treat it as a review question, not a discovery:**

> A test whose expected value is derived from the thing under test cannot fail. It measures
> internal consistency and reports it as correctness.

Every one of the four had this shape. The oracle came from inside:

| Test | Where the expected value came from |
|---|---|
| Excel reconciliation | Excel, one read earlier |
| Byte-identical TMDL | the same generator, run twice |
| Report structure | a schema the generator's author defined |
| The TMDL validator | a grammar the same author assumed |

**Four countermeasures, all of them now in the repository rather than in this document:**

### 1. A planted-lie negative control

For any check that can pass vacuously, ship a fixture that is *known to be wrong* and assert the
check fails on it. `tests/excel/test_reconciliation.py::test_the_reconciliation_can_actually_fail`
builds a three-formula workbook with one cached value set to 999 and asserts exactly one
difference is found, at that cell, with that delta.

The rule this encodes: **a check nobody has watched fail is not evidence.** It is the cheapest
test in the repository and it is the reason the zero-difference result means anything.

### 2. Parse the written artifact; never re-derive it

The reconciliation now reads cached values out of the `.xlsx`'s own XML — the `<v>` elements
xlsxwriter wrote — rather than asking Excel what they are. `test_dax_semantics.py` reads the
measure text back out of `Measures.tmdl` rather than calling `measure_dax()` again.
`test_headless_parity.py` hashes the file the subprocess produced.

The rule: **if a test can obtain the expected value by running the code under test, it will, and
it must be denied the opportunity.** Reading the artifact is the denial.

### 3. Validate the validator against known-good input

Every negative case in `tests/powerbi/test_validate.py` is a defect the generator **actually
shipped**, not one imagined while writing the checker — the misplaced `dataCategory`, the
column-less table, the space indentation. Alongside them sit positive cases asserting the
validator stays silent on input it must accept, including the `=`-valued property that produced
its eleven false alarms.

The rule: **a checker needs both directions.** False negatives make it useless; false positives
make it ignored, which is the same outcome with more noise.

### 4. One external-authority gate per generated artifact

Every artifact this project generates must have at least one check whose verdict comes from
outside the project:

| Artifact | External authority | Status |
|---|---|---|
| `.xlsx` workbook | Excel, via COM — recalculates and reports | automated, `requires_excel` |
| TMDL semantic model | **Microsoft's own TMDL parser** (Tabular Object Model) | automated, `requires_tom` |
| Power BI report | Power BI Desktop — renders the pages | **manual**, criterion 5.30 |
| DAX measures | Power BI's engine — evaluates them | **manual**, criterion 5.15 |
| Parquet star | `pyarrow` round trip | automated |

The second row started as a manual gate and did not have to stay one. The Tabular Object Model
ships with DAX Studio and Tabular Editor and contains the **same deserializer Power BI Desktop
uses**, so the model can be parsed by the real authority headless. Looking for an automatable
authority before accepting a manual one is part of the countermeasure, not a refinement of it.

It justified itself on its first run. The project passed the project's own structural validator
and Microsoft's parser still rejected it:

```
Parsing error type - InvalidLineType
Detailed error - Unexpected line type: Empty!
Document - './tables/Measures'
Line Number - 5
```

A `///` line describes the object that follows it. A blank line between the two leaves it
describing nothing. The hand-written validator had no opinion about that, because its author had
not known the rule — which is the entire reason an authority outside the system is not optional.
Two hand-written checkers in sequence, each blind in the same place, are one checker.

Where the authority cannot be automated, the gate is **manual and named as manual**. It is not
replaced by a proxy that is then described as though it were the real thing.

## Rationale

The reason this is worth an ADR rather than four bug fixes is that **nothing in the code review
would have caught any of them.** Each test read correctly. Each asserted something true. The
defect was in the epistemology, not the logic: the answer key had been copied from the student.

It is also worth recording that the project's own documentation predicted this. The phase 5 spec
said, before any of it was built:

> This is a **weaker guarantee than phase 4's and should be stated as weaker**: it proves the DAX
> was generated from the definition, not that the DAX evaluates correctly.

That was correct and it was still not enough, because it located the gap at DAX evaluation. The
first real failure landed a level below, in the file grammar — somewhere the spec had implicitly
assumed correctness because generation and validation shared an author. **Naming a limitation is
not the same as bounding it**, and the parts of a system nobody thought to doubt are exactly the
parts with no external check.

The economics also favour the external gate strongly. Each of these took one round trip to a real
tool to find and minutes to fix. Cumulatively they would have shipped a repository whose central
claim — two independent implementations that cross-check — was false in a way a reviewer opening
the workbook would have discovered instead.

## Alternatives considered

**Treat each as an isolated bug and fix it.** The default, and what would have happened if the
third had not arrived. Rejected once the pattern was pointed out: three instances in one phase is
a property of how the tests were designed, not three coincidences.

**Require an external authority for everything, automated or not.** Rejected as impossible rather
than undesirable. There is no supported way to evaluate a DAX measure from a script; Power BI
Desktop is interactive and Windows-only. Demanding it would produce either a fabricated
substitute or a permanently red build, and the fabricated substitute is precisely defect 3.

**Drop the checks that cannot be externally verified.** Rejected: byte-identical regeneration is
still worth having — it catches a non-deterministic generator, which is a real failure — as long
as it is not mistaken for validity. The fix is to state what each check covers, not to delete it.

## Consequences

Criterion 5.31 (structural TMDL validation) and 5.32 (evaluating the emitted DAX against the star)
both exist because of this. Neither replaces the manual gate; both narrow what reaches it.

**Every future generated artifact inherits the fourth countermeasure.** The phase 6 board pack is
a PDF, and a PDF that this project both writes and reads back is defect 3 again with different
file extensions. Its external authority is a human opening it, and that needs to be in the phase 6
spec as a named gate rather than assumed.

The manual gates are a standing cost. `docs/phases/phase-05-spec.md` records 5.15 and 5.30 as not
done rather than quietly satisfied by their automated proxies, and that is the honest state to
leave a phase in.
