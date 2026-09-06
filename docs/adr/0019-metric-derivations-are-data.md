# ADR 0019 — A metric's derivation is data, and every consumer generates from it

- **Status:** Accepted
- **Date:** 2026-09-06
- **Phase:** 5 (Excel/COM stage and Power BI)

## Context

`Metric` carried `depends_on` and nothing else about how the dependency was used:

```python
"Net Revenue":    depends_on=("Gross Revenue", "Contra Revenue")   # subtract
"Gross Margin %": depends_on=("Gross Profit", "Net Revenue")       # divide
```

Nothing in the definition said *subtract* or *divide*. The arithmetic lived somewhere else, and
by the end of phase 4 it lived in three somewhere-elses:

| Where | What it held |
|---|---|
| `semantic.evaluate_ladder` | the scalar ladder, written out longhand |
| `statements.metric_series` | the same ladder again, over pandas Series |
| `workbook.model.DERIVATIONS` / `RATIOS` | the same ladder a third time, as cell references |

They agreed. They agreed because nobody had edited one copy.

Phase 5 is what forced the issue. `.claude/rules/powerbi-pbip.md` positions Power BI as a thin
consumer of the semantic layer, and ADR 0007 rests on the same claim. But a `Metric` could not be
translated into a DAX measure, because the definition did not contain the operation. Any
generator would have needed its own table of "which arithmetic goes with which dependency pair"
— which is the definition living in the generator rather than in the semantic layer. Generated
DAX would have been a fourth copy, and hand-written DAX a fourth copy that drifts.

## Decision

**A derived metric carries its derivation as an expression, and every consumer generates from
that one string.**

```python
"Net Revenue":    derivation="[Gross Revenue] - [Contra Revenue]"
"Gross Margin %": derivation="DIVIDE([Gross Profit], [Net Revenue])"
```

`transform/expressions.py` turns one expression into three forms:

| Backend | Output | Consumer |
|---|---|---|
| Python | a float or a pandas Series | the scalar ladder and the monthly series |
| Excel | `B6-B7`, `IF(B8=0,0,B10/B8)` | the workbook's tied formulas |
| DAX | `[Gross Revenue] - [Contra Revenue]` | the Power BI measure table |

`depends_on` is no longer stored. It is derived from the expression, so a dependency list cannot
disagree with the arithmetic that uses it.

**The syntax is DAX's own.** `[Measure Name]` is how DAX references a measure and `DIVIDE(a, b)`
is how it divides safely, so the DAX backend is close to a pass-through. That is not laziness:
phase 5 cannot execute DAX in CI, so its guarantee is that measures are *generated* rather than
authored. A generator is only as trustworthy as the translation it performs, and a translation
small enough to read in one sitting is the difference between a guarantee and a hope.

**`is_cost` moves onto the metric** in the same change. Variance direction was a function
argument, so every consumer — including a DAX generator — had to keep its own list of which
measures are costs. Favourable-is-positive is a property of the metric.

## Rationale

This is the two-sources-of-truth problem the project exists to demonstrate, found one layer
below where the project had been looking for it. The oracle rule was written about the boundary
between Python and Excel, and it held there. Inside Python, the same ladder had quietly been
written three times.

The three copies had not diverged, which is exactly what makes the case worth recording. Nothing
was broken. There was no failing test to motivate the change and no incident to point at. The
argument is entirely about what happens on the first edit — a reclassification between COGS and
opex, say, or a change to what sits above EBITDA — where two of the three copies get updated and
the third is discovered by a board member.

The alternative framing, that this is premature abstraction over three short blocks of
arithmetic, would be fair if the copies were incidental. They are not: each exists because a
different consumer needed the ladder in a different shape, and *more consumers are coming*. Power
BI is the fourth. A board pack narrative is the fifth.

**Evaluation is parsed, not `eval`ed.** Derivations are read from a definition table and turned
into an AST checked against an allow-list of node types — arithmetic, numbers, metric
references, and `DIVIDE`. Anything else raises. A definition table should not be able to express
a function call, an attribute access or an import, and the guard costs about twenty lines.

## Alternatives considered

**Keep `depends_on` and add an `operation` enum** (`SUBTRACT`, `DIVIDE`). Rejected: it handles
the six cases that exist and nothing else. `EBITDA - [Other Income and Expense]` fits; a metric
needing three operands or a constant does not, and the enum would then grow into an expression
language one case at a time, without a parser.

**Write the DAX by hand and reconcile it numerically.** The obvious approach, and the one most
projects take. Rejected because the reconciliation cannot run in CI — there is no supported way
to evaluate a DAX measure from a script — so the check would run when someone remembered, which
is when it is least likely to be needed. Generation moves the guarantee from a periodic
comparison to a structural property.

**Python callables as derivations** — `lambda m: m["Gross Revenue"] - m["Contra Revenue"]`.
Rejected: a callable evaluates but does not translate. The whole point is that the definition
must be readable by three backends, and a lambda is readable by one.

## Consequences

`Metric` is now the only place a metric is defined, and the workbook's formulas are generated
rather than written — so a change to the ladder reaches Excel without anyone touching
`workbook/`. Criterion 5.10 asserts the same for DAX.

**The expression language is a thing that must be maintained.** It is deliberately tiny — four
operators, one function, a parser with an allow-list — and it should stay that way. A derivation
that cannot be expressed in it is a signal that the metric is not a derivation, not a reason to
grow the language.

Adding `Other Income and Expense` and `Net Income` as real metrics, which this change required
in order to make the definition set total, **surfaced that both are structurally zero**: the
forecast ledger never posts interest or financing fees. That is recorded separately; it is a
generator defect this ADR only exposed.
