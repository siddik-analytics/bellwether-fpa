"""Commentary constrained to what it can prove — criteria 6.13 to 6.19.

These tests cannot establish that the prose is *good*. They establish that it is not lying:
every number traceable to the bridge, every causal claim backed by an effect that computed it,
and what is not explained said rather than omitted. Judging the writing is a reader's job, and
R-4 records that deliberately rather than inventing a quality metric — which would be an oracle
derived from the system under test.
"""

from __future__ import annotations

import re

import pandas as pd
import pytest

from bellwether.data import generate
from bellwether.transform import bridge, commentary, semantic, star

MONEY = re.compile(r"\$([\d,]+(?:\.\d+)?)(M?)")


@pytest.fixture(scope="module")
def blocks() -> dict[str, commentary.Block]:
    tables = generate.generate()
    schema = star.build_star(tables)
    gl = schema["fact_gl"].assign(year=pd.to_datetime(schema["fact_gl"]["date"]).dt.year)
    accounts = tables["dim_gl_account"]

    def side(label, version, year):
        sub = gl[
            (gl["version_name"] == version)
            & (gl["year"] == year)
            & (gl["scenario_name"] == "Balanced Base")
        ]
        revenue, profit = {}, {}
        for channel in bridge.CHANNELS:
            ladder = semantic.evaluate_ladder(sub[sub["channel_allocation"] == channel], accounts)
            revenue[channel], profit[channel] = ladder["Net Revenue"], ladder["Gross Profit"]
        corporate = semantic.evaluate_ladder(
            sub[sub["channel_allocation"] == "Unallocated corporate"], accounts
        )
        return bridge.quantities_from_ledger(label, revenue, profit, corporate["Gross Profit"])

    return {
        "budget": commentary.block(
            "Performance against budget",
            bridge.build("Gross Profit", side("b", "Budget", 2025), side("a", "Actual", 2025)),
            "FY2025 gross profit",
            "budget",
        ),
        "year": commentary.block(
            "Year on year",
            bridge.build("Gross Profit", side("a24", "Actual", 2024), side("a25", "Actual", 2025)),
            "FY2025 gross profit",
            "FY2024",
        ),
        "forecast": commentary.block(
            "Forecast revision",
            bridge.build(
                "Gross Profit", side("b26", "Budget", 2026), side("f26", "Latest Forecast", 2026)
            ),
            "FY2026 gross profit",
            "budget",
        ),
    }


def _numbers_in(text: str) -> list[float]:
    out = []
    for value, millions in MONEY.findall(text):
        amount = float(value.replace(",", ""))
        out.append(amount * 1_000_000 if millions else amount)
    return out


def test_every_number_in_the_prose_is_one_the_bridge_produced(blocks) -> None:
    """6.13 — parsed back out of the finished sentence, not read off the object that made it."""
    for name, block in blocks.items():
        printed = _numbers_in(block.prose)
        claimed = [abs(n) for n in block.numbers]
        for value in printed:
            assert any(abs(value - c) <= max(1.0, abs(c) * 0.005) for c in claimed), (
                f"{name}: {value} appears in the prose and not in the bridge"
            )


def test_every_causal_claim_names_an_effect_that_computed_it(blocks) -> None:
    """6.14 — there is no path from an adjective to a number."""
    known = {"Revenue", "Channel mix", "Margin rate", "Unexplained at this grain"}
    for name, block in blocks.items():
        assert block.claims, name
        for claim in block.claims:
            assert claim in known, f"{name}: {claim} is not an effect the bridge computes"


def test_immaterial_movements_are_named_as_immaterial_with_their_size(blocks) -> None:
    """6.15 and 6.17 — filtered, and visibly filtered."""
    block = blocks["budget"]
    assert "Below the $25,000 threshold" in block.prose
    assert "Channel mix" in block.prose
    assert block.threshold_note == "Movements below $25,000 are not discussed."


def test_the_grain_limitation_is_stated_where_it_applies(blocks) -> None:
    """R-3 — a comparison that could only be made at blended grain says so."""
    assert "blended margin rather than by channel" in blocks["forecast"].prose
    assert "blended margin rather than by channel" not in blocks["budget"].prose


def test_commentary_is_deterministic(blocks) -> None:
    """6.16 — same data, same sentences."""
    base, comparison = _rebuild()
    again = commentary.block(
        "Performance against budget",
        bridge.build("Gross Profit", base, comparison),
        "FY2025 gross profit",
        "budget",
    )
    assert again.prose == blocks["budget"].prose
    assert again.numbers == blocks["budget"].numbers


def _rebuild():
    tables = generate.generate()
    schema = star.build_star(tables)
    gl = schema["fact_gl"].assign(year=pd.to_datetime(schema["fact_gl"]["date"]).dt.year)
    accounts = tables["dim_gl_account"]

    def side(label, version):
        sub = gl[
            (gl["version_name"] == version)
            & (gl["year"] == 2025)
            & (gl["scenario_name"] == "Balanced Base")
        ]
        revenue, profit = {}, {}
        for channel in bridge.CHANNELS:
            ladder = semantic.evaluate_ladder(sub[sub["channel_allocation"] == channel], accounts)
            revenue[channel], profit[channel] = ladder["Net Revenue"], ladder["Gross Profit"]
        corporate = semantic.evaluate_ladder(
            sub[sub["channel_allocation"] == "Unallocated corporate"], accounts
        )
        return bridge.quantities_from_ledger(label, revenue, profit, corporate["Gross Profit"])

    return side("b", "Budget"), side("a", "Actual")


def test_direction_words_match_the_sign_convention(blocks) -> None:
    """6.19 — a favourable movement never reads as a shortfall."""
    budget, year = blocks["budget"], blocks["year"]
    assert "behind budget" in budget.prose, "gross profit was below budget"
    assert "ahead of FY2024" in year.prose, "gross profit rose year on year"
    for block in blocks.values():
        for sentence in block.sentences:
            if sentence.kind != "finding":
                continue
            amount = sentence.numbers[0]
            assert (" added " in sentence.text) == (amount > 0), sentence.text
            assert (" cost " in sentence.text) == (amount <= 0), sentence.text


def test_commentary_is_generated_in_the_transform_layer(blocks) -> None:
    """6.18 — commentary is an originated value, so it lives with the other originated values."""
    from bellwether.paths import REPO_ROOT

    offenders = []
    for package in ("workbook", "excel_stage"):
        for path in (REPO_ROOT / "src" / "bellwether" / package).rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if "commentary" in text and "import" in text:
                for line in text.splitlines():
                    if "commentary" in line and line.strip().startswith(("import", "from")):
                        offenders.append(f"{package}/{path.name}: {line.strip()}")
    assert not offenders or all("transform" in o for o in offenders), offenders
