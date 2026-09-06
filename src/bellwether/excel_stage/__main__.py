"""Windows-only Excel stage entry point: ``python -m bellwether.excel_stage``.

Opens the workbook the headless build already produced, recalculates it, adds what
xlsxwriter cannot create, verifies every figure against the oracle, and exports the
distribution artifacts.

Additive only. If this stage ever originates a financial value, that is a defect regardless
of whether the value is correct.

Phase 0: the stage is declared but empty.
"""

from __future__ import annotations

import logging
import sys

from bellwether import __version__
from bellwether.paths import BUILD_DIR

log = logging.getLogger("bellwether.excel_stage")

#: What this stage will add, in order, with the phase that implements each.
STEPS: tuple[tuple[str, str], ...] = (
    ("recalculate with CalculateFullRebuild", "phase 3"),
    ("add native data tables and pivots", "phase 3"),
    ("reconcile workbook values against the oracle", "phase 3"),
    ("export the board pack PDF", "phase 5"),
    ("export named ranges as PNGs", "phase 6"),
)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    log.info("bellwether %s - Excel stage (Windows only)", __version__)
    log.info("build: %s", BUILD_DIR)

    for step, phase in STEPS:
        log.info("  [ ] %s - not yet implemented (%s)", step, phase)

    log.info("nothing to package yet; scaffold is in place")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
