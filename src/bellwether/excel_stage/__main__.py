"""Windows-only Excel stage entry point: ``python -m bellwether.excel_stage``.

Opens the workbook the headless build already produced, recalculates it, adds what xlsxwriter
cannot create, verifies every figure against the oracle, and exports the distribution artifacts.

Additive only. If this stage ever originates a financial value, that is a defect regardless of
whether the value is correct.

Deleting this package must leave a complete, correct model — criterion 5.6. That is why nothing
outside it imports it, and why ``pywin32`` is an optional extra rather than a dependency.
"""

from __future__ import annotations

import logging
import sys

from bellwether import __version__
from bellwether.paths import BUILD_DIR

log = logging.getLogger("bellwether.excel_stage")

WORKBOOK = "northlake-model.xlsx"


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    log.info("bellwether %s - Excel stage (Windows only)", __version__)

    from bellwether.data import generate
    from bellwether.excel_stage import com, data_tables, reconcile
    from bellwether.workbook import model

    if not com.available():
        log.error("Excel is not available on this machine. This stage is Windows-only.")
        return 2

    path = BUILD_DIR / WORKBOOK
    if not path.exists():
        log.error("%s not found - run `python -m bellwether.build` first", path)
        return 2
    log.info("workbook: %s", path)

    # The sensitivity ranges come from the builder rather than being rediscovered here: the
    # layout is the workbook's business, and a second description of it would be a second
    # source of truth for where the numbers live.
    summary = model.build(generate.generate(), path)
    ranges = summary["sensitivity_ranges"]

    clean, message = com.opened_without_repair(path)
    log.info("  [%s] opens without repair warnings", "x" if clean else " ")
    if not clean:
        log.error("      %s", message)
        return 1

    report = reconcile.reconcile(path)
    differences = len(report["differences"])
    log.info("  [%s] recalculation reconciles to the oracle", "x" if not differences else " ")
    for line in reconcile.format_report(report).splitlines():
        log.info("      %s", line)
    if differences:
        return 1

    tables = data_tables.apply(path, ranges)
    log.info(
        "  [%s] native Data Tables over the sensitivity grids",
        "x" if tables["all_are_tables"] else " ",
    )
    for entry in tables["attached"]:
        log.info("      %s", entry)
    log.info(
        "      %d grid cells compared, %d differences",
        tables["compared"],
        len(tables["differences"]),
    )
    if tables["differences"] or not tables["all_are_tables"]:
        for difference in tables["differences"][:10]:
            log.error("      %s", difference)
        return 1

    for step, phase in (
        ("export the board pack PDF", "phase 6"),
        ("export named ranges as PNGs", "phase 7"),
    ):
        log.info("  [ ] %s - not yet implemented (%s)", step, phase)

    log.info("Excel agrees with the oracle. Nothing in this stage originated a value.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
