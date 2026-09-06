# Power BI Desktop's own output, as a fixture

A blank report saved by **Power BI Desktop 2.157.1354.0**, kept so the project's generated PBIP
can be checked against the real thing rather than against values transcribed from documentation
or inferred from an error message.

This is ADR 0022's fourth countermeasure applied to a detail that looks too small to need it.
Every `$schema` URL in the generator was **guessed**, and every one was wrong:

| File | Guessed | Desktop actually writes |
|---|---|---|
| `northlake.pbip` | a `definitionProperties` schema | **no `$schema` at all** |
| `Report/definition.pbir` | a `definitionProperties` schema | **no `$schema` at all** |
| `Report/…/report.json` | `report/1.0.0`, at the report root | `report/3.3.0`, under `definition/` |
| `SemanticModel/definition.pbism` | version `4.0` | version `4.2` |
| `definition/database.tmdl` | `database northlake`, level 1567 | `database` unnamed, level **1606** |

It also settled a structural question no amount of care would have answered: the report is the
**PBIR format** — `definition/report.json` plus `definition/pages/pages.json` and a
`definition/pages/<id>/page.json` per page — not the legacy single `report.json` with
`sections` and `visualContainers` that the generator was emitting.

## What was left out, and why

- **`.pbi/localSettings.json`** — carries a DPAPI-encrypted `securityBindingsSignature`, which is
  machine-bound credential material. Not committed, and `.gitignore` now excludes the directory
  so a future save cannot sweep it in.
- **`.pbi/cache.abf`** — a binary. Rule 3: no binaries in this repository.
- **`StaticResources/…/Fluent2-CY26SU08.json`** — 99 KB of Microsoft's stock theme. Nothing here
  needs it, and it is Microsoft's content rather than this project's.

The `.platform` files keep their `logicalId` GUID. It identifies the artifact, not a person or a
machine, and removing it would make the fixture less faithful for no gain.

## How it is used

`tests/powerbi/test_schema_fixture.py` asserts every `$schema` the generator emits equals the one
in the corresponding file here — and that the two files Desktop leaves without a `$schema` do not
acquire one. The oracle is Desktop's own output, which is the entire point: a test comparing the
generator to a constant the same author typed would pass on all five of the wrong values above.

Regenerate it by saving a blank report from Desktop into a scratch directory and copying the
files listed here. Do not point Desktop at `powerbi/` — that directory is generated, and saving
over it is what produced this fixture in the first place.

## One deliberate alteration

Line endings were normalised from CRLF to LF and a trailing newline added, by this repository's
own `.gitattributes` and pre-commit hooks. Nothing else was touched: every `$schema`, version,
key and structure is byte-for-byte what Desktop wrote.

This is worth stating rather than leaving for someone to discover, because the fixture's whole
value is that it is not our own output. Line endings are the one thing about it that is, and they
are also the one thing nothing here depends on — the assertions read parsed JSON and TMDL lines,
neither of which can tell the difference.
