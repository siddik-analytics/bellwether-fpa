# ADR 0024 — Hand-written prose states claims, and the claims are predicates

- **Status:** Accepted
- **Date:** 2026-09-06
- **Phase:** 6 (board pack and automated variance commentary)

## Context

Phase 6 built two kinds of prose and treated them very differently.

The **commentary** is derived. Every sentence comes from a `bridge.Bridge`, every number is
carried on the `Sentence` that used it, and `tests/reporting/test_commentary.py` parses the
numbers back out of the finished text and asserts each one appears in the bridge it claims to come
from. That machinery exists because templated prose with numbers substituted is a table read
aloud, and worse than a table, since it implies an analyst looked at it.

The **section leads and exhibit rationales** are hand-written. That was the right call and it
should stay. An argument is what the reader is paying for:

> The covenant, not earnings, decides which plan is available. The plan with the highest revenue
> is the one that breaches.

Nothing generated would produce that, and attempting to generate it would produce exactly the
prose the commentary machinery exists to avoid.

But a hand-written sentence still asserts facts, and this project's figures have moved repeatedly
— phase 3's D-1, phase 4's gross margin calibration, phase 6's financing posting. "Consolidation
is the only plan that reaches profitability" was true when it was written, and **nothing forced it
to stay true**. The pack shipped with fifteen sentences of that shape, all of them accurate at the
moment of writing and none of them checked.

The phase-6 report called this out as R-4 and proposed nothing, on the grounds that inventing a
prose-quality metric would be an oracle derived from the system under test. That reasoning was
right about the metric and wrong about the conclusion. Prose quality is not checkable. **The
claim inside the prose is.**

## Decision

**The sentence stays hand-written. The claim inside it becomes a predicate.**

`transform/claims.py` holds one `Claim` per assertion: the fragment of prose being verified,
verbatim, and a check that computes the answer from the ledger. `pack.Section` and `pack.Exhibit`
carry the claims their prose makes, so a lead and its claims sit in the same diff.

Three rules, in `tests/reporting/test_claims.py`:

1. **Every claim holds.** Twenty-one predicates, evaluated against the data the pack was built
   from. A failure means the pack states something untrue.
2. **Every sentence is covered.** Each sentence of each lead must have a claim whose fragment is
   a substring of it. Prose cannot be added without saying what it asserts. A sentence that
   genuinely argues rather than asserts is recorded as `framing` — and a lint closes that route:
   a sentence containing a digit or a quantifier (*only, never, highest, lowest, neither,
   entirely*) may not be framing.
3. **Every claim can fail.** ADR 0022's negative control, one claim at a time. `FALSIFIERS` names,
   for each claim, the perturbation of the world that must break it — the corporate block removed,
   the scenario labels swapped, nothing breaching, no budget — and the claim must return `False`
   under it. Twenty-one predicates that all return `True` prove nothing unless each is shown
   capable of returning `False`.

The checks compute their figures from the ledger rather than calling `pack`'s helpers. A claim
that reused the pack's own arithmetic would be checking the pack against itself, which is the
failure ADR 0022 exists to name, so the duplication is deliberate.

## What it found immediately

Two of the shipped sentences were false. Neither was a rounding question; both were the kind of
claim a reader would repeat in a meeting.

**"The scenario with the highest revenue and the best EBITDA of the three that grow is the one
that runs out of room."** True on revenue. On earnings it depends entirely on a reading the
sentence did not state. Wholesale Acceleration has the best *cumulative* EBITDA of the three
growing plans over FY2026–28 (−$2,370,538 against −$2,390,298 and −$2,516,181), and the *worst but
one* in the final year alone (−$679,598 against DTC Recovery's −$592,110). The sentence now says
"ranked over the whole horizon, the best cumulative EBITDA", and the claim verifies that reading.

**"The only plan that reaches profitability is the one that shrinks."** Consolidation does not
shrink. Its FY2028 revenue is $11.36M against FY2025 actual of $10.60M — the lowest of the four
and the slowest-growing, but larger than today. The sentence now reads "the one that grows
slowest", with a second sentence saying so explicitly, and both are claimed.

A third sentence was strengthened rather than corrected. C-1 argued that the allocation drivers
"disagree by enough that choosing one manufactures precision the business does not have", which
invited a threshold on the spread — a number arguing with itself. The claim instead asserts the
consequence: **the choice of driver reverses which channel contributes more.** Under units shipped
DTC leads; under order and invoice lines Wholesale does. That is a conclusion a reader could act
on being wrong about, and it is why the exhibit is in the pack.

## Alternatives considered

**Generate the leads too.** Rejected. It solves verification by deleting the thing being verified,
and the result would read like the commentary — correct, quantified and saying nothing a table
does not.

**Snapshot the prose and fail on change.** Cheap, and it would have caught neither error, because
neither sentence changed. The data moved underneath prose that stayed put. A snapshot detects
edits; the failure here is the absence of an edit.

**Review the pack before each release.** This is what was already happening, and it produced two
false sentences that survived a phase. Human review is the gate for whether the argument is
*worth making*; it is a poor gate for whether a superlative is still true across four scenarios
and three years.

**A prose-quality score.** Rejected, and the phase-6 report was right to reject it: readability
computed from the text is a measurement of the text by the text.

## Consequences

- Editing a lead now costs more: the sentence, its claim, and the perturbation that falsifies it.
  That is the intended price. Fifteen unchecked assertions in the client-facing artifact was the
  cheaper arrangement and it was carrying two errors.
- The claims are a second implementation of parts of the pack's arithmetic, and they will drift if
  the pack changes and they do not. `test_every_claim_is_attached_to_something_in_the_pack` and
  the coverage test are what make the drift loud.
- Some claims are checked at a coarser grain than the sentence implies. "Roughly breakeven" is a
  band (±5% EBITDA margin) declared in `claims.py` rather than a phrase; "not one for one" is a
  growth ratio outside 0.90–1.10. Naming the threshold is the honest version of a word that would
  otherwise mean whatever the reader assumed.
- The pattern generalises to the README and the case study in phase 7, both of which quote figures
  in prose today with nothing holding them to the model.
