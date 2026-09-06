"""Headless build entry point: ``python -m bellwether.build``.

This must produce a complete, correct workbook on Linux with no Excel installed. Every
financial value originates here, in pure Python. The Excel stage that follows only ever adds
presentation and packaging on top of what this command produced.

Phase 0: the pipeline is declared but empty. Each stage lands in the phase named beside it.
"""

from __future__ import annotations

import logging
import sys

from bellwether import __version__
from bellwether.paths import BUILD_DIR, DATA_DIR, ensure_output_dirs

log = logging.getLogger("bellwether.build")

#: Build stages in dependency order, with the phase that implements each.
STAGES: tuple[tuple[str, str], ...] = (
    ("recalculate and package with Excel", "phase 5"),
    ("board pack and variance commentary", "phase 5"),
)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    log.info("bellwether %s - headless build", __version__)

    ensure_output_dirs()
    log.info("data:  %s", DATA_DIR)
    log.info("build: %s", BUILD_DIR)

    from bellwether.data import generate

    log.info("  [x] generate synthetic source data")
    counts = generate.run(DATA_DIR)
    tables = generate.generate()
    log.info("      %s rows across %d tables", f"{sum(counts.values()):,}", len(counts))

    log.info("  [x] build star schema and semantic layer")

    from bellwether.workbook import model

    workbook_path = BUILD_DIR / "northlake-model.xlsx"
    summary = model.build(tables, workbook_path)
    log.info("  [x] write the workbook")
    log.info(
        "      %s, %d sheets, %d months", workbook_path.name, summary["sheets"], summary["months"]
    )

    for stage, phase in STAGES:
        log.info("  [ ] %s - not yet implemented (%s)", stage, phase)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
