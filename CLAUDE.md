# Bellwether — FP&A Reporting & Planning Stack

Synthetic but realistic FP&A system for an illustrative mid-market company:
raw transactions → dimensional warehouse → driver-based model → Power BI → board pack.

One build, two audiences:

- **Hiring managers** clone the repo. Structure, ADRs, tests and commit history are the artifact.
- **Prospective clients** never open the repo. They see the PDF board pack, the dashboard, and a video.

Deeper context lives in `docs/charter.md`, `docs/architecture.md`, `docs/data-contract.md`
and `docs/adr/`. Read the relevant one before non-trivial work. They are deliberately not
imported here — read them on demand.

## Environment

- Windows, running natively. Not WSL. Shell is PowerShell.
- Repo root: `C:\Dev\bellwether-fpa`
- Interpreter: `.venv\Scripts\python.exe`
- Excel is installed locally. Excel is **not** available in CI.
- The repo must not live in a OneDrive-synced folder. Sync locks break Excel automation
  in ways that look like code bugs.

## Non-negotiable rules

1. **The oracle originates every number.** `src/bellwether/oracle/` computes all financial
   values in pure Python. The workbook, the Power BI model and the board pack consume those
   values. The Excel/COM stage verifies and packages. COM never originates a value.

2. **Headless build parity.** `python -m bellwether.build` must produce a complete, correct
   workbook on Linux with no Excel installed. The Excel stage only ever *adds* — native data
   tables, pivots, PDF, PNG. If correctness starts depending on Excel, the change is wrong.

3. **Code is the source of truth.** `.xlsx`, `.pdf` and `.png` are build artifacts. Never
   hand-edit them. Never commit them outside a release tag. Power BI lives in PBIP text
   format, never as a `.pbix` binary.

4. **Every requirement is a test.** Acceptance criteria go in the phase spec as a numbered
   table and map to assertions in `tests/`. "It looks right" is not an acceptance criterion.

5. **Phase gate.** Do not begin phase N+1 until phase N is tagged, tests are green and docs
   are updated. If asked to skip ahead, say so and ask for confirmation first.

6. **All data is synthetic.** No real company, no scraped data, no real personal names.
   Every generated artifact carries an "illustrative company, synthetic data" note.

## Commands

```powershell
# Headless build — must work with no Excel present
.venv\Scripts\python.exe -m bellwether.build

# Windows-only stage: recalc, native data tables, PDF board pack, PNG exports
.venv\Scripts\python.exe -m bellwether.excel_stage

# Tests that run everywhere (this is what CI runs)
.venv\Scripts\python.exe -m pytest -m "not requires_excel"

# Full suite including Excel reconciliation — local Windows only
.venv\Scripts\python.exe -m pytest
```

Do not introduce `make`. It is not reliably available on Windows and would break the
"same command everywhere" property that keeps CI honest.

## Layout

```
src/bellwether/
  data/         synthetic transaction + master data generator (seeded, deterministic)
  transform/    star schema build, semantic definitions
  oracle/       model logic — SOURCE OF TRUTH for every financial value
  workbook/     xlsxwriter generation, cross-platform
  excel_stage/  COM: recalc, data tables, PDF, PNG — Windows only, additive only
powerbi/        PBIP project (TMDL + report JSON)
docs/           charter, architecture, data contract, ADRs, phase specs
tests/          acceptance assertions; Excel-dependent ones marked requires_excel
data/           generated — gitignored
build/          artifacts — gitignored except at release tags
```

## Phases

Current phase: **0**.

| Phase | Output | Tag |
|---|---|---|
| 0 | Repo scaffold, docs, CI, pre-commit | `v0.1-scaffold` |
| 1 | Data contract, synthetic generator, validation suite | `v0.2-data` |
| 2 | Transformation layer, star schema, semantic definitions | `v0.3-warehouse` |
| 3 | Code-generated Excel model, three statements tying | `v0.4-model` |
| 4 | Power BI PBIP, DAX, four report pages | `v0.5-bi` |
| 5 | Board pack, automated variance commentary | `v0.6-reporting` |
| 6 | README, case study, video, distribution assets | `v1.0` |

Definition of done for every phase: tests green, docs updated, tag pushed, and the decision
log in `docs/adr/` extended if anything non-obvious was chosen.

## Git

You own local git: staging, commits, branches, tags. I own `git push`. Never attempt a
push — it is denied in settings, and it is the review gate before anything reaches a public
repository that hiring managers read.

- Conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`.
- **Write the message for the reason, not the diff.** `fix: interest accrued on average
  rather than opening balance` is useful. `fix: update oracle.py` is not. The reader is a
  hiring manager reconstructing how the project was built, not a bot.
- **Stage explicitly.** Name the paths. Never `git add -A` or `git add .` — this repo
  generates workbooks, PDFs, PNGs and `~$` Excel lock files, and a blanket add will
  eventually sweep one in. A committed binary is permanent in a repo strangers clone.
- **One logical change per commit.** If a change touches the oracle and the workbook and the
  docs for unrelated reasons, that is three commits. Do not batch a session's work into one.
- Commit at working increments, not at phase boundaries. But do not manufacture commits to
  look busy — a history with twenty commits in ten minutes reads as generated, which
  undermines the point of committing carefully in the first place.
- Tag at phase completion using the table above. Say so before tagging: a tag is a claim
  that a phase is done, and that claim is mine to make.
- Stop and ask before anything that rewrites history — reset, rebase, amend of a pushed
  commit, force anything.
- An architecture decision a reviewer might question gets an ADR, numbered and dated,
  stating the decision, the alternative considered, and why.

## Standing acceptance checks

These hold from phase 3 onward and run in CI on every commit:

- Balance sheet balances for all 36 forecast periods, tolerance 0.01
- Closing cash on the cash flow equals balance sheet cash, every period
- Revenue disaggregated by channel sums to total revenue at every grain
- No orphan keys across any fact-to-dimension join
- Workbook values, when recalculated by Excel, match the oracle within 0.01
  (marked `requires_excel`, local only)

## Stop and ask

Raise these rather than deciding alone:

- A financial convention that is not already documented — revenue recognition timing,
  depreciation method, working capital assumptions. These are the domain expertise the
  project exists to demonstrate; guessing at them produces generic output.
- Anything that would make the headless build depend on Excel.
- Anything that would put a value into the workbook or Power BI that the oracle did not compute.
- Adding a dependency, especially one that is Windows-only.
- Skipping a phase gate.

<!-- Maintainer note: this file is stripped of HTML comments before it reaches context.
     Keep the whole file under 200 lines. Stage-specific detail belongs in .claude/rules/. -->
