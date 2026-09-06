# Phase 0 — Scaffold

Goal: an empty but *correct* repo. No business logic. When this phase is done, every guardrail
that protects phases 1–6 is in place and proven to work.

Tag on completion: `v0.1-scaffold`

---

## Order of work

The order matters. CI cannot run before the remote exists, and the ignore rules must be proven
before any build artifact is ever generated.

### 1. Local skeleton

```
C:\Dev\bellwether-fpa\
```

`git init`, then place the files already drafted:

- `CLAUDE.md` at the root
- `.claude/rules/excel-com.md`, `powerbi-pbip.md`, `data-contract.md`
- `.claude/settings.json`
- `.gitignore`
- `docs/phases/phase-01-interview.md`

### 2. Python environment

- Python 3.12, `src` layout, package name `bellwether`
- `pyproject.toml` with ruff and pytest
- Register the `requires_excel` marker in `pyproject.toml` so unmarked tests never silently skip
- `python -m venv .venv` at the repo root

Create stub modules so the documented commands exist and exit cleanly:
`bellwether.build`, `bellwether.excel_stage`. They do nothing yet. They must not error.

### 3. Guardrails

- `.pre-commit-config.yaml` with `check-added-large-files`, plus a local hook rejecting
  `*.xlsx`, `*.xlsm`, `*.pbix`, and `~$*`
- `pre-commit install`
- One real test in `tests/` so the suite is not vacuously green

### 4. Documentation skeleton

- `docs/charter.md` — **written, not stubbed.** Two separate success-criteria lists, one for
  the hiring-manager audience and one for the client audience. This is the document that
  settles scope arguments in weeks three and four; a placeholder here is worse than nothing.
- `docs/architecture.md` — layers, the oracle rule, the Windows/COM boundary
- `docs/adr/0001-beginning-balance-interest.md` — the circularity decision
- `docs/adr/` and `docs/phases/` directories in place

### 5. GitHub — this is the step to remember

Create the repository. **Private.** Flip it public at `v0.4-model`, once the history opens on
substantive work rather than scaffolding.

Do this part yourself — Claude Code is denied push and should not be creating accounts or
handling authentication.

- New repo `bellwether-fpa` on GitHub, private, **no** README, `.gitignore` or licence
  (you already have your own and the extra commit is noise)
- `git remote add origin <url>`
- First commit, then `git push -u origin main`

After this push, `git log --oneline origin/main..HEAD` works and the normal review loop applies.

### 6. CI

`.github/workflows/ci.yml`, running on `ubuntu-latest`:

```
ruff check .
python -m pytest -m "not requires_excel"
```

Linux is the point. CI has no Excel, so it enforces headless parity mechanically rather than
by discipline. If a future change makes correctness depend on Excel, CI is what catches it.

### 7. Tag

`v0.1-scaffold`, after every criterion below passes.

---

## Acceptance criteria

| # | Criterion | How it is checked |
|---|---|---|
| 0.1 | `python -m bellwether.build` exits 0 with no Excel present | CI on ubuntu |
| 0.2 | `pytest -m "not requires_excel"` passes, with at least one non-trivial test | CI |
| 0.3 | `ruff check .` clean | CI |
| 0.4 | pre-commit rejects a staged `.xlsx` and a `~$` file | Stage one deliberately and confirm the reject |
| 0.5 | `git status` is clean immediately after a build run | Manual, once |
| 0.6 | `CLAUDE.md` appears under **Memory files** | `/context` in a session |
| 0.7 | Rules files do *not* load until a matching path is opened | `/context` before and after opening a file under `src/bellwether/excel_stage/` |
| 0.8 | `docs/charter.md` contains two distinct success-criteria lists | Read it |
| 0.9 | Repo is private, first push complete | GitHub |

0.4 is the one people skip. Stage a real `.xlsx`, confirm the hook blocks it, then unstage.
An untested guardrail is not a guardrail, and this is the failure that is permanent and public.

---

## Not in this phase

No synthetic data, no entities, no model logic. Those wait on the Phase 1 interview.
