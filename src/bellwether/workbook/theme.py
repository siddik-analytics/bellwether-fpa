"""Workbook skin — declarative, so a reskin is data rather than a rewrite.

The workbook has three layers and this is the only one that changes per client. It holds no
model logic and imports nothing from the semantic layer; a test asserts that, because the
separation is worth nothing if it depends on discipline.

``xlsxwriter`` binds Format objects to a workbook instance, so a theme cannot itself be a bag of
formats. It is plain data, resolved into concrete formats once at build time by ``resolve``.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

MONEY = "#,##0;(#,##0)"
MONEY_CENTS = "#,##0.00;(#,##0.00)"
PERCENT = "0.0%;(0.0%)"
MULTIPLE = '0.00"x"'
DATE_MONTH = "mmm-yy"
INTEGER = "#,##0"


@dataclass(frozen=True)
class Theme:
    """Everything a reskin touches. Nothing here decides a number."""

    name: str = "Bellwether default"

    font: str = "Calibri"
    font_size: int = 10
    heading_font: str = "Calibri"

    ink: str = "#1F2933"
    muted: str = "#7B8794"
    rule: str = "#CBD2D9"
    accent: str = "#1D4E89"
    accent_light: str = "#E3ECF5"
    surface: str = "#FFFFFF"
    band: str = "#F5F7FA"

    positive: str = "#0B6E4F"
    negative: str = "#A4243B"
    #: The actual/forecast boundary a reader must not miss — contract §8, phase 4 E-d.
    boundary: str = "#B98B00"
    boundary_fill: str = "#FFF8E1"

    #: Input cells are conventionally a different colour so a user knows what is safe to change.
    input_ink: str = "#0B4F9E"
    input_fill: str = "#EEF4FC"

    tab_colours: dict[str, str] = field(
        default_factory=lambda: {
            "Cover": "#1D4E89",
            "Assumptions": "#0B4F9E",
            "P&L": "#1F2933",
            "Balance sheet": "#1F2933",
            "Cash flow": "#1F2933",
            "Scenarios": "#0B6E4F",
            "Sensitivity": "#B98B00",
            "Documentation": "#7B8794",
        }
    )

    column_width_label: float = 42.0
    column_width_month: float = 11.5
    freeze_at: tuple[int, int] = (5, 2)


#: A second theme, used only to prove the separation holds — criterion 4.18 builds the whole
#: workbook under both and asserts identical values with different formats.
SLATE = Theme(
    name="Slate",
    font="Segoe UI",
    heading_font="Segoe UI Semibold",
    ink="#111827",
    muted="#6B7280",
    rule="#D1D5DB",
    accent="#374151",
    accent_light="#F3F4F6",
    band="#FAFAFA",
    positive="#065F46",
    negative="#991B1B",
    boundary="#92400E",
    boundary_fill="#FEF3C7",
    input_ink="#1E40AF",
    input_fill="#EFF6FF",
)


def resolve(workbook, theme: Theme) -> dict[str, object]:
    """Materialise the theme into xlsxwriter formats bound to this workbook."""
    base = {"font_name": theme.font, "font_size": theme.font_size, "font_color": theme.ink}

    def fmt(**overrides):
        return workbook.add_format({**base, **overrides})

    return {
        "title": fmt(
            font_name=theme.heading_font, font_size=20, font_color=theme.accent, bold=True
        ),
        "subtitle": fmt(font_size=12, font_color=theme.muted),
        "heading": fmt(
            font_name=theme.heading_font, font_size=12, bold=True, font_color=theme.accent
        ),
        "column_header": fmt(bold=True, bottom=1, border_color=theme.rule, align="right"),
        "column_header_left": fmt(bold=True, bottom=1, border_color=theme.rule),
        "label": fmt(),
        "label_indent": fmt(indent=1),
        "label_total": fmt(bold=True, top=1, border_color=theme.rule),
        "money": fmt(num_format=MONEY, align="right"),
        "money_total": fmt(num_format=MONEY, bold=True, top=1, border_color=theme.rule),
        "money_band": fmt(num_format=MONEY, bg_color=theme.band),
        "percent": fmt(num_format=PERCENT),
        "percent_total": fmt(num_format=PERCENT, bold=True, top=1, border_color=theme.rule),
        "multiple": fmt(num_format=MULTIPLE),
        "integer": fmt(num_format=INTEGER),
        "month": fmt(
            num_format=DATE_MONTH, bold=True, align="right", bottom=1, border_color=theme.rule
        ),
        "boundary_header": fmt(
            num_format=DATE_MONTH,
            bold=True,
            align="right",
            bottom=1,
            left=2,
            left_color=theme.boundary,
            border_color=theme.rule,
            bg_color=theme.boundary_fill,
        ),
        "boundary_cell": fmt(num_format=MONEY, left=2, left_color=theme.boundary),
        "input": fmt(
            num_format=MONEY,
            font_color=theme.input_ink,
            bg_color=theme.input_fill,
            border=1,
            border_color=theme.rule,
        ),
        "input_percent": fmt(
            num_format=PERCENT,
            font_color=theme.input_ink,
            bg_color=theme.input_fill,
            border=1,
            border_color=theme.rule,
        ),
        "note": fmt(font_size=9, font_color=theme.muted, italic=True),
        "disclosure": fmt(font_size=9, font_color=theme.muted, italic=True),
        "not_applicable": fmt(font_color=theme.muted, italic=True, align="center"),
        "selector": fmt(
            font_color=theme.input_ink,
            bg_color=theme.input_fill,
            bold=True,
            border=1,
            border_color=theme.accent,
        ),
    }


def variant(theme: Theme, **overrides) -> Theme:
    """A reskin: one call, no model code touched."""
    return replace(theme, **overrides)
