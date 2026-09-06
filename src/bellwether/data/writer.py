"""Output: Parquet for the pipeline, CSV samples for the browsing reviewer — spec D-2.

Parquet preserves dtypes, which matters because the contract stores money as integer minor
units and dates as dates. It is also opaque on GitHub, and half this project's audience reads
the repository rather than running it — so every table also lands as a bounded CSV sample.
"""

from __future__ import annotations

import pathlib

import pandas as pd

from bellwether.data import config as C

MONEY_SUFFIXES = (
    "_value",
    "_amount",
    "_revenue",
    "_cost",
    "_discount",
    "_allowance",
    "_deduction",
    "_expense",
    "_fee",
    "_advance",
    "_base",
    "_drawn",
    "_availability",
    "_gap",
    "_flow",
    "_profit",
    "_capital",
    "_reserve",
    "_liability",
)


def to_minor_units(df: pd.DataFrame, *, is_fact: bool) -> pd.DataFrame:
    """Money as integer cents (§2.1). Floats accumulate error the ledger cannot afford.

    Fact tables only, as the contract says. The suffix list cannot tell a rate from an amount -
    ``msrp_discount`` is a fraction on the wholesale account dimension and a dollar figure on an
    order line - and applying it everywhere turned a 0.49 discount rate into 49 and left
    ``fully_loaded_cost`` in cents beside an ``annual_salary`` in dollars on the same row.
    Restricting it to facts resolves both, because §2.1 also requires rates to stay decimals and
    every genuine rate lives on a dimension.
    """
    out = df.copy()
    if not is_fact:
        return out
    for column in out.columns:
        if out[column].dtype.kind == "f" and column.endswith(MONEY_SUFFIXES):
            out[column] = (out[column] * 100).round().astype("int64")
    return out


#: Floats are rounded before they reach a CSV sample. The samples are committed, the build
#: regenerates them, and CI asserts the working tree is clean afterwards — so a difference of
#: one bit in a float repr between the Windows machine that committed them and the Linux runner
#: that regenerates them would fail the build for no real reason.
SAMPLE_FLOAT_PRECISION = 6


def write(
    tables: dict[str, pd.DataFrame],
    data_dir: pathlib.Path,
    sample_dir: pathlib.Path,
    sample_rows: int = C.SAMPLE_ROWS,
) -> dict[str, int]:
    """Write every table to Parquet, plus a committed CSV sample of each.

    Parquet goes to ``data/`` and is gitignored; samples go to ``samples/`` at the repo root and
    are committed. Returns row counts.
    """
    parquet_dir = data_dir / "parquet"
    parquet_dir.mkdir(parents=True, exist_ok=True)
    sample_dir.mkdir(parents=True, exist_ok=True)

    counts: dict[str, int] = {}
    for name in sorted(tables):
        frame = to_minor_units(tables[name], is_fact=name.startswith("fact_"))
        frame.to_parquet(parquet_dir / f"{name}.parquet", index=False)
        # Head rather than a random sample: a reviewer opening the CSV wants the first rows of
        # a recognisable table, not a scatter that hides the ordering.
        sample = frame.head(sample_rows).round(SAMPLE_FLOAT_PRECISION)
        sample.to_csv(sample_dir / f"{name}.csv", index=False, lineterminator=chr(10))
        counts[name] = len(frame)
    return counts
