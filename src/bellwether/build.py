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
from bellwether.paths import BUILD_DIR, DATA_DIR, POWERBI_DIR, ensure_output_dirs

log = logging.getLogger("bellwether.build")

#: Build stages in dependency order, with the phase that implements each.
STAGES: tuple[tuple[str, str], ...] = (
    ("board pack and variance commentary", "phase 6"),
    ("case study, video and distribution assets", "phase 7"),
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

    from bellwether.data import writer
    from bellwether.transform import star as star_mod

    star = star_mod.build_star(tables)
    star_counts = writer.write_star(star, DATA_DIR)
    log.info("  [x] build star schema and semantic layer")
    log.info(
        "      %s rows across %d star tables, in dollars",
        f"{sum(star_counts.values()):,}",
        len(star_counts),
    )

    from bellwether.powerbi import tmdl, validate
    from bellwether.workbook import model

    workbook_path = BUILD_DIR / "northlake-model.xlsx"
    summary = model.build(tables, workbook_path)
    log.info("  [x] write the workbook")
    log.info(
        "      %s, %d sheets, %d months", workbook_path.name, summary["sheets"], summary["months"]
    )

    pbip = tmdl.build(star, POWERBI_DIR)

    # A structural check, not a semantic one. It cannot prove the DAX evaluates; it proves the
    # file is TMDL rather than text that looks like TMDL, which is the class of defect that sent
    # the first generated project back from Power BI Desktop unopened.
    problems = validate.validate_project(
        POWERBI_DIR / f"{tmdl.PROJECT}.SemanticModel" / "definition"
    )
    if problems:
        log.error("  [ ] generate the Power BI project - %d structural errors", len(problems))
        for problem in problems:
            log.error("      %s", problem)
        return 1
    log.info("  [x] generate the Power BI project (PBIP text, structurally validated)")
    log.info(
        "      %d tables, %d measures, %d relationships, %d pages",
        len(pbip["tables"]),
        pbip["measures"],
        pbip["relationships"],
        pbip["pages"],
    )

    for stage, phase in STAGES:
        log.info("  [ ] %s - not yet implemented (%s)", stage, phase)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
