"""The pack's hand-written prose, checked against the data — R-4, closed.

Phase 6 shipped with the section leads and exhibit rationales hand-written. That was right: an
argument is what the reader is paying for, and generating it produces the templated prose
`commentary.py` exists to avoid. But "Consolidation is the only plan that reaches profitability"
is a claim, and in a project where the figures have moved repeatedly, nothing forced it to stay
true.

So the sentence stays hand-written and the claim inside it became a predicate. This module
enforces three things:

* **every claim holds** against the data the pack was built from;
* **every sentence is covered** by a claim, so prose cannot be added without one;
* **every claim can fail**, which is ADR 0022's negative control applied one claim at a time.

The third is the load-bearing one. Twenty-one predicates that all return `True` prove nothing
unless each is shown to return `False` when the world changes under it, so `FALSIFIERS` names,
for every one of them the perturbation that must break it.
"""

from __future__ import annotations

import re

import pandas as pd
import pytest

from bellwether.transform import claims, pack

#: Words that turn a sentence into an assertion about the data. A sentence carrying one of these,
#: or any digit, cannot be recorded as framing — that is the route an unchecked claim would take.
QUANTIFIERS = (
    "only",
    "never",
    "every",
    "all ",
    "none",
    "neither",
    "both",
    "highest",
    "lowest",
    "largest",
    "smallest",
    "slowest",
    "best",
    "worst",
    "entirely",
    "whole",
)

#: Split on a full stop followed by a space. Money is written `$10.60M`, so a decimal point never
#: has a space after it and never splits a sentence.
_SENTENCE = re.compile(r"(?<=\.)\s+")


def sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE.split(text.strip()) if s.strip()]


@pytest.fixture(scope="module")
def composed(star_tables) -> tuple:
    gl = star_tables["fact_gl"]
    return pack.compose(star_tables, gl), pack.evidence(star_tables, gl)


def prose_units(sections) -> list[tuple[str, str, tuple]]:
    """Every hand-written passage in the pack, with the claims attached to it."""
    units = [(f"{s.title} — lead", s.lead, s.claims) for s in sections]
    units += [(f"{s.title} — {e.key}", e.why, e.claims) for s in sections for e in s.exhibits]
    return units


def test_every_claim_holds(composed) -> None:
    """The claims themselves. A failure here means the pack states something untrue."""
    _, evidence = composed
    verdicts = {claim.sentence: claim.verdict(evidence) for claim in claims.ALL}
    broken = {s: v.detail for s, v in verdicts.items() if not v.holds}
    assert not broken, broken
    print(f"\nR-4 — {len(verdicts)} claims in the pack's prose, checked against the ledger:")
    for sentence, verdict in verdicts.items():
        print(f'  "{sentence[:58]}"\n      {verdict.detail}')


def test_every_sentence_is_covered_by_a_claim(composed) -> None:
    """Prose cannot be added without saying what it asserts.

    The coverage direction matters more than the claim count: a lead gains a sentence far more
    easily than it gains a predicate, and this is what stops the two drifting apart.
    """
    sections, _ = composed
    uncovered = []
    for where, text, attached in prose_units(sections):
        for sentence in sentences(text):
            if not any(claim.sentence in sentence for claim in attached):
                uncovered.append(f"{where}: {sentence}")
    assert not uncovered, "sentences with no claim:\n" + "\n".join(uncovered)


def test_a_sentence_that_states_a_fact_is_not_recorded_as_framing(composed) -> None:
    """Framing is for sentences that argue. It is not a way past the checks."""
    sections, _ = composed
    smuggled = []
    for where, text, attached in prose_units(sections):
        for sentence in sentences(text):
            factual = any(ch.isdigit() for ch in sentence) or any(
                word in sentence.lower() for word in QUANTIFIERS
            )
            if not factual:
                continue
            covering = [c for c in attached if c.sentence in sentence]
            if not any(c.kind == "verified" for c in covering):
                smuggled.append(f"{where}: {sentence}")
    assert not smuggled, "factual sentences covered only by framing:\n" + "\n".join(smuggled)


def test_every_claim_is_attached_to_something_in_the_pack(composed) -> None:
    """`claims.ALL` and the pack must not drift — an orphan claim is checked but never read."""
    sections, _ = composed
    attached = {c.sentence for _, _, group in prose_units(sections) for c in group}
    orphans = {c.sentence for c in claims.ALL} - attached
    assert not orphans, orphans


# --- the negative control -----------------------------------------------------------------------


def _swap(frame: pd.DataFrame, column: str, left: str, right: str) -> pd.DataFrame:
    frame = frame.copy()
    frame[column] = frame[column].replace({left: right, right: left})
    return frame


def _perturb(name: str, tables: dict[str, pd.DataFrame], monkeypatch) -> claims.Evidence:
    """Change one thing about the world, and return the evidence it produces."""
    tables = dict(tables)
    gl = tables["fact_gl"]
    accounts = tables["dim_gl_account"]

    if name == "channels swapped":
        gl = _swap(gl, "channel_allocation", "DTC", "Wholesale")
    elif name == "scenarios swapped":
        gl = _swap(gl, "scenario_name", claims.CONSOLIDATION, "Wholesale Acceleration")
        tables["fact_financing_monthly"] = _swap(
            tables["fact_financing_monthly"],
            "scenario_name",
            claims.CONSOLIDATION,
            "Wholesale Acceleration",
        )
    elif name == "no corporate block":
        gl = gl[gl["channel_allocation"] != claims.CORPORATE]
    elif name == "no equity raised":
        equity = set(accounts.loc[accounts["account_type"] == "equity", "account_code"])
        gl = gl[~gl["account_code"].isin(equity)]
    elif name == "nothing breaches":
        schedule = tables["fact_financing_monthly"].copy()
        schedule["covenant_breached"] = False
        schedule["revolver_drawn"] = 0.0
        tables["fact_financing_monthly"] = schedule
    elif name == "supply chain costs nothing":
        gl = gl[gl["department_name"] != pack.SUPPLY_CHAIN_DEPARTMENT]
    elif name == "the thresholds admit anything":
        monkeypatch.setattr(claims, "BREAKEVEN_BAND", 0.0)
        monkeypatch.setattr(claims, "ONE_FOR_ONE", (0.0, 1e9))
    elif name == "no revenue in the final year":
        revenue = set(accounts.loc[accounts["account_type"] == "revenue", "account_code"])
        year = pd.to_datetime(gl["date"]).dt.year
        gl = gl[~(gl["account_code"].isin(revenue) & (year == year.max()))]
    elif name == "no budget":
        gl = gl[gl["version_name"] != "Budget"]
    elif name == "no bridge":
        return claims.Evidence(tables, gl, bridge=None)
    else:  # pragma: no cover — a typo in the table below, not a runtime path
        raise AssertionError(f"unknown perturbation {name!r}")

    tables["fact_gl"] = gl
    return pack.evidence(tables, gl)


#: For each claim, the change to the world that must break it. A claim with no entry here has
#: never been shown to be capable of failing, and `test_every_claim_has_a_falsifier` says so.
FALSIFIERS = {
    "of net revenue and an EBITDA loss of": "no corporate block",
    "in June 2024": "no equity raised",
    "at roughly breakeven": "the thresholds admit anything",
    "on a wholesale growth story": "channels swapped",
    "Both channels are contribution-positive, so neither is the loss": "no corporate block",
    "The whole of it is a corporate cost base": "no corporate block",
    "grew with it — directionally, but not one for one": "the thresholds admit anything",
    "The covenant, not earnings, decides which plan is available": "nothing breaches",
    "The plan with the highest revenue is the one that breaches": "nothing breaches",
    "is the only plan that reaches profitability inside the horizon": "scenarios swapped",
    "the only one that never draws the facility": "scenarios swapped",
    "It does so on the lowest revenue of the four": "scenarios swapped",
    "Neither channel is the loss": "no corporate block",
    "choosing one manufactures precision the business does not have": (
        "supply chain costs nothing"
    ),
    "the best cumulative EBITDA of the three that grow is the one that runs out of room": (
        "nothing breaches"
    ),
    "Both show up here as named causes rather than as a single unexplained variance": "no bridge",
    "The only plan that reaches profitability is the one that grows slowest": "scenarios swapped",
    "A brand that shifted toward wholesale and posted a loss": "no corporate block",
    "The explanation is entirely in working capital": "nothing breaches",
    "It is still a larger company in FY2028 than it is today": "no revenue in the final year",
    "The budget was approved before the April supplier increase and before the": "no budget",
}


def test_every_verified_claim_has_a_falsifier() -> None:
    verified = {c.sentence for c in claims.ALL if c.kind == "verified"}
    assert verified - set(FALSIFIERS) == set(), "claims never shown capable of failing"
    assert set(FALSIFIERS) - verified == set(), "falsifiers for claims that no longer exist"


@pytest.mark.parametrize("sentence", sorted(FALSIFIERS))
def test_the_claim_fails_when_the_world_changes(sentence, star_tables, monkeypatch) -> None:
    """ADR 0022's first countermeasure, one claim at a time.

    A predicate that returns True proves nothing unless it can return False. This breaks the
    specific fact each claim rests on and requires the claim to notice.
    """
    claim = next(c for c in claims.ALL if c.sentence == sentence)
    evidence = _perturb(FALSIFIERS[sentence], star_tables, monkeypatch)
    verdict = claim.verdict(evidence)
    assert not verdict.holds, (
        f'"{sentence}" still held under "{FALSIFIERS[sentence]}" — {verdict.detail}'
    )
