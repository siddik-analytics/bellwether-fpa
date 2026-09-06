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


def to_minor_units(df: pd.DataFrame) -> pd.DataFrame:
    """Money as integer cents (§2.1). Floats accumulate error the ledger cannot afford."""
    out = df.copy()
    for column in out.columns:
        if out[column].dtype.kind == "f" and column.endswith(MONEY_SUFFIXES):
            out[column] = (out[column] * 100).round().astype("int64")
    return out


def write(
    tables: dict[str, pd.DataFrame], data_dir: pathlib.Path, sample_rows: int = C.SAMPLE_ROWS
) -> dict[str, int]:
    """Write every table to Parquet, plus a CSV sample of each. Returns row counts."""
    parquet_dir = data_dir / "parquet"
    sample_dir = data_dir / "samples"
    parquet_dir.mkdir(parents=True, exist_ok=True)
    sample_dir.mkdir(parents=True, exist_ok=True)

    counts: dict[str, int] = {}
    for name in sorted(tables):
        frame = to_minor_units(tables[name])
        frame.to_parquet(parquet_dir / f"{name}.parquet", index=False)
        # Head rather than a random sample: a reviewer opening the CSV wants the first rows of
        # a recognisable table, not a scatter that hides the ordering.
        frame.head(sample_rows).to_csv(sample_dir / f"{name}.csv", index=False)
        counts[name] = len(frame)
    return counts
