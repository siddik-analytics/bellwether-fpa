"""Structural validation of generated TMDL — criterion 5.31.

Phase 5's spec said the CI guarantee is that measures are *generated*, not that the model is
correct, and named that as the limitation. The first attempt to open the project in Power BI
Desktop demonstrated it precisely: the byte-identical regeneration test passed on a file Desktop
refused to parse, because `dataCategory` was emitted **after** a table's columns rather than
before them.

That failure needed no DAX engine to find. It is a grammar error, and a grammar can be checked
headless. This module does that: it parses the emitted TMDL and asserts the indentation and
object nesting are well-formed, so the class of defect that cost a round trip to Desktop is
caught by `pytest` instead.

It does not prove the model is semantically valid, and nothing here should be read as claiming
that. It proves the file is TMDL rather than text that looks like TMDL.

**The indentation contract**, as the parser enforces it:

- Indentation is **tabs only**. A leading space is an error, not a style preference.
- Depth increases by at most one level at a time.
- An object declaration (``table X``, ``column 'Y'``) opens a block; its properties sit one
  level deeper.
- **Within any object, every property must precede every child object.** This is the rule that
  was broken: once ``column`` blocks have started, a table-level property can no longer appear.
"""

from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass, field

#: Object declarations, by the depth they are legal at within their parent.
ROOT_OBJECTS = {"model", "table", "database", "relationship", "expression", "ref", "cultureInfo"}
TABLE_CHILDREN = {"column", "measure", "partition", "hierarchy", "calculationGroup"}
COLUMN_CHILDREN: set[str] = set()

#: Properties each object accepts. Deliberately a closed set: a typo in a property name is
#: otherwise accepted by the file and rejected by Desktop, which is the whole failure mode.
TABLE_PROPERTIES = {
    "dataCategory",
    "description",
    "isHidden",
    "isPrivate",
    "lineageTag",
    "showAsVariationsOnly",
    "sourceLineageTag",
}
COLUMN_PROPERTIES = {
    "dataCategory",
    "dataType",
    "description",
    "displayFolder",
    "formatString",
    "isDataTypeInferred",
    "isHidden",
    "isKey",
    "isNameInferred",
    "isUnique",
    "lineageTag",
    "sortByColumn",
    "sourceColumn",
    "sourceLineageTag",
    "summarizeBy",
}
MEASURE_PROPERTIES = {
    "description",
    "displayFolder",
    "formatString",
    "isHidden",
    "lineageTag",
    "sourceLineageTag",
}
PARTITION_PROPERTIES = {"mode", "source", "description", "queryGroup"}

#: Properties written with ``=`` rather than ``:`` because their value is an expression.
#: ``source = let ... in ...`` on a partition, and ``annotation X = value`` anywhere.
EXPRESSION_PROPERTIES = {"source"}
MODEL_PROPERTIES = {
    "culture",
    "defaultPowerBIDataSourceVersion",
    "discourageImplicitMeasures",
    "sourceQueryCulture",
    "description",
    "valueFilterBehavior",
}

#: A nested object under model, whose own properties are bare flags. Taken from Desktop's
#: output, not from a guess — the validator rejected the real file until this was added.
DATA_ACCESS_PROPERTIES = {"legacyRedirects", "returnErrorValuesAsNull", "fastCombine"}
RELATIONSHIP_PROPERTIES = {
    "fromColumn",
    "toColumn",
    "fromCardinality",
    "toCardinality",
    "crossFilteringBehavior",
    "isActive",
    "joinOnDateBehavior",
    "relyOnReferentialIntegrity",
    "securityFilteringBehavior",
}
DATABASE_PROPERTIES = {"compatibilityLevel"}
EXPRESSION_OBJECT_PROPERTIES = {"lineageTag", "description", "queryGroup", "kind"}

PROPERTIES_FOR = {
    "table": TABLE_PROPERTIES,
    "column": COLUMN_PROPERTIES,
    "measure": MEASURE_PROPERTIES,
    "partition": PARTITION_PROPERTIES,
    "model": MODEL_PROPERTIES,
    "relationship": RELATIONSHIP_PROPERTIES,
    "database": DATABASE_PROPERTIES,
    "expression": EXPRESSION_OBJECT_PROPERTIES,
    "dataAccessOptions": DATA_ACCESS_PROPERTIES,
    "cultureInfo": set(),
}

CHILDREN_FOR = {
    "table": TABLE_CHILDREN,
    "column": COLUMN_CHILDREN,
    "measure": set(),
    "partition": set(),
    "model": {"dataAccessOptions"},
    "relationship": set(),
    "database": set(),
    "expression": set(),
    "dataAccessOptions": set(),
    "cultureInfo": set(),
}

_PROPERTY = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(:|=|$)")
_DECLARATION = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s+(.+)$")


@dataclass
class Line:
    number: int
    depth: int
    text: str


@dataclass
class Node:
    """One object in the tree, with where its properties stopped and its children began."""

    kind: str
    name: str
    line: int
    depth: int
    children: list[Node] = field(default_factory=list)
    properties: list[tuple[int, str]] = field(default_factory=list)
    first_child_line: int | None = None


def _scan(text: str) -> tuple[list[Line], list[str]]:
    errors: list[str] = []
    lines: list[Line] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip():
            continue
        stripped = raw.lstrip("\t")
        indent = len(raw) - len(stripped)
        if stripped.startswith(" "):
            errors.append(f"line {number}: indented with spaces; TMDL uses tabs only")
            continue
        if "\t" in stripped and not stripped.startswith("///"):
            # A tab inside the content is legal in an M expression, so only the leading run is
            # measured. Nothing to do; recorded here so the intent is not mistaken for an omission.
            pass
        lines.append(Line(number=number, depth=indent, text=stripped))
    return lines, errors


def validate_text(text: str, source: str = "<tmdl>") -> list[str]:
    """Every structural problem in one file, as readable messages."""
    lines, errors = _scan(text)
    stack: list[Node] = []
    previous_depth = -1

    for line in lines:
        if line.depth > previous_depth + 1:
            errors.append(
                f"{source} line {line.number}: indentation jumps from depth "
                f"{previous_depth} to {line.depth}"
            )
        while stack and stack[-1].depth >= line.depth:
            stack.pop()
        parent = stack[-1] if stack else None

        if line.text.startswith("///"):
            previous_depth = line.depth
            continue

        declaration = _DECLARATION.match(line.text)
        property_match = _PROPERTY.match(line.text)
        keyword = (
            (declaration or property_match).group(1) if (declaration or property_match) else ""
        )
        # Three property spellings, all legal: ``name: value``, a bare boolean flag, and
        # ``name = <expression>`` for a partition source or an annotation. Treating the third as
        # an object declaration is what made the validator's own first run mostly noise.
        # An object may be declared with no name at all. Desktop writes "database" bare at the
        # root and "dataAccessOptions" bare inside the model, each with its properties nested
        # underneath. Without this the validator reads them as properties outside any object and
        # rejects Desktop's own file — which is how these rules were found in the first place.
        legal_here = ROOT_OBJECTS if parent is None else CHILDREN_FOR.get(parent.kind, set())
        bare_object = not declaration and keyword in legal_here
        is_property = not bare_object and (keyword == "annotation" or bool(property_match))

        if is_property:
            if parent is None and keyword == "annotation":
                # Desktop writes model annotations at depth 0, after the model block. They
                # belong to the file's root object rather than to nothing.
                previous_depth = line.depth
                continue
            if parent is None:
                errors.append(f"{source} line {line.number}: property outside any object")
            else:
                allowed = PROPERTIES_FOR.get(parent.kind, set())
                if keyword != "annotation" and keyword not in allowed:
                    errors.append(
                        f"{source} line {line.number}: '{keyword}' is not a property of "
                        f"{parent.kind}"
                    )
                if parent.first_child_line is not None:
                    errors.append(
                        f"{source} line {line.number}: table-level property '{keyword}' appears "
                        f"after a child object opened at line {parent.first_child_line}; every "
                        f"property of a {parent.kind} must precede its children"
                    )
                parent.properties.append((line.number, keyword))
            previous_depth = line.depth
            continue

        if not declaration and not property_match:
            errors.append(f"{source} line {line.number}: cannot parse {line.text!r}")
            previous_depth = line.depth
            continue

        kind = keyword
        name = declaration.group(2) if declaration else ""
        node = Node(kind=kind, name=name, line=line.number, depth=line.depth)

        if parent is None:
            if kind not in ROOT_OBJECTS:
                errors.append(f"{source} line {line.number}: '{kind}' is not a root object")
        else:
            allowed_children = CHILDREN_FOR.get(parent.kind, set())
            if kind not in allowed_children:
                errors.append(
                    f"{source} line {line.number}: '{kind}' is not a child of {parent.kind}"
                )
            if parent.first_child_line is None:
                parent.first_child_line = line.number
            parent.children.append(node)

        # A name containing a **space** must be quoted in a declaration. Narrow on purpose:
        # hyphens are fine (every relationship name has them and Microsoft's parser accepts
        # them), so a broader rule would fire on valid files and get relaxed until it was mute.
        # The trigger was `partition Key Figures = m`, which parses as a name plus a stray token.
        if kind in {"table", "column", "measure", "partition"} and name:
            bare = name.split(" = ")[0].strip()
            if " " in bare and not (bare.startswith("'") and bare.endswith("'")):
                errors.append(
                    f"{source} line {line.number}: the name {bare!r} contains a space and must "
                    "be quoted in a TMDL declaration"
                )

        stack.append(node)
        previous_depth = line.depth

    return errors


def _bare_properties(parent: Node | None) -> set[str]:
    """Boolean properties written without a value — ``isHidden`` rather than ``isHidden: true``."""
    if parent is None:
        return set()
    return {
        p
        for p in PROPERTIES_FOR.get(parent.kind, set())
        if p.startswith("is") or p in {"discourageImplicitMeasures", "showAsVariationsOnly"}
    }


def validate_table(text: str, source: str) -> list[str]:
    """Semantic checks a table file must satisfy beyond parsing.

    A table with a partition but no columns parses cleanly and is rejected on load — which is
    what the Measures table did, because a measures-only table still needs a column to exist.
    """
    errors: list[str] = []
    if not re.search(r"^table ", text, re.M):
        return [f"{source}: no table declaration"]
    columns = len(re.findall(r"^\tcolumn ", text, re.M))
    partitions = len(re.findall(r"^\tpartition ", text, re.M))
    if columns == 0:
        errors.append(f"{source}: a table needs at least one column, even a hidden placeholder")
    if partitions != 1:
        errors.append(f"{source}: expected exactly one partition, found {partitions}")
    if "dataCategory: Time" in text:
        if not re.search(r"^\tdataCategory: Time", text, re.M):
            errors.append(f"{source}: dataCategory must be a table property at depth 1")
        if "dataType: dateTime" not in text:
            errors.append(f"{source}: a Time table needs a dateTime column")
    return errors


def validate_project(model_dir: pathlib.Path) -> list[str]:
    """Validate every TMDL file under a semantic model definition directory."""
    errors: list[str] = []
    files = sorted(model_dir.rglob("*.tmdl"))
    if not files:
        return [f"{model_dir}: no TMDL files"]
    for path in files:
        source = path.relative_to(model_dir).as_posix()
        text = path.read_text(encoding="utf-8")
        errors.extend(validate_text(text, source))
        if path.parent.name == "tables":
            errors.extend(validate_table(text, source))
    return errors
