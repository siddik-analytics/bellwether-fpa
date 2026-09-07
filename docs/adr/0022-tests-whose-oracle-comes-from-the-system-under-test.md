# ADR 0022 — A test whose oracle is derived from the thing under test cannot fail

- **Status:** Accepted
- **Date:** 2026-09-06
- **Phase:** 5 (Excel/COM stage and Power BI)
- **Amended:** 2026-09-06, phase 6 — a sixth instance, and the countermeasure it needed

## Context

Phase 5 shipped five defects of one kind: tests that passed while verifying nothing, and an
artifact that was wrong because of what had been left out of it. Phase 6 added a sixth, where the
test was never written at all. They were not sloppy, they were not skipped, and none of them was
found by reading the code. Each was internally consistent and externally wrong, and each needed an
authority outside the project to expose.

They are worth recording together because they are one defect wearing several costumes.

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

### 5. The omission variant — and this one was the cause

The four above are all cases of **inventing** something: a schema, a comparison, a grammar. The
fifth is its mirror image, and it is the one that actually stopped Power BI Desktop from opening
the report.

`report.json` was generated without `themeCollection`, `objects` and `resourcePackages`, and
neither artifact had a `.platform` file. Every one of the three Desktop references carries all
four. The reasoning at the time was recorded in the code and sounded like care:

> The theme collection and resource packages are deliberately omitted: they point at a 99 KB
> stock theme file this repository does not ship.

Every clause of that is true. Declining to redistribute 99 KB of Microsoft's content is a
defensible instinct in a repository that bans committed binaries. And it produced **an artifact
Desktop had never seen** — a report definition naming no base theme, which is a shape none of the
references produce and which failed to load with a dialog carrying no detail at all.

Restoring all four fixed it. `report.json` is now byte-equivalent in every key to what Desktop
writes for a blank project, and the project opens with all five pages rendering.

**Removing what every reference carries is the same defect as inventing what none carry.** The
oracle is still the author's judgement rather than an external authority; the only difference is
the direction. And the omission is *harder to catch*, for three reasons:

- **It looks like restraint.** Inventing a schema URL feels like a guess while writing it.
  Dropping a file feels like discipline, and the justification writes itself.
- **The result is tidier**, so it survives review. A reviewer sees a smaller, cleaner
  `report.json` and has no reason to ask what is missing — nothing is there to look wrong.
- **Nothing points at it.** An invented value is present and can be compared to something. An
  absent key is not in the diff unless the diff is run the other way round, against the
  reference, asking what *it* has that we lack. That comparison was not being made.

The countermeasure is a direction, not a new check: **diff both ways.** Countermeasure 2 says to
parse the written artifact rather than re-derive it; this adds that comparing generated to
reference catches inventions, and comparing reference to generated catches omissions. Only the
second finds this class, and it is now how the report shell is tested.

There is a quieter lesson about scope. Excluding the theme from the *fixtures* was right — a
fixture needs the shapes, not Microsoft's stylesheet. Excluding it from the *generated artifact*
was wrong, because there the file is a functional dependency rather than reference material. The
same reasoning was applied to two things that only looked alike.

### 6. Agreement by shared construction — the variant with no test at all

Added in phase 6.

The first five are tests that could not fail. The sixth is the case where **no test was written**,
because agreement seemed to follow from how the thing was built.

Criterion 6.22 says every figure in the board pack equals the workbook's and Power BI's figure for
the same thing. It was recorded as met, with this justification:

> Shared source: every figure comes from the same semantic layer the workbook and PBIP read.

That is true, and it is the architecture working as intended, and it is not a test. It is the
oracle-from-the-system-under-test failure with the test removed: the reason the three artifacts
agree is a property of the code that generates them, asserted by the person who wrote that code.
Nothing forced the three to meet, and this is the criterion behind the README's strongest claim.

The failure it cannot see is **staleness**. A workbook built from one run of the generator and a
Power BI model refreshed from another will disagree in every figure while every by-construction
argument still holds — each artifact is internally consistent with the code, and the code is
consistent with itself. The existing checks would all pass. `tests/powerbi/` already reconciled
the engine against the semantic layer *as it is now*, which is precisely the check a stale
artifact survives.

The countermeasure is countermeasure 2 applied across artifacts rather than within one:
**compare built artifacts to each other, not each to the code.** Two legs, each reading files
rather than calling generators —

| Leg | One side | Other side | Runs |
|---|---|---|---|
| pack ↔ workbook | the composed pack | `build/northlake-model.xlsx`, read from the file | headless, in CI |
| workbook ↔ Power BI | that same workbook file | the engine hosted by Desktop | `requires_powerbi`, local |

Neither leg has Python arithmetic in the middle. `workbook/read.py` reads the workbook's own row
labels and month headers out of the XML rather than reconstructing the layout, so a row moving is
a changed key rather than a silently shifted value; `reconcile.cached_values` now delegates to it,
since reading the artifact back was never a COM concern.

This is also the answer to a fair objection: a by-construction argument is *evidence*, and often
good evidence. The problem is not that it is weak. The problem is that it is unfalsifiable, so it
gets stronger as the system gets more complex, which is exactly backwards.

## Decision

**Name the general form and treat it as a review question, not a discovery:**

> A test whose expected value is derived from the thing under test cannot fail. It measures
> internal consistency and reports it as correctness.

Every one of them had this shape. The oracle came from inside:

| Test | Where the expected value came from |
|---|---|
| Excel reconciliation | Excel, one read earlier |
| Byte-identical TMDL | the same generator, run twice |
| Report structure | a schema the generator's author defined |
| The TMDL validator | a grammar the same author assumed |
| The report shell | a judgement about what could be left out |
| Pack, workbook and Power BI agreeing | the shared code that generates all three |

The fifth row is the omission variant. Its oracle was not a wrong value but a wrong *boundary* —
the author deciding which parts of the reference mattered, which is the same act of substituting
internal judgement for an external authority.

**Countermeasures, all of them now in the repository rather than in this document:**

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

And **diff in both directions.** Generated-against-reference catches what was invented;
reference-against-generated catches what was dropped. The second direction is the one nobody runs
by default, and it is the only one that finds a missing file.

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

| Artifact | External authority | Covers | Status |
|---|---|---|---|
| `.xlsx` workbook | Excel, via COM | recalculation of every formula | automated, `requires_excel` |
| TMDL semantic model | TOM — Microsoft's TMDL parser | **the metadata format only** | automated, `requires_tom` |
| TMDL object names | Desktop's own `NameValidator` | one of Desktop's rules on top | automated, `requires_tom` |
| Power BI report | Power BI Desktop | rendering the pages | **manual**, criterion 5.30 |
| DAX measures | Power BI's engine | evaluating them | **manual**, criterion 5.15 |
| Parquet star | `pyarrow` round trip | serialisation | automated |

### An authority can be real and still not be the whole authority

The TMDL row was moved from manual to automated on the strength of TOM parsing the model, and
that was **overstated**. Desktop then refused the same model:

```
Unsupported Table name "Measures" has been found in data model schema.
```

TOM validates the metadata format. Power BI Desktop applies its own rules **on top** of a model
that parses. So "the authority accepts it" was true and "Desktop will open it" did not follow,
and the table above now says what each authority covers rather than only that one exists.

This is the same failure as the other four, one level up: the *scope* of a check was inferred
from the check itself rather than established from outside it. A gate that is real but partial,
described as though it were total, buys exactly the false confidence this ADR is about.

**The fix was not another manual round trip**, and that matters, because the reflex after being
burned is to send everything back to a human. The rule turned out to be readable: Desktop's
`Microsoft.PowerBI.Modeling.Engine.dll` contains `ModelSchemaValidator.EnsureValidObjectName`,
whose IL is ten instructions and says

```
name != NameValidator.RemoveInvalidNameCharacters(name, objectType)  ->  reject
```

It is not a reserved-word list — it is a sanitiser, and the rejection is the *inequality*.
`Measures` comes back as `Measures 1`. Calling that method directly over every object in the
model found exactly one offender and cleared every other name, which no amount of careful
guessing would have established. It is now `tom.validate_names`, and it runs on every build.

**Prefer an executable authority to a human one**, in this order: run the real component if it
can be run; read the real rule if it can be read; ask a person only when neither is possible. The
suspected cause here — the hidden placeholder column and the partition added earlier — was
plausible, was the obvious thing to send back for a fixture, and was **wrong**.

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
replaced by a proxy that is then described as though it were the real thing — and where it *can*
be automated, what it covers is named too, because a partial gate sold as a total one is the
same error wearing a lab coat.

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

**A checker's silence is evidence only about what it checks.** Two more gaps surfaced the moment
the table was renamed, both invisible to the project's own validator and both reported instantly
by Microsoft's parser: a declaration whose name contains a space must be quoted (`partition Key
Figures = m` parses as a name plus a stray token), and the generator left the old `Measures.tmdl`
behind on rename, so the model contained both tables and kept failing. Neither was caught by the
hand-written validator, and the first attempt to add the quoting rule to it was over-strict
enough to reject valid files — which is how a checker gets relaxed until it is mute.

**Every future generated artifact inherits the fourth countermeasure.** The phase 6 board pack is
a PDF, and a PDF that this project both writes and reads back is defect 3 again with different
file extensions. Its external authority is a human opening it, and that needs to be in the phase 6
spec as a named gate rather than assumed.

The manual gates are a standing cost. `docs/phases/phase-05-spec.md` records 5.15 and 5.30 as not
done rather than quietly satisfied by their automated proxies, and that is the honest state to
leave a phase in.
