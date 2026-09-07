"""The variance bridge — criteria 6.9 to 6.12."""

from __future__ import annotations

import pandas as pd
import pytest

from bellwether.data import generate
from bellwether.transform import bridge, semantic, star


@pytest.fixture(scope="module")
def sides() -> dict:
    tables = generate.generate()
    schema = star.build_star(tables)
    gl = schema["fact_gl"]
    gl = gl.assign(year=pd.to_datetime(gl["date"]).dt.year)
    accounts = tables["dim_gl_account"]

    def side(label, version, year, scenario="Balanced Base"):
        sub = gl[
            (gl["version_name"] == version)
            & (gl["year"] == year)
            & (gl["scenario_name"] == scenario)
        ]
        revenue, profit = {}, {}
        for channel in bridge.CHANNELS:
            ladder = semantic.evaluate_ladder(sub[sub["channel_allocation"] == channel], accounts)
            revenue[channel] = ladder["Net Revenue"]
            profit[channel] = ladder["Gross Profit"]
        corporate = semantic.evaluate_ladder(
            sub[sub["channel_allocation"] == "Unallocated corporate"], accounts
        )
        return bridge.quantities_from_ledger(label, revenue, profit, corporate["Gross Profit"])

    return {
        "budget_2025": side("FY2025 budget", "Budget", 2025),
        "actual_2025": side("FY2025 actual", "Actual", 2025),
        "actual_2024": side("FY2024 actual", "Actual", 2024),
        "budget_2026": side("FY2026 budget", "Budget", 2026),
        "forecast_2026": side("FY2026 forecast", "Latest Forecast", 2026),
    }


def test_the_effects_sum_to_the_movement(sides) -> None:
    """6.9 — including the residual, to the cent."""
    for base, comparison in (
        (sides["budget_2025"], sides["actual_2025"]),
        (sides["actual_2024"], sides["actual_2025"]),
        (sides["budget_2026"], sides["forecast_2026"]),
    ):
        built = bridge.build("Gross Profit", base, comparison)
        total = built.explained + built.residual.amount
        assert abs(total - built.movement) < 0.01, built.comparison.label


def test_the_movement_is_the_one_the_statements_report(sides) -> None:
    """A bridge that sums perfectly to a movement nobody reported explains nothing.

    The first version reconstructed both sides from unit economics and did exactly that: it
    balanced to $513,014 while the statements showed −$238,991.
    """
    built = bridge.build("Gross Profit", sides["budget_2025"], sides["actual_2025"])
    reported = sides["actual_2025"].total_gross_profit - sides["budget_2025"].total_gross_profit
    assert abs(built.movement - reported) < 0.01


def test_the_residual_is_its_own_line_and_never_folded_in(sides) -> None:
    """6.10 — it exists whether or not it is material."""
    built = bridge.build("Gross Profit", sides["budget_2025"], sides["actual_2025"])
    frame = built.frame()
    assert "Unexplained at this grain" in set(frame["effect"])
    assert len(frame) == len(built.effects) + 1
    assert built.residual.name not in {e.name for e in built.effects}


def test_every_named_effect_comes_from_a_measured_quantity(sides) -> None:
    """6.11 — only the residual is a remainder.

    Each effect carries the quantities it was computed from, so an effect that had been derived
    by subtracting the others would have nothing to show.
    """
    built = bridge.build("Gross Profit", sides["budget_2025"], sides["actual_2025"])
    for effect in built.effects:
        assert effect.driver, effect.name
        assert effect.detail, f"{effect.name} has no quantity behind it"
    assert not built.residual.detail, "the residual is a remainder and should show no quantity"


def test_it_reproduces_a_known_movement(sides) -> None:
    """6.12 — FY2024 to FY2025, the comparison the charter's example is drawn from."""
    built = bridge.build("Gross Profit", sides["actual_2024"], sides["actual_2025"])
    names = {e.name for e in built.effects}
    assert names == {"Revenue", "Channel mix", "Margin rate"}
    mix = next(e for e in built.effects if e.name == "Channel mix")
    assert mix.amount < 0, "DTC share fell, and DTC carries the higher margin"
    assert built.grain == "channel"


def test_the_grain_drops_when_cost_is_unallocated(sides) -> None:
    """R-2 and R-3's floor, made explicit rather than papered over.

    Forecast cost of sales has no measured units behind it, so it sits unallocated and every
    channel shows a 100% margin. A channel-mix effect computed from that would be a number with
    no meaning presented as an explanation.
    """
    built = bridge.build("Gross Profit", sides["budget_2026"], sides["forecast_2026"])
    assert built.grain == "blended"
    assert {e.name for e in built.effects} == {"Revenue", "Margin rate"}
    assert not sides["forecast_2026"].has_channel_grain
    assert sides["actual_2025"].has_channel_grain


def test_the_two_budget_causes_appear_with_the_right_signs(sides) -> None:
    """G-a's whole point: two named causes, both unfavourable, nothing else material."""
    built = bridge.build("Gross Profit", sides["budget_2025"], sides["actual_2025"])
    by_name = {e.name: e.amount for e in built.effects}
    assert by_name["Revenue"] < 0, "the launch missed"
    assert by_name["Margin rate"] < 0, "product cost rose"
    assert built.movement < 0
