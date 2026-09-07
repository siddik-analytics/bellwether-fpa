# Power BI Desktop's bound visuals, as a fixture

The third Desktop reference, and the first with fields **actually assigned**. The blank fixture
settled the file layout; the visuals fixture settled the container envelope; this one settles how
a field is bound.

## The three shapes it supplied

**The query object.** A visual's data binding:

```
visual.query.queryState.Data.projections[]
    field         { "Measure": { "Expression": { "SourceRef": { "Entity": ... } }, "Property": ... } }
    queryRef      "<table>.<measure>"
    nativeQueryRef, displayName, format
```

`Column` replaces `Measure` for a column reference; nothing else changes.

**The textbox.** Content lives under
`objects.general[].properties.paragraphs[].textRuns[]`, with background and border switched off
through `visualContainerObjects`.

**The drillthrough target.** A hidden page that declares its field **twice**:

| Where | Key | Marker |
|---|---|---|
| `filterConfig.filters[]` | `field` | `howCreated: "Drillthrough"` |
| `pageBinding.parameters[]` | `fieldExpr` | `boundFilter` naming that filter |

Not a shape anyone would invent. The same field expression appears under two different keys, and
omitting either leaves a page that looks configured and does not drill.

## What was kept, and what was not

The source was a **different company's real report** — six pages, ninety-odd visuals, business
commentary. Publishing it into this repository would have meant shipping someone else's work
alongside Northlake's, so only seven files were taken: the smallest example of each visual type
needed, one drillthrough target page and one ordinary page.

**One alteration:** the other project's company name was replaced. Every key, nesting level and
type is Desktop's, untouched — and nothing in `tests/powerbi/test_bound_fixture.py` asserts on a
redacted value. The tests read structure: key sets, nesting, and which markers are present.

That is a weaker fixture than a verbatim copy, and the weakness is in the part nothing depends
on. It is recorded here because ADR 0022 is about knowing exactly which parts of an oracle are
external and which are ours — and this one is a mixture, which the other two are not.

`.pbi/` and `StaticResources/` were excluded for the same reasons as the other fixtures. Line
endings were normalised to LF by this repository's own hooks.
