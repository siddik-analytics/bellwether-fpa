# ADR 0021 — The COM stage is optional at import time, and uses raw win32com

- **Status:** Accepted
- **Date:** 2026-09-06
- **Phase:** 5 (Excel/COM stage and Power BI)

## Context

Phase 5 gives the Excel stage something to do. Until now it was a docstring, so `CLAUDE.md`'s
rule 2 — the headless build must produce a complete, correct workbook on Linux with no Excel —
held for free. It stops holding for free the moment the stage imports a Windows-only library.

The failure this guards against is unglamorous and common: someone adds `import win32com.client`
at the top of a module, everything works on the machine they are using, and the Linux CI job
fails on an import that has nothing to do with the change.

## Decision

**`pywin32` is an optional extra, imported lazily, and the headless build is tested with it
unresolvable.**

```toml
[project.optional-dependencies]
excel = ["pywin32>=306; sys_platform == 'win32'"]
```

Three things together, none sufficient alone:

1. **Optional extra, not a dependency.** `pip install -e ".[dev]"` on Linux installs nothing
   Windows-only.
2. **Imported inside functions.** `import bellwether.excel_stage` succeeds on any platform;
   only calling COM fails, and it fails with a message that says so.
3. **Tested with the import actively blocked.** Criterion 5.6 runs the build in a subprocess
   with a `sys.meta_path` finder that raises `ImportError` for `win32com` and friends, then
   compares the resulting workbook by SHA-256 against a fresh headless build.

Point 3 is the one that matters and it is why "uninstalled" was not good enough. A developer
machine with `pywin32` present would pass any test that merely checked the package was absent
from the environment. Blocking the import reproduces the Linux condition on Windows, where the
work is actually being done.

**The stage uses raw `win32com` rather than `xlwings`.** `.claude/rules/excel-com.md` names
`xlwings` as the default surface and says to drop to `win32com` deliberately, for APIs it does
not wrap. This stage needs exactly three: `CalculateFullRebuild`, `Range.Table`, and later
`ExportAsFixedFormat`. The rules file names the first and third itself. `xlwings`' advantage is
DataFrame interop, and this stage moves no DataFrames — it reads formulas and values in bulk
arrays and compares them to numbers parsed out of the file. Adding a dependency that would be
used for none of its strengths is not a deliberate reach for `win32com`; it is the opposite.

## Rationale

The rule being protected is not "Linux should work". It is that **correctness must never
depend on Excel**. The moment the headless build needs the COM stage for a figure to be right,
the reconciliation stops being two independent implementations and becomes one implementation
with an extra step, and the strongest artifact in the repo quietly stops meaning anything.

That is why 5.6 compares by hash rather than asserting the build merely succeeded. A build that
produces *a* workbook without Excel proves nothing; a build that produces the *same* workbook
proves the COM stage contributed nothing to it.

## Alternatives considered

**A hard `pywin32` dependency, guarded by `sys.platform`.** Rejected: the dependency still has
to resolve at install time, and a marker that is wrong in one place fails CI for a reason
unrelated to whatever changed.

**A stub `win32com` module for Linux.** Rejected: it would make an unsupported call fail
somewhere deep instead of at the import, and it is one more thing that can silently diverge from
the real API.

**`xlwings`.** See above. Also worth naming: it drives Excel through a helper add-in in some
modes, and `.claude/rules/excel-com.md` requires add-ins to be suppressed for reproducibility.
The two would have needed reconciling for no gain.

## Consequences

Running the stage needs `pip install -e ".[dev,excel]"` on Windows, and the stage says so
rather than failing with an import error.

`tests/excel/` is `requires_excel` and skipped in CI, so **the headless suite has to carry the
correctness argument on its own** — which it does, and `tests/test_headless_parity.py` is the
seam between the two.

The stage suppresses add-ins and `PERSONAL.XLSB` and uses `DispatchEx` rather than `Dispatch`,
so it never attaches to an Excel the user already has open. Automating someone's live session is
how a stage like this destroys work that has nothing to do with it.

**A finding this ADR should record, because it nearly invalidated the phase:** the first
reconciliation harness compared values read through COM before and after recalculating. Excel
evaluates formulas as it opens a workbook, so the "before" read was already Excel's own answer
and the comparison was a value against itself. It reported **zero differences on a workbook with
a deliberately wrong cached value**. The cached value has to be parsed out of the file's XML,
where the oracle wrote it. The negative control that caught this is now a permanent test.
