"""Channel allocation — contract §6.7, ADR 0010, phase 3 D-b.

The mapping is **data, not branching logic**. Power BI needs the same mapping to compute channel
contribution, and expressing it as conditionals here would guarantee the two drift — the failure
ADR 0007 exists to prevent.

It also forces §6.7 to say what it previously only implied: which departments are directly
attributable to a channel, and which are corporate. That vagueness was harmless in a document
and would not have survived a board pack.
"""

from __future__ import annotations

import pandas as pd

CORPORATE = "Unallocated corporate"

#: (account prefix, department, channel). The first matching row wins, so a department rule can
#: be overridden by a more specific account rule above it.
ALLOCATION_RULES: list[tuple[str, str, str]] = [
    # Directly attributable to DTC — costs that disappear if the channel does.
    ("4000", "*", "DTC"),
    ("4020", "*", "DTC"),
    ("4100", "*", "DTC"),
    ("4110", "*", "DTC"),
    ("4111", "*", "DTC"),
    ("5100", "*", "DTC"),
    ("5200", "*", "DTC"),
    ("6200", "*", "DTC"),
    ("*", "Marketing / Ecommerce", "DTC"),
    ("*", "Customer Experience", "DTC"),
    # Directly attributable to wholesale.
    ("4010", "*", "Wholesale"),
    ("4120", "*", "Wholesale"),
    ("4121", "*", "Wholesale"),
    ("4130", "*", "Wholesale"),
    ("4140", "*", "Wholesale"),
    ("4150", "*", "Wholesale"),
    ("5110", "*", "Wholesale"),
    ("5210", "*", "Wholesale"),
    ("6400", "*", "Wholesale"),
    ("*", "Wholesale Sales", "Wholesale"),
    # Cost of goods that both channels consume, split by the units each shipped.
    ("5000", "*", "BY_UNITS"),
    ("5010", "*", "BY_UNITS"),
    ("5020", "*", "BY_UNITS"),
    ("5220", "*", "BY_UNITS"),
    ("5300", "*", "BY_UNITS"),
    ("5310", "*", "BY_UNITS"),
    ("5320", "*", "BY_UNITS"),
    # Everything else is corporate and stays unallocated — see the note below.
    ("*", "*", CORPORATE),
]


def build_mapping(accounts: pd.DataFrame, departments: pd.DataFrame) -> pd.DataFrame:
    """Resolve the rules into one row per (account, department) — the table Power BI consumes."""
    rows = []
    for account in accounts.itertuples():
        for department in departments.itertuples():
            channel = CORPORATE
            for rule_account, rule_department, rule_channel in ALLOCATION_RULES:
                account_ok = rule_account in ("*", account.account_code)
                department_ok = rule_department in ("*", department.department_name)
                if account_ok and department_ok:
                    channel = rule_channel
                    break
            rows.append(
                {
                    "account_code": account.account_code,
                    "account_name": account.account_name,
                    "department_name": department.department_name,
                    "channel_allocation": channel,
                    "is_directly_attributable": channel in ("DTC", "Wholesale"),
                    "is_split_by_units": channel == "BY_UNITS",
                }
            )
    return pd.DataFrame(rows)


#: Candidate drivers for splitting Supply Chain / Operations, if it were allocated. Each is
#: defensible on its own terms, which is exactly the problem — see ``supply_chain_sensitivity``.
SUPPLY_CHAIN_DRIVERS = {
    "Units shipped": "wholesale ships more units than DTC on less revenue",
    "Net revenue": "the default, and the one that flatters whichever channel is larger",
    "Order and invoice lines": "DTC generates far more transactions per dollar",
    "Purchase order lines": "purchasing serves the catalogue, not the channel that sells it",
    "Inventory value held": "wholesale commits stock further ahead",
}


def supply_chain_sensitivity(
    units_by_channel: dict[str, float],
    revenue_by_channel: dict[str, float],
    lines_by_channel: dict[str, float],
    supply_chain_cost: float,
) -> pd.DataFrame:
    """How much Supply Chain cost each candidate driver would push to each channel.

    ADR 0010 leaves Supply Chain / Operations unallocated. This is the evidence for that
    decision rather than an assertion of it: every driver below is defensible, and they disagree
    by enough that choosing one manufactures precision the business does not have.
    """
    bases = {
        "Units shipped": units_by_channel,
        "Net revenue": revenue_by_channel,
        "Order and invoice lines": lines_by_channel,
    }
    rows = []
    for driver, base in bases.items():
        total = sum(base.values())
        for channel, value in base.items():
            share = value / total if total else 0.0
            rows.append(
                {
                    "driver": driver,
                    "channel_name": channel,
                    "share": share,
                    "allocated_cost": supply_chain_cost * share,
                    "rationale": SUPPLY_CHAIN_DRIVERS[driver],
                }
            )
    frame = pd.DataFrame(rows)
    spread = frame.groupby("channel_name")["allocated_cost"].agg(["min", "max"])
    frame["range_for_channel"] = frame["channel_name"].map(spread["max"] - spread["min"])
    return frame
