"""The board pack — criteria 6.20 to 6.25 and 6.27.

Everything checkable about the pack is checked before a PDF exists, on the composed content.
What a PDF can be asked is close to nothing: reading our own figures back out of our own export
proves the export ran, not that the pack is right (ADR 0022, defect 3). The reader is the
authority, and criterion 6.30 stays a manual gate.
"""

from __future__ import annotations

import pathlib
import re
import zipfile

import pytest

from bellwether.data import generate
from bellwether.paths import BUILD_DIR
from bellwether.transform import pack, star


@pytest.fixture(scope="module")
def sections() -> list[pack.Section]:
    tables = generate.generate()
    schema = star.build_star(tables)
    return pack.compose(tables, schema["fact_gl"])


def test_the_pack_argues_rather_than_reports(sections) -> None:
    """6.20 — a position, a tension, evidence, and what follows from it."""
    titles = [s.title for s in sections]
    assert titles == ["Position", "The tension", "Whether it is fundable", "What follows"]
    for section in sections:
        assert section.lead.strip(), section.title
    decision = sections[-1]
    assert "decision in front of the board" in decision.lead


def test_all_three_carried_exhibits_appear(sections) -> None:
    """6.21 — C-1, C-2 and C-3 from docs/phases/phase-06-carried.md."""
    keys = {e.key for s in sections for e in s.exhibits}
    assert {"allocation_sensitivity", "channel_contribution", "covenant_trace"} <= keys


def test_every_exhibit_says_why_it_earns_space(sections) -> None:
    """An exhibit with no argument for being there is a data dump with a border."""
    for section in sections:
        for exhibit in section.exhibits:
            assert exhibit.why.strip(), exhibit.key
            assert not exhibit.table.empty, exhibit.key


def test_each_comparison_is_commented_on_once(sections) -> None:
    """One variance, one framing. The against-budget movement was narrated in Position and again
    as a bridge exhibit three sections later, which read as two findings rather than one."""
    titles = [b.title for section in sections for b in section.blocks]
    assert len(titles) == len(set(titles)), f"a comparison is commented on twice: {titles}"
    by_section = {s.title: [b.title for b in s.blocks] for s in sections}
    # Both FY2025 comparisons, and the bridge that decomposes one of them, sit together at the
    # front. The pack ends on the decision rather than on the evidence for the year behind it.
    assert by_section["Position"] == ["Year on year", "Performance against budget"]
    assert by_section["What follows"] == []
    position = next(s for s in sections if s.title == "Position")
    assert [e.key for e in position.exhibits] == ["pl_bridge"]
    assert sections[-1].title == "What follows"


def test_the_threshold_is_stated_under_every_block(sections) -> None:
    """6.17 — an undisclosed filter is one the reader cannot see."""
    for section in sections:
        for block in section.blocks:
            assert "$25,000" in block.threshold_note


def test_the_pack_carries_the_disclosure(sections) -> None:
    """6.23 — synthetic data, on the artifact a client actually receives."""
    assert "illustrative company" in pack.DISCLOSURE
    assert "synthetic" in pack.DISCLOSURE


def test_the_supply_chain_cost_is_derived_from_the_ledger(sections) -> None:
    """The exhibit's argument is about how much a real number moves, so it must be the real one."""
    sensitivity = next(e for s in sections for e in s.exhibits if e.key == "allocation_sensitivity")
    table = sensitivity.table
    assert len(table) == 3, "one row per driver, channels across — six rows did not scan"
    spread = table["Cost to Wholesale"].max() - table["Cost to Wholesale"].min()
    total = float(table["Cost to DTC"].iloc[0] + table["Cost to Wholesale"].iloc[0])
    assert spread / total > 0.4, (
        "the drivers must disagree, or the argument for not choosing is empty"
    )


def test_the_pack_is_composed_without_excel(sections) -> None:
    """6.25 — deleting the COM stage leaves a complete pack definition.

    An import-graph assertion, not a text search: the module docstring names `excel_stage` in
    order to explain the boundary, and the first version of this test failed on its own prose.
    """
    import bellwether.transform.pack as module

    text = pathlib.Path(module.__file__).read_text(encoding="utf-8")
    offenders = [
        line.strip()
        for line in text.splitlines()
        if line.strip().startswith(("import ", "from "))
        and ("excel_stage" in line or "win32" in line)
    ]
    assert not offenders, offenders
    assert sections, "the pack composed with no Excel present"


def test_named_ranges_exist_for_every_exhibit(sections) -> None:
    """6.27 — the export takes a name, so layout stays in the layer that owns it."""
    names = {e.named_range for s in sections for e in s.exhibits}
    assert names == set(pack.NAMED_RANGES)
    assert len(names) == 5


def test_the_workbook_defines_those_names() -> None:
    """The other half of 6.27: the names must reach the file."""
    path = BUILD_DIR / "northlake-model.xlsx"
    if not path.exists():
        pytest.skip("run `python -m bellwether.build` first")
    workbook_xml = zipfile.ZipFile(path).read("xl/workbook.xml").decode("utf-8")
    defined = set(re.findall(r'<definedName name="([^"]+)"', workbook_xml))
    assert set(pack.NAMED_RANGES) <= defined, set(pack.NAMED_RANGES) - defined
