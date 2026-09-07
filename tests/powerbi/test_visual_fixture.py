"""Generated visuals checked against Power BI Desktop's own — criterion 5.35.

The second Desktop reference, `tests/fixtures/powerbi-desktop-visuals/`, contains one visual of
each of 24 types. Every generated visual container is asserted against it: the same `$schema`,
the same key set at every level, and a `visualType` drawn from the vocabulary the reference
proves rather than from memory.

That last point already mattered. The modern card is **`cardVisual`**; a guess would have written
`card`, which is what the earlier invented report format used, and Power BI would not have
recognised it.

**What the reference does not contain, and what therefore is not generated.** All 24 visuals are
unbound placeholders — no `query`, no `projections`, no field reference of any kind — and there
is no textbox among them. So the container shape is authoritative and the *binding* is still
unknown. Criteria 5.27 and 5.28 remain open, and the tests below say so rather than asserting
around it.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from bellwether.data import generate
from bellwether.paths import REPO_ROOT
from bellwether.powerbi import tmdl
from bellwether.transform import star

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "powerbi-desktop-visuals"


def _json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def reference() -> list[dict]:
    visuals = sorted(FIXTURE.rglob("visual.json"))
    assert visuals, f"no visuals in the fixture at {FIXTURE}"
    return [_json(path) for path in visuals]


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> pathlib.Path:
    out = tmp_path_factory.mktemp("visuals")
    tmdl.build(star.build_star(generate.generate()), out)
    return out


def _generated(built: pathlib.Path) -> list[dict]:
    return [_json(path) for path in sorted(built.rglob("visual.json"))]


# --- the fixture itself -----------------------------------------------------------------------


def test_the_fixture_is_desktops_own_and_carries_no_secrets() -> None:
    for path in FIXTURE.rglob("*"):
        if not path.is_file() or path.suffix == ".md":
            continue
        assert ".pbi" not in path.parts, path
        assert path.suffix not in {".abf", ".pbix", ".pbit"}, path
        assert "securityBindingsSignature" not in path.read_text(encoding="utf-8-sig")


def test_the_reference_has_one_shape_for_every_visual(reference) -> None:
    """24 types, one envelope. That uniformity is what makes it safe to generate from."""
    assert len(reference) >= 20
    assert {tuple(sorted(v)) for v in reference} == {("$schema", "name", "position", "visual")}
    assert {tuple(sorted(v["position"])) for v in reference} == {
        ("height", "tabOrder", "width", "x", "y", "z")
    }


# --- the generated visuals against it ------------------------------------------------------------


def test_generated_visuals_use_desktops_schema(built, reference) -> None:
    expected = {v["$schema"] for v in reference}
    assert len(expected) == 1
    generated = _generated(built)
    assert generated, "no visuals were generated"
    for visual in generated:
        assert visual["$schema"] in expected, visual["name"]


def test_generated_visuals_have_desktops_key_set(built, reference) -> None:
    """Not a subset and not a superset — an extra key is an invented contract."""
    expected_top = {tuple(sorted(v)) for v in reference}.pop()
    expected_position = {tuple(sorted(v["position"])) for v in reference}.pop()
    for visual in _generated(built):
        assert tuple(sorted(visual)) == expected_top, visual["name"]
        assert tuple(sorted(visual["position"])) == expected_position, visual["name"]
        assert set(visual["visual"]) <= {"visualType", "drillFilterOtherVisuals"}, visual["name"]


def test_the_visual_type_comes_from_desktops_vocabulary(built, reference) -> None:
    """`cardVisual`, not `card`. The earlier invented format used the name that does not exist."""
    known = {v["visual"]["visualType"] for v in reference}
    assert tmdl.CARD_VISUAL in known
    for visual in _generated(built):
        assert visual["visual"]["visualType"] in known, visual["visual"]["visualType"]


def test_visual_names_are_desktop_shaped_and_deterministic(built) -> None:
    """Twenty lowercase hex characters, and the same on every build."""
    for visual in _generated(built):
        name = visual["name"]
        assert len(name) == 20, name
        assert all(c in "0123456789abcdef" for c in name), name
    assert tmdl.visual_name("executive-summary", "EBITDA") == tmdl.visual_name(
        "executive-summary", "EBITDA"
    )
    assert tmdl.visual_name("a", "EBITDA") != tmdl.visual_name("b", "EBITDA")


def test_every_named_measure_gets_a_visual(built) -> None:
    definition = built / f"{tmdl.PROJECT}.Report" / "definition" / "pages"
    for display_name, _, measures in tmdl.PAGES:
        page_dir = definition / tmdl.page_name(display_name)
        for measure in measures:
            visual = (
                page_dir
                / "visuals"
                / tmdl.visual_name(tmdl.page_name(display_name), measure)
                / "visual.json"
            )
            assert visual.is_file(), f"{display_name} / {measure}"


def test_visuals_do_not_overlap_on_a_page(built) -> None:
    """Geometry Desktop would render on top of itself is geometry nobody checked."""
    definition = built / f"{tmdl.PROJECT}.Report" / "definition" / "pages"
    for page_dir in definition.iterdir():
        if not page_dir.is_dir():
            continue
        boxes = [_json(p)["position"] for p in sorted(page_dir.rglob("visual.json"))]
        for i, a in enumerate(boxes):
            for b in boxes[i + 1 :]:
                separated = (
                    a["x"] + a["width"] <= b["x"]
                    or b["x"] + b["width"] <= a["x"]
                    or a["y"] + a["height"] <= b["y"]
                    or b["y"] + b["height"] <= a["y"]
                )
                assert separated, f"{page_dir.name}: {a} overlaps {b}"


def test_visuals_fit_inside_the_page(built) -> None:
    definition = built / f"{tmdl.PROJECT}.Report" / "definition" / "pages"
    for page_dir in definition.iterdir():
        if not page_dir.is_dir():
            continue
        page = _json(page_dir / "page.json")
        for path in page_dir.rglob("visual.json"):
            box = _json(path)["position"]
            assert box["x"] + box["width"] <= page["width"], path.parent.name
            assert box["y"] + box["height"] <= page["height"], path.parent.name


# --- what is still missing, asserted so it cannot be closed by a guess ---------------------------


def test_the_reference_contains_no_field_binding(reference) -> None:
    """The reason 5.27 is still open, stated as a fact about the fixture.

    If a future reference does carry a binding this test fails, which is the intended signal:
    the gap can be closed, and the generator should be taught the real shape.
    """
    text = json.dumps(reference)
    for token in ("query", "projections", "queryRef", "dataRoles"):
        assert token not in text, f"the reference now shows {token}; bindings can be generated"


def test_the_reference_contains_no_textbox(reference) -> None:
    """The reason 5.28 cannot be met on report pages."""
    types = {v["visual"]["visualType"] for v in reference}
    assert "textbox" not in types, "a textbox reference exists; the disclosure can go on a page"


def test_generated_visuals_are_unbound_and_that_is_deliberate(built) -> None:
    """A card with an invented binding would look finished and be wrong."""
    for visual in _generated(built):
        assert set(visual["visual"]) == {"visualType", "drillFilterOtherVisuals"}, (
            "a binding appeared without an authoritative example to generate it from"
        )
