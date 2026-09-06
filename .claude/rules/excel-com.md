---
paths:
  - "src/bellwether/excel_stage/**"
  - "tests/excel/**"
---

# Excel / COM stage

Windows-only, additive-only. This stage opens a workbook the headless build already produced,
recalculates it, adds features xlsxwriter cannot create, verifies the numbers against the
oracle, and exports distribution artifacts.

## The boundary

This stage **never originates a financial value**. If a number appears here that Python did not
compute, that is a defect regardless of whether it is correct. The oracle is a property rather
than a package — `docs/architecture.md` lists the modules that constitute it.

Permitted here:

- Full recalculation and reading values back for verification
- Native Data Tables for sensitivity grids
- Pivot tables and slicers
- `ExportAsFixedFormat` → board pack PDF
- `CopyPicture` → named ranges as PNGs for README, case study, LinkedIn

Not permitted here:

- Writing a formula or constant that changes a reported figure
- Any step the headless build depends on for correctness

## Library choice

`xlwings` is the default surface — the DataFrame interop is far cleaner. Drop to raw
`win32com` only for APIs xlwings does not wrap, notably `ExportAsFixedFormat` and
`CalculateFullRebuild`. Reach for `win32com` deliberately, not by habit.

## Instance hygiene

Every entry point launches a dedicated, isolated Excel instance and tears it down in `finally`:

- `Visible = False`
- `DisplayAlerts = False`
- Suppress add-ins and `PERSONAL.XLSB` — an inherited add-in makes automation slow and
  unpredictable in ways that are painful to diagnose
- Always `Quit()` in `finally`, then release the COM reference

Skipping the teardown accumulates zombie `EXCEL.EXE` processes that hold file locks and
silently break the next run.

## Known failure modes

- **Relative paths silently fail.** COM does not resolve paths against the Python working
  directory. Pass absolute Windows paths, always.
- **`Calculate()` is not enough.** Use `CalculateFullRebuild()` — it reconstructs the
  dependency tree and surfaces broken references a normal recalc will skip past.
- **Transient RPC errors are normal.** "Call was rejected by callee" and friends appear under
  load and mean nothing. Wrap COM calls in a retry decorator with backoff; do not treat the
  first failure as a real error.
- **OneDrive.** If the repo ends up in a synced folder, expect intermittent, misleading
  failures. This is an environment bug, not a code bug — say so rather than working around it.

## Circularity

The model uses **beginning-of-period debt balance** for interest, so no iterative calculation
is required. This keeps the headless build exactly equivalent to the full build. See the ADR.

If a change would require enabling iterative calculation, stop and raise it. Do not enable it.

## Tests

Everything in this stage is marked `@pytest.mark.requires_excel` so CI skips it. The
reconciliation test is the important one: open the generated workbook, force a full rebuild,
read values back, assert agreement with the oracle within 0.01.

That test is two independent implementations of the same spec cross-checking each other. It is
the strongest single artifact in the repo for the hiring-manager audience — treat it as a
first-class deliverable, not a smoke test.
