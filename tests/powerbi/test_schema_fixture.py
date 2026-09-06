"""Every generated `$schema` checked against Power BI Desktop's own output — criterion 5.34.

ADR 0022 again, applied to something that looks far too small to need it. Five values in the
generator were transcribed from memory and documentation, and **all five were wrong**: two files
that Desktop leaves without a `$schema` had one invented for them, the report schema was both the
wrong version and in the wrong place, `definition.pbism` was a version behind, and the database
compatibility level was 1567 rather than 1606.

None of that could have been caught by a test comparing the generator to a constant, because the
constant and the generator had the same author. So the oracle here is
`tests/fixtures/powerbi-desktop-blank/` — a blank report saved by Desktop itself.

The fixture also settled a structural question: the report is **PBIR**, with
`definition/report.json` and a file per page under `definition/pages/`, not the legacy single
`report.json` of `sections` and `visualContainers` the generator had been emitting.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from bellwether.data import generate
from bellwether.paths import REPO_ROOT
from bellwether.powerbi import tmdl, validate
from bellwether.transform import star

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "powerbi-desktop-blank"

#: Which generated file each fixture file is the authority for. The page file is matched by
#: shape rather than by name — Desktop names pages with an opaque id, this project uses a slug.
AUTHORITY: dict[str, str] = {
    "northlake.Report/definition/report.json": "northlake.Report/definition/report.json",
    "northlake.Report/definition/version.json": "northlake.Report/definition/version.json",
    "northlake.Report/definition/pages/pages.json": "northlake.Report/definition/pages/pages.json",
}


def _schema(path: pathlib.Path) -> str | None:
    return json.loads(path.read_text(encoding="utf-8-sig")).get("$schema")


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> pathlib.Path:
    out = tmp_path_factory.mktemp("schemas")
    tmdl.build(star.build_star(generate.generate()), out)
    return out


def test_the_fixture_is_present_and_is_desktops_own() -> None:
    """Without it every assertion below degrades into comparing us to ourselves."""
    assert FIXTURE.is_dir(), f"missing fixture at {FIXTURE}"
    platform = json.loads(
        (FIXTURE / "northlake.Report" / ".platform").read_text(encoding="utf-8-sig")
    )
    assert platform["metadata"]["type"] == "Report"


def test_the_fixture_carries_no_credentials_or_binaries() -> None:
    """`.pbi/localSettings.json` holds a machine-bound securityBindingsSignature."""
    for path in FIXTURE.rglob("*"):
        if not path.is_file() or path.suffix == ".md":
            continue  # the README names the excluded key in order to explain the exclusion
        assert ".pbi" not in path.parts, path
        assert path.suffix not in {".abf", ".pbix", ".pbit"}, path
        assert "securityBindingsSignature" not in path.read_text(encoding="utf-8-sig")


@pytest.mark.parametrize("relative", sorted(AUTHORITY))
def test_generated_schema_matches_desktops(relative, built) -> None:
    """The core assertion: our `$schema` is Desktop's, character for character."""
    expected = _schema(FIXTURE / relative)
    assert expected, f"{relative} carries no $schema in the fixture"
    actual = _schema(built / AUTHORITY[relative])
    assert actual == expected, f"{relative}\n  generated {actual}\n  desktop   {expected}"


def test_the_page_schema_matches_desktops(built) -> None:
    """Matched by shape: Desktop names a page with an opaque id, this project uses a slug."""
    fixture_page = next((FIXTURE / "northlake.Report/definition/pages").rglob("page.json"))
    generated = sorted((built / "northlake.Report/definition/pages").rglob("page.json"))
    assert generated, "no page files were generated"
    for page in generated:
        assert _schema(page) == _schema(fixture_page), page.parent.name


def test_files_desktop_leaves_unschemad_stay_that_way(built) -> None:
    """Two of these three had a `$schema` invented for them.

    Adding one is not harmless decoration — it asserts a contract Microsoft did not publish for
    that file, and the version in it was wrong anyway.
    """
    for relative in (
        "northlake.pbip",
        "northlake.Report/definition.pbir",
        "northlake.SemanticModel/definition.pbism",
    ):
        assert _schema(FIXTURE / relative) is None, f"fixture changed: {relative}"
        assert _schema(built / relative) is None, f"generated {relative} invented a $schema"


def test_every_schema_the_generator_knows_is_backed_by_the_fixture() -> None:
    """No entry in SCHEMAS may exist that the fixture cannot vouch for."""
    from_fixture = {
        _schema(path)
        for path in FIXTURE.rglob("*.json")
        if _schema(path) is not None and ".pbi" not in path.parts
    }
    unbacked = set(tmdl.SCHEMAS.values()) - from_fixture
    assert not unbacked, unbacked


def test_metadata_versions_match_desktops(built) -> None:
    """The values around the schemas were wrong too, and by the same mechanism."""
    for relative, key in (
        ("northlake.Report/definition.pbir", "version"),
        ("northlake.SemanticModel/definition.pbism", "version"),
        ("northlake.Report/definition/version.json", "version"),
        ("northlake.pbip", "version"),
    ):
        expected = json.loads((FIXTURE / relative).read_text(encoding="utf-8-sig"))[key]
        actual = json.loads((built / relative).read_text(encoding="utf-8-sig"))[key]
        assert actual == expected, f"{relative}[{key}]: {actual} != {expected}"


def test_the_database_matches_desktops(built) -> None:
    """Unnamed, and compatibility level 1606 — the generator said `database northlake` / 1567."""
    expected = (FIXTURE / "northlake.SemanticModel/definition/database.tmdl").read_text(
        encoding="utf-8"
    )
    actual = (built / "northlake.SemanticModel/definition/database.tmdl").read_text(
        encoding="utf-8"
    )
    assert actual.strip() == expected.strip()


# --- countermeasure 3: the validator must accept known-good input ---------------------------


@pytest.mark.parametrize(
    "relative",
    sorted(p.relative_to(FIXTURE).as_posix() for p in FIXTURE.rglob("*.tmdl")),
)
def test_the_validator_accepts_desktops_own_tmdl(relative) -> None:
    """A checker that rejects the real thing is a checker that will be relaxed until it is mute.

    This found three genuine gaps the moment the fixture arrived: a root object may be declared
    with no name (`database`), `dataAccessOptions` is a nested object rather than a property, and
    Desktop writes model annotations at depth 0 after the model block.
    """
    text = (FIXTURE / relative).read_text(encoding="utf-8")
    assert not validate.validate_text(text, relative)
