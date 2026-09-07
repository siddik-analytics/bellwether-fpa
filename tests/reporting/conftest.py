"""Shared build for the reporting tests.

Generating and starring the model takes long enough that doing it per module is felt, and every
test here reads the same world.
"""

from __future__ import annotations

import pandas as pd
import pytest

from bellwether.data import generate
from bellwether.transform import star


@pytest.fixture(scope="session")
def star_tables() -> dict[str, pd.DataFrame]:
    """The generated tables, with the star's ledger in place of the raw one.

    `pack` reads both: the transaction facts for the allocation exhibit, and the starred ledger
    for anything that needs `channel_allocation`. Handing back one dictionary keeps the tests
    from having to remember which is which.
    """
    tables = generate.generate()
    schema = star.build_star(tables)
    return {**tables, "fact_gl": schema["fact_gl"]}
