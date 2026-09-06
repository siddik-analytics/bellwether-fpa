"""One expression, three backends — ADR 0019, phase 5 F-b."""

from __future__ import annotations

import pandas as pd
import pytest

from bellwether.transform import expressions, semantic

# --- the language itself ---------------------------------------------------------------------


def test_dependencies_come_from_the_expression() -> None:
    assert expressions.dependencies("[A] - [B] + [A]") == ("A", "B")


def test_scalar_and_series_share_one_expression() -> None:
    """The property that stopped the ladder existing twice."""
    derivation = "[Gross Revenue] - [Contra Revenue]"
    scalar = expressions.evaluate(derivation, {"Gross Revenue": 100.0, "Contra Revenue": 30.0})
    series = expressions.evaluate(
        derivation,
        {"Gross Revenue": pd.Series([100.0, 50.0]), "Contra Revenue": pd.Series([30.0, 5.0])},
    )
    assert scalar == 70.0
    assert series.tolist() == [70.0, 45.0]


@pytest.mark.parametrize(
    ("denominator", "expected"),
    [(4.0, 2.5), (0.0, 0.0)],
)
def test_divide_falls_back_rather_than_raising(denominator, expected) -> None:
    """A month with no revenue is an expected state, not an error."""
    assert expressions.evaluate("DIVIDE([A], [B])", {"A": 10.0, "B": denominator}) == expected


def test_divide_falls_back_elementwise_on_a_series() -> None:
    result = expressions.evaluate(
        "DIVIDE([A], [B])", {"A": pd.Series([10.0, 10.0]), "B": pd.Series([4.0, 0.0])}
    )
    assert result.tolist() == [2.5, 0.0]


@pytest.mark.parametrize(
    "derivation",
    [
        "__import__('os').getcwd()",
        "[A].values",
        "SUM([A])",
        "[A] if [B] else 0",
        "lambda: 1",
    ],
)
def test_only_arithmetic_survives_the_parser(derivation) -> None:
    """A definition table should not be able to express anything but arithmetic."""
    with pytest.raises(expressions.DerivationError):
        expressions.evaluate(derivation, {"A": 1.0, "B": 2.0})


def test_an_undefined_reference_names_itself() -> None:
    with pytest.raises(expressions.DerivationError, match="Missing"):
        expressions.evaluate("[A] - [Missing]", {"A": 1.0})


def test_a_cycle_is_reported_with_the_path() -> None:
    with pytest.raises(expressions.DerivationError, match="circular"):
        expressions.resolution_order({"A": "[B]", "B": "[A]"})


# --- the three backends ----------------------------------------------------------------------


def test_dax_is_close_to_a_pass_through() -> None:
    """The translation surface is small enough to read, which is what 5.10 rests on."""
    assert expressions.to_dax("[Gross Profit] - [Operating Expense]") == (
        "[Gross Profit] - [Operating Expense]"
    )


def test_excel_resolves_references_to_cells() -> None:
    assert expressions.to_excel("[A] - [B]", {"A": "B6", "B": "B7"}) == "B6-B7"


def test_excel_divide_becomes_a_guard_not_an_error_suppressor() -> None:
    """IFERROR would hide the divisions that are not expected to fail."""
    formula = expressions.to_excel("DIVIDE([A], [B])", {"A": "B10", "B": "B8"})
    assert formula == "IF(B8=0,0,B10/B8)"
    assert "IFERROR" not in formula


def test_the_three_backends_agree_on_every_shipped_derivation() -> None:
    """Whatever the ladder is, all three consumers must be able to express it."""
    cells = {name: f"B{index + 1}" for index, name in enumerate(semantic.ALL_METRICS)}
    for name, metric in semantic.DERIVED.items():
        assert metric.derivation, name
        expressions.to_dax(metric.derivation)
        excel = expressions.to_excel(metric.derivation, cells)
        assert "[" not in excel, f"{name} left an unresolved reference: {excel}"


# --- the definitions themselves ----------------------------------------------------------------


def test_every_derived_metric_resolves_in_dependency_order() -> None:
    order = semantic.DERIVATION_ORDER
    seen: set[str] = set(semantic.BASE)
    for name in order:
        for dependency in semantic.DERIVED[name].depends_on:
            assert dependency in seen, f"{name} reads {dependency} before it is computed"
        seen.add(name)
    assert set(order) == set(semantic.DERIVED)


def test_depends_on_cannot_disagree_with_the_arithmetic() -> None:
    """It is derived from the expression rather than stored beside it."""
    metric = semantic.DERIVED["Net Revenue"]
    assert metric.depends_on == ("Gross Revenue", "Contra Revenue")
    assert not hasattr(type(metric), "_depends_on")


def test_a_derived_metric_refuses_to_be_evaluated_as_a_base_metric() -> None:
    with pytest.raises(ValueError, match="derived"):
        semantic.DERIVED["Net Revenue"].evaluate(pd.DataFrame(), pd.DataFrame())


def test_cost_lines_carry_their_direction() -> None:
    """B-4 — variance direction is metric metadata, not a caller's argument."""
    for name in (
        "Cost of Sales",
        "Operating Expense",
        "Contra Revenue",
        "Other Income and Expense",
    ):
        assert semantic.ALL_METRICS[name].is_cost, name
    for name in ("Gross Revenue", "Net Revenue", "Gross Profit", "EBITDA", "Net Income"):
        assert not semantic.ALL_METRICS[name].is_cost, name


def test_variance_direction_comes_from_the_definition() -> None:
    """Favourable is positive on both sides of the P&L — §9 check 24."""
    assert semantic.variance_for("Gross Revenue", actual=110, comparison=100) > 0
    assert semantic.variance_for("Cost of Sales", actual=90, comparison=100) > 0
    assert semantic.variance_for("Gross Revenue", actual=90, comparison=100) < 0
    assert semantic.variance_for("Cost of Sales", actual=110, comparison=100) < 0
