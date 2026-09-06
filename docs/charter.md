# Charter

> **Northlake, Inc. is an illustrative company.** All data in this project is synthetic. No real
> company, no real people, no scraped or proprietary data.
>
> **Naming convention.** *Northlake* is the modelled business — the brand, and "Northlake, Inc."
> as the reporting entity. *Bellwether* is this project: the repository, the Python package and
> the build tooling. The two are never interchangeable, and no artifact should use Bellwether as
> a company name.

## Why this project exists

Two audiences, one build. That constraint is the whole design, and it is the thing this
document exists to protect when scope arguments start.

- **Hiring managers** clone the repository. They read structure, ADRs, tests and commit
  history. The artifact *is* the repo. They will not open the dashboard for more than a
  minute, and they will not be impressed by it.
- **Prospective clients** never open the repository. They see a PDF board pack, a dashboard
  and a short video. The artifact is the output. They do not care that the workbook was
  generated from code, only that the numbers are right and the story is clear.

Work that serves neither audience does not get built. Work that serves only one gets built
only if it is cheap.

## The company being modelled

A direct-to-consumer brand with a wholesale channel. Roughly $8–12M revenue, three years of
history, thirty-six months of forecast. Single legal entity, single currency.

The specifics — channel mix, unit economics, the central financial tension the board pack
argues — are settled in the phase 1 interview and recorded in `docs/data-contract.md`. They
are deliberately not fixed here, because inventing them without the interview is exactly the
failure mode this project is built to avoid.

## Scope

In scope:

| Layer | What it is |
|---|---|
| Synthetic data | Seeded generator producing a transaction ledger with realistic structure |
| Warehouse | Star schema, semantic metric definitions, validation suite |
| Model | Driver-based three-statement model, 36 forecast periods, scenarios |
| Workbook | Code-generated Excel, verified against the model by an independent read-back |
| BI | Power BI in PBIP text format, four report pages, DAX reconciled to the model |
| Reporting | Board pack PDF with automated variance commentary |
| Distribution | README, case study, video |

Out of scope, and staying out:

- Multi-entity, multi-currency, or consolidation logic
- A live database or any hosted service
- Real or scraped data of any kind
- A web application front end
- Anything requiring credentials, an account, or a paid tier to reproduce

## Success criteria — hiring managers

The question this audience is answering is: *can this person build a financial system, or
only a spreadsheet?* Each criterion below is something they can verify in under fifteen
minutes with a clone and a terminal.

1. **`git clone` then one command produces the whole build.** No manual steps, no Excel
   required, no undocumented prerequisites. If setup takes more than five minutes, the
   reviewer stops.
2. **CI is green on Linux and enforces something real.** Not a lint-only workflow. It runs
   the full headless build and the acceptance suite, and it would fail if correctness ever
   started depending on a local Excel installation.
3. **The Excel reconciliation test exists and is convincing.** Two independent
   implementations of the same specification — the Python oracle and the recalculated
   workbook — cross-checking to 0.01. This is the single strongest artifact in the repo.
4. **The three statements tie, in tests, not by inspection.** Balance sheet balances in all
   36 periods; cash flow closing cash equals balance sheet cash in every period; revenue
   disaggregates cleanly to total at every grain.
5. **DAX arrives as reviewable text.** PBIP, TMDL, diffable in a pull request. A finance
   portfolio that can be code-reviewed is uncommon; that is the point.
6. **Commit history reads as a build, not a dump.** Conventional commits, one logical change
   each, messages written for the reason rather than the diff. A reviewer can reconstruct
   how the project was made.
7. **Non-obvious decisions have ADRs.** Every place a competent reviewer would ask "why did
   you do it that way" has a dated answer stating the alternative that was rejected.
8. **Financial conventions are stated and consistently applied.** The COGS boundary, the
   revenue recognition timing, the depreciation method, the variance sign convention — all
   documented once and held to everywhere.
9. **The tests express requirements, not coverage.** Acceptance criteria in phase specs map
   to named assertions. "It looks right" appears nowhere.

## Success criteria — prospective clients

The question this audience is answering is: *would I trust this person with my board
reporting?* They judge the output, and they judge it fast.

1. **The board pack stands alone.** A reader with no context understands the position of the
   business within two pages. No jargon that is not defined on the page it appears.
2. **There is an argument, not a data dump.** The pack states a central financial tension,
   supports it with numbers, and says what should be done. A pack that only reports is a
   pack no one needed.
3. **Variance commentary reads as though a person wrote it.** Specific, quantified, and
   attributed to a driver — "gross margin fell 240bp, of which 180bp is channel mix" — not
   "revenue was below budget."
4. **The dashboard answers questions rather than displaying metrics.** Four pages, each with
   a job, drillthrough to transaction level from every summary visual.
5. **The numbers agree everywhere.** The pack, the dashboard and the workbook show the same
   figure for the same thing. A single visible disagreement destroys the credibility of all
   three.
6. **It looks deliberate.** Consistent formatting, sensible rounding, units labelled,
   nothing default-styled. This is judged in seconds and is not a matter of taste.
7. **Reproducing it monthly is obviously cheap.** The value proposition is not the pack; it
   is that the pack rebuilds itself. The case study has to make that legible.
8. **The synthetic-data disclosure is present and does not undermine the work.** Every
   artifact carries the note. It should read as professional care, not as a caveat.

## A deliberate feature of the model

**Northlake does not reach profitability within the 36-month forecast horizon under any of the
three scenarios.** Balanced Base reaches −1.8% EBITDA by FY2028, Wholesale Acceleration −1.0%, and
DTC Recovery −1.4%. Trailing-twelve-month EBITDA is negative in every month of every scenario.

This is a deliberate choice, not an oversight or a modelling failure, and it is stated here so that
nobody — reviewer, client, or a future contributor — reads it as one.

Three things follow from it, and each is worth more than a profitable forecast would have been:

1. **The board question is real.** A plan that turns profitable inside the horizon answers itself.
   This one forces the actual decision — whether to keep funding wholesale-led growth, and with
   whose money.
2. **The financing constraint does the work.** Because earnings never cover the cash requirement,
   the borrowing base is what determines feasibility. Wholesale Acceleration has the *best* FY2028
   EBITDA of the three and is the only scenario that runs out of availability. A model where the
   most profitable-looking plan is the unfundable one is more interesting, and more like real
   FP&A, than one where the rankings agree.
3. **It is honest about the company described.** A DTC brand whose gross margin fell four points
   on channel mix, whose CAC rose 17%, and which absorbed $720k into working capital in one year
   does not recover to profit in three years without something changing. Forcing a profitable
   forecast would have required assumptions the interview does not support.

See `docs/data-contract.md` §7.6 for the scenario drivers and ADR 0008 for why this makes the
covenant structure what it is.

## Non-negotiables

These are restated from `CLAUDE.md` because they are the ones most likely to erode under
schedule pressure.

1. The oracle originates every number. Excel verifies and packages; it never originates.
2. The headless build must produce a complete, correct workbook with no Excel installed.
3. Code is the source of truth. Workbooks, PDFs and PNGs are build artifacts, never
   hand-edited, never committed outside a release tag.
4. Every requirement is a test.
5. All data is synthetic, and every generated artifact says so.

## How this document is used

When a proposed piece of work does not map to a numbered criterion above, it is out of
scope until this document is amended. Amending it is a normal thing to do; doing the work
without amending it is not.
