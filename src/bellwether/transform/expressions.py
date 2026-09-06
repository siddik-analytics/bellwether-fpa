"""One expression language, three backends — phase 5 F-b, ADR 0019.

A metric's derivation is written once, as an expression over other metric names:

    "[Gross Revenue] - [Contra Revenue]"

and this module turns that single string into a Python value, an Excel formula, or a DAX
measure. Before this existed the gross-to-net ladder was written out three times in Python —
once in ``semantic.evaluate_ladder``, once in ``statements.metric_series``, once in the
workbook's derivation table — and generated DAX would have been a fourth. They agreed because
nobody had edited one copy.

The syntax is deliberately DAX's own: ``[Measure Name]`` is how DAX references a measure, and
``DIVIDE(a, b)`` is how it divides safely. That makes the DAX backend nearly a pass-through and
keeps the translation surface small enough to read, which is what the phase 5 verification
approach depends on — see ``docs/phases/phase-05-spec.md``.

Evaluation goes through ``ast`` with an allow-list of node types rather than ``eval``. A
derivation is data read from a definition table; it should not be able to express anything but
arithmetic.
"""

from __future__ import annotations

import ast
import re

import numpy as np

#: ``[Metric Name]`` — a reference to another metric, in DAX's own syntax.
REFERENCE = re.compile(r"\[([^\]]+)\]")

#: Divide-by-zero returns this rather than an error, matching DAX's ``DIVIDE`` third argument
#: and the ``IF(denominator=0, 0, ...)`` guard the workbook has always used.
DIVIDE_FALLBACK = 0.0

_ALLOWED_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.USub,
    ast.UAdd,
    ast.Constant,
    ast.Name,
    ast.Load,
    ast.Call,
)


class DerivationError(ValueError):
    """A derivation that is not a plain arithmetic expression over metric names."""


def dependencies(derivation: str) -> tuple[str, ...]:
    """The metric names a derivation references, in order of first appearance."""
    seen: list[str] = []
    for name in REFERENCE.findall(derivation):
        if name not in seen:
            seen.append(name)
    return tuple(seen)


def _placeholder(index: int) -> str:
    return f"_m{index}"


def _to_ast(derivation: str, names: tuple[str, ...]) -> ast.Expression:
    """Parse the derivation with metric references replaced by safe identifiers."""
    slots = {name: _placeholder(i) for i, name in enumerate(names)}
    source = REFERENCE.sub(lambda m: slots[m.group(1)], derivation)
    try:
        tree = ast.parse(source, mode="eval")
    except SyntaxError as exc:  # pragma: no cover - defensive
        raise DerivationError(f"cannot parse derivation {derivation!r}") from exc

    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise DerivationError(
                f"derivation {derivation!r} contains {type(node).__name__}, which is not "
                "arithmetic over metric names"
            )
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id != "DIVIDE":
                raise DerivationError(
                    f"derivation {derivation!r} calls something other than DIVIDE"
                )
            if len(node.args) not in (2, 3):
                raise DerivationError(f"DIVIDE takes two or three arguments in {derivation!r}")
    return tree


def evaluate(derivation: str, values: dict):
    """Evaluate against already-computed metric values.

    ``values`` maps metric name to a float or to a pandas Series; the same expression serves
    both, which is why the scalar ladder and the monthly series can share one definition.
    """
    names = dependencies(derivation)
    missing = [name for name in names if name not in values]
    if missing:
        raise DerivationError(f"derivation {derivation!r} references undefined {missing}")
    tree = _to_ast(derivation, names)
    scope = {_placeholder(i): values[name] for i, name in enumerate(names)}
    scope["DIVIDE"] = _divide
    # The tree was validated against an allow-list above; nothing but arithmetic survives.
    return eval(compile(tree, filename="<derivation>", mode="eval"), {"__builtins__": {}}, scope)


def _divide(numerator, denominator, fallback=DIVIDE_FALLBACK):
    """DAX's DIVIDE: a zero denominator yields the fallback rather than an error.

    Dispatch is on whether the denominator is a Series, tested rather than caught: a scalar
    division by zero raises before any exception handler could tell the two cases apart.
    """
    if hasattr(denominator, "where"):
        with np.errstate(divide="ignore", invalid="ignore"):
            quotient = numerator / denominator.replace(0, np.nan)
        return quotient.fillna(fallback)
    return numerator / denominator if denominator else fallback


def to_dax(derivation: str) -> str:
    """The DAX form. Almost a pass-through, which is the point of choosing this syntax."""
    _to_ast(derivation, dependencies(derivation))
    return derivation


def to_excel(derivation: str, cells: dict[str, str]) -> str:
    """The Excel form, with each metric reference replaced by the cell holding it.

    ``DIVIDE`` becomes the ``IF(denominator=0, 0, ...)`` guard rather than ``IFERROR``: a zero
    denominator is an expected state in a month with no revenue, and an error suppressor would
    hide the ones that are not expected.
    """
    _to_ast(derivation, dependencies(derivation))
    resolved = REFERENCE.sub(lambda m: cells[m.group(1)], derivation)
    while True:
        match = re.search(r"DIVIDE\(", resolved)
        if not match:
            return resolved.replace(" ", "")
        start = match.end()
        depth, index = 1, start
        while depth:
            if resolved[index] == "(":
                depth += 1
            elif resolved[index] == ")":
                depth -= 1
            index += 1
        args = _split_arguments(resolved[start : index - 1])
        numerator, denominator = args[0], args[1]
        fallback = args[2] if len(args) == 3 else "0"
        guard = f"IF({denominator}=0,{fallback},{numerator}/{denominator})"
        resolved = resolved[: match.start()] + guard + resolved[index:]


def _split_arguments(text: str) -> list[str]:
    args, depth, current = [], 0, ""
    for character in text:
        if character == "," and depth == 0:
            args.append(current.strip())
            current = ""
            continue
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
        current += character
    args.append(current.strip())
    return args


def resolution_order(derivations: dict[str, str]) -> list[str]:
    """Derived metrics in dependency order, so each is computed after what it reads.

    Raises on a cycle. A metric ladder with a cycle is not a ladder, and the failure should name
    the metrics involved rather than surface later as a missing key.
    """
    ordered: list[str] = []
    state: dict[str, int] = {}

    def visit(name: str, path: tuple[str, ...]) -> None:
        if state.get(name) == 2:
            return
        if state.get(name) == 1:
            raise DerivationError(f"circular derivation: {' -> '.join([*path, name])}")
        if name not in derivations:
            return
        state[name] = 1
        for dependency in dependencies(derivations[name]):
            visit(dependency, (*path, name))
        state[name] = 2
        ordered.append(name)

    for name in derivations:
        visit(name, ())
    return ordered
