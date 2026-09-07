"""Bound visuals checked against Desktop's own — criteria 5.27, 5.28 and 5.37.

The third Desktop reference, `tests/fixtures/powerbi-desktop-bound/`, is the first with fields
actually assigned. It supplied three shapes nothing before it could:

- **the query object** — `query.queryState.Data.projections[]`, each projection carrying a
  `field`, a `queryRef`, a `nativeQueryRef`, a `displayName` and a `format`;
- **the textbox** — content under `objects.general[].properties.paragraphs[].textRuns[]`;
- **the drillthrough target** — a hidden page declaring its field *twice*, as a `filterConfig`
  filter marked `howCreated: Drillthrough` and as a `pageBinding` parameter bound to that filter
  by name.

None of those could have been guessed, and the last one in particular is not a shape anyone would
invent: the same field expression appears in two places under different keys, and omitting either
leaves a page that looks configured and does not drill.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from bellwether.data import generate
from bellwether.paths import REPO_ROOT
from bellwether.powerbi import tmdl, tom
from bellwether.transform import star

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "powerbi-desktop-bound"


def _json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> pathlib.Path:
    out = tmp_path_factory.mktemp("bound")
    tmdl.build(star.build_star(generate.generate()), out)
    return out


def _visuals(built: pathlib.Path, visual_type: str) -> list[dict]:
    definition = built / f"{tmdl.PROJECT}.Report" / "definition"
    return [
        _json(p)
        for p in sorted(definition.rglob("visual.json"))
        if _json(p)["visual"]["visualType"] == visual_type
    ]


# --- the fixture -------------------------------------------------------------------------------


def test_the_fixture_carries_no_other_projects_identity() -> None:
    """It came from a different company's report, so only the shape was kept.

    Every key, nesting level and type is Desktop's. The one alteration is that the other
    project's name was replaced, which the README records — nothing here asserts on that value.
    """
    for path in FIXTURE.rglob("*.json"):
        text = path.read_text(encoding="utf-8-sig")
        assert "Helio" not in text, path
        assert "securityBindingsSignature" not in text, path


def test_the_fixture_supplies_the_three_missing_shapes() -> None:
    card = _json(FIXTURE / "visuals" / "card.json")
    textbox = _json(FIXTURE / "visuals" / "textbox.json")
    target = _json(FIXTURE / "pages" / "drillthrough-target.json")
    assert "query" in card["visual"]
    assert "objects" in textbox["visual"]
    assert "pageBinding" in target and "filterConfig" in target


# --- 5.27: bound cards ---------------------------------------------------------------


def test_the_query_object_matches_desktops_shape(built) -> None:
    """Key for key, at every level, against the reference card."""
    reference = _json(FIXTURE / "visuals" / "card.json")["visual"]["query"]
    for card in _visuals(built, tmdl.CARD_VISUAL):
        query = card["visual"]["query"]
        assert sorted(query) == sorted(reference), card["name"]
        assert sorted(query["queryState"]) == sorted(reference["queryState"])
        assert sorted(query["queryState"]["Data"]) == sorted(reference["queryState"]["Data"])
        expected_keys = sorted(reference["queryState"]["Data"]["projections"][0])
        for projection in query["queryState"]["Data"]["projections"]:
            assert sorted(projection) == expected_keys, card["name"]


def test_a_field_reference_matches_desktops_shape(built) -> None:
    """`Measure` / `Expression.SourceRef.Entity` / `Property` — the whole vocabulary."""
    reference = _json(FIXTURE / "visuals" / "card.json")
    ref_field = reference["visual"]["query"]["queryState"]["Data"]["projections"][0]["field"]
    kind = next(iter(ref_field))
    for card in _visuals(built, tmdl.CARD_VISUAL):
        field = card["visual"]["query"]["queryState"]["Data"]["projections"][0]["field"]
        assert next(iter(field)) == kind
        assert sorted(field[kind]) == sorted(ref_field[kind])
        assert sorted(field[kind]["Expression"]) == sorted(ref_field[kind]["Expression"])


def test_card_formats_come_from_the_metric(built) -> None:
    """The report is not a second place formatting is decided — 5.22, now on the visual too."""
    from bellwether.transform import semantic

    for card in _visuals(built, tmdl.CARD_VISUAL):
        projection = card["visual"]["query"]["queryState"]["Data"]["projections"][0]
        measure = projection["field"]["Measure"]["Property"]
        assert projection["format"] == semantic.ALL_METRICS[measure].format_string, measure


# --- 5.28: the disclosure textbox ----------------------------------------------------


def test_every_page_carries_the_disclosure_as_a_textbox(built) -> None:
    """5.28 — on every page a reader can land on, including the drillthrough target."""
    definition = built / f"{tmdl.PROJECT}.Report" / "definition" / "pages"
    pages = [d for d in definition.iterdir() if d.is_dir()]
    assert pages
    for page_dir in pages:
        boxes = [
            _json(p)
            for p in page_dir.rglob("visual.json")
            if _json(p)["visual"]["visualType"] == tmdl.TEXTBOX_VISUAL
        ]
        assert boxes, page_dir.name
        text = json.dumps(boxes)
        assert "illustrative company" in text, page_dir.name
        assert "synthetic" in text, page_dir.name


def test_the_textbox_matches_desktops_shape(built) -> None:
    reference = _json(FIXTURE / "visuals" / "textbox.json")["visual"]
    for box in _visuals(built, tmdl.TEXTBOX_VISUAL):
        assert sorted(box["visual"]) == sorted(reference)
        assert sorted(box["visual"]["objects"]) == sorted(reference["objects"])
        run = box["visual"]["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"][0]
        ref_run = reference["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"][0]
        assert sorted(run) == sorted(ref_run)


# --- 5.27: the drillthrough target ---------------------------------------------------


def test_the_drillthrough_target_matches_desktops_shape(built) -> None:
    """Declared twice, as the reference does it. Either half alone does not drill."""
    reference = _json(FIXTURE / "pages" / "drillthrough-target.json")
    definition = built / f"{tmdl.PROJECT}.Report" / "definition" / "pages"
    target = _json(definition / tmdl.page_name(tmdl.DRILLTHROUGH_PAGE) / "page.json")

    assert target["visibility"] == reference["visibility"]
    assert sorted(target["filterConfig"]["filters"][0]) == sorted(
        reference["filterConfig"]["filters"][0]
    )
    assert target["filterConfig"]["filters"][0]["howCreated"] == "Drillthrough"
    assert sorted(target["pageBinding"]) == sorted(reference["pageBinding"])
    assert target["pageBinding"]["type"] == "Drillthrough"
    assert sorted(target["pageBinding"]["parameters"][0]) == sorted(
        reference["pageBinding"]["parameters"][0]
    )


def test_the_binding_parameter_points_at_the_filter(built) -> None:
    """`boundFilter` naming a filter that does not exist is a page that looks configured."""
    definition = built / f"{tmdl.PROJECT}.Report" / "definition" / "pages"
    target = _json(definition / tmdl.page_name(tmdl.DRILLTHROUGH_PAGE) / "page.json")
    filters = {f["name"] for f in target["filterConfig"]["filters"]}
    for parameter in target["pageBinding"]["parameters"]:
        assert parameter["boundFilter"] in filters, parameter["boundFilter"]
        assert parameter["fieldExpr"] == target["filterConfig"]["filters"][0]["field"]


def test_only_the_drillthrough_page_is_hidden(built) -> None:
    definition = built / f"{tmdl.PROJECT}.Report" / "definition" / "pages"
    for page_dir in definition.iterdir():
        if not page_dir.is_dir():
            continue
        page = _json(page_dir / "page.json")
        hidden = page.get("visibility") == "HiddenInViewMode"
        assert hidden == (page["displayName"] == tmdl.DRILLTHROUGH_PAGE), page["displayName"]


# --- 5.37: every reference resolves against the model ---------------------------------


@pytest.mark.requires_tom
def test_every_field_reference_resolves_against_the_model(built) -> None:
    """5.37 — the check that ties the two halves of the project together.

    A card can be perfectly shaped and name a measure the model does not contain. Nothing in the
    report definition would object, and Power BI would render a broken visual. So every `Entity`
    and `Property` in the report is resolved against the model **as TOM parsed it**, not against
    the generator's own idea of what it wrote.
    """
    if not tom.available():
        pytest.skip("no Tabular Object Model assembly on this machine")
    model = tom.parse_model(built / f"{tmdl.PROJECT}.SemanticModel" / "definition")
    assert model["ok"], model.get("error")

    measures = {(t["name"], m["name"]) for t in model["tables"] for m in t["measures"]}
    columns = {(t["name"], c["name"]) for t in model["tables"] for c in t["columns"]}

    checked, unresolved = 0, []
    for path in sorted((built / f"{tmdl.PROJECT}.Report" / "definition").rglob("*.json")):
        stack = [_json(path)]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                for kind, pool in (("Measure", measures), ("Column", columns)):
                    reference = node.get(kind)
                    if isinstance(reference, dict) and "Property" in reference:
                        entity = reference["Expression"]["SourceRef"]["Entity"]
                        checked += 1
                        if (entity, reference["Property"]) not in pool:
                            unresolved.append(
                                f"{path.parent.name}: {entity}[{reference['Property']}]"
                            )
                stack.extend(node.values())
            elif isinstance(node, list):
                stack.extend(node)

    assert checked >= len(tmdl.PAGES), f"only {checked} references found"
    assert not unresolved, unresolved
