"""Statement assembly and time-series evaluation — contract §5.8a, ADR 0018.

Two things the semantic layer did not expose, both built here rather than in the workbook
because Power BI needs the identical shapes in phase 5. Reimplementing either there would
recreate the two-sources-of-truth problem ADR 0014 just closed.

**Series, not scalars.** ``semantic.evaluate_ladder`` answers "what is EBITDA for this slice".
A workbook column is a month, so it needs the whole axis: 72 months x version x scenario, in one
pass rather than several thousand filtered aggregations.

**Statements, not accounts.** The ledger holds accounts. A balance sheet needs them classified
and ordered, and an indirect cash flow needs to know which balance movements are working capital
and which are financing.
"""

from __future__ import annotations

import pandas as pd

from bellwether.transform import semantic

# --- §5.8a balance sheet classification ---------------------------------------------------

CURRENT_ASSET = "Current asset"
NON_CURRENT_ASSET = "Non-current asset"
CONTRA_ASSET = "Contra-asset"
CURRENT_LIABILITY = "Current liability"
NON_CURRENT_LIABILITY = "Non-current liability"
EQUITY = "Equity"

CLASSIFICATION: dict[str, str] = {
    "1000": CURRENT_ASSET,
    "1100": CURRENT_ASSET,
    "1150": CURRENT_ASSET,
    "1200": CURRENT_ASSET,
    "1250": CURRENT_ASSET,
    "1300": CURRENT_ASSET,
    "1180": CONTRA_ASSET,
    "1210": CONTRA_ASSET,
    "1400": NON_CURRENT_ASSET,
    "2000": CURRENT_LIABILITY,
    "2100": CURRENT_LIABILITY,
    "2200": CURRENT_LIABILITY,
    # The refund utilisation accounts (ADR 0017) are movements against the refund liability, so
    # they classify with it. They are neither P&L nor a balance of their own, and leaving them
    # out of both put the balance sheet $1.4M out.
    "4111": CURRENT_LIABILITY,
    "4121": CURRENT_LIABILITY,
    # Committed facility: availability constrains it, not maturity — §5.8a.
    "2500": NON_CURRENT_LIABILITY,
    "3000": EQUITY,
    "3900": EQUITY,
}

#: Balance movements the indirect cash flow treats as working capital, and their sign against
#: cash. An asset increase consumes cash; a liability increase releases it.
#: Debits are positive here, so an asset increase and a liability increase have opposite signs
#: in the ledger and the *same* multiplier against cash: -1 turns a debit into a cash outflow and
#: a credit into an inflow. Writing +1 for the liabilities reverses them.
WORKING_CAPITAL: dict[str, int] = {
    "1200": -1,  # inventory
    "1100": -1,  # wholesale receivables
    "1150": -1,  # processor receivable
    "1300": -1,  # supplier advances
    "2000": -1,  # accounts payable
    "2200": -1,  # refund liability
    "4111": -1,  # refund liability utilisation, DTC
    "4121": -1,  # refund liability utilisation, wholesale
}

#: Non-cash charges added back explicitly rather than omitted, so a reader can see each was
#: considered — ADR 0018.
NON_CASH_ACCOUNTS = ("5310", "6500")

FINANCING_ACCOUNTS = {"2500": "Net revolver drawings", "3000": "Equity raised"}
INTEREST_ACCOUNTS = ("7000", "7010")
CAPEX_ACCOUNT = "1400"
OPENING_MEMO = "Opening balance sheet"


def monthly(ledger: pd.DataFrame) -> pd.DataFrame:
    """Ledger aggregated to account x department x month x version x scenario.

    Actuals post daily and the forecast monthly (§8); a statement column is a month, so this is
    where the two become one axis. Daily precision stays in the warehouse for drillthrough.
    """
    frame = ledger.copy()
    frame["month"] = pd.to_datetime(frame["date"]).dt.to_period("M").dt.to_timestamp()
    return frame.groupby(
        ["month", "account_code", "version_name", "scenario_name"], as_index=False
    )["amount"].sum()


def metric_series(ledger: pd.DataFrame, accounts: pd.DataFrame) -> pd.DataFrame:
    """Every P&L metric by month, version and scenario — W-1.

    One grouped pass rather than a filtered aggregation per cell. Returns a long frame so a
    caller can pivot it into whichever shape it needs; the workbook wants months as columns and
    Power BI wants it long.
    """
    by_month = monthly(ledger)
    types = accounts.set_index("account_code")["account_type"]
    by_month["account_type"] = by_month["account_code"].map(types)

    pivot = by_month.pivot_table(
        index=["month", "version_name", "scenario_name"],
        columns="account_type",
        values="amount",
        aggfunc="sum",
        fill_value=0.0,
    ).reset_index()
    for column in ("revenue", "contra_revenue", "cogs", "opex", "other"):
        if column not in pivot:
            pivot[column] = 0.0

    pivot["Gross Revenue"] = -pivot["revenue"]
    pivot["Contra Revenue"] = pivot["contra_revenue"]
    pivot["Net Revenue"] = pivot["Gross Revenue"] - pivot["Contra Revenue"]
    pivot["Cost of Sales"] = pivot["cogs"]
    pivot["Gross Profit"] = pivot["Net Revenue"] - pivot["Cost of Sales"]
    pivot["Operating Expense"] = pivot["opex"]
    pivot["EBITDA"] = pivot["Gross Profit"] - pivot["Operating Expense"]
    pivot["Other Income and Expense"] = pivot["other"]
    pivot["Net Income"] = pivot["EBITDA"] - pivot["Other Income and Expense"]
    for ratio, numerator in (("Gross Margin %", "Gross Profit"), ("EBITDA Margin %", "EBITDA")):
        pivot[ratio] = (pivot[numerator] / pivot["Net Revenue"]).where(
            pivot["Net Revenue"] != 0, 0.0
        )
    return pivot[
        ["month", "version_name", "scenario_name"]
        + [m for m in semantic.ALL_METRICS if m in pivot]
        + ["Net Income", "Other Income and Expense"]
    ]


def balance_sheet(ledger: pd.DataFrame) -> pd.DataFrame:
    """Closing balances by classification, month, version and scenario — §5.8a.

    Balances are cumulative movements, so the series must start from a posted opening position.
    """
    by_month = monthly(ledger)
    by_month = by_month[by_month["account_code"].isin(CLASSIFICATION)].copy()

    # A balance persists whether or not the account posted this month. Cumulating over only the
    # rows that exist drops every dormant account out of that month's total, so the grid is
    # completed first — otherwise the balance sheet is short by whatever happened to be quiet.
    # Each version and scenario spans only its own months — actuals run FY2023-25 and the
    # forecast FY2026-28 — so the grid is built per combination. Cross-joining every month to
    # every combination invents periods that do not exist and flat-lines their balances.
    accounts_present = sorted(by_month["account_code"].unique())
    span = by_month.groupby(["version_name", "scenario_name"])["month"].agg(["min", "max"])
    pieces = []
    for (version, scenario), row in span.iterrows():
        months = pd.date_range(row["min"], row["max"], freq="MS")
        piece = pd.DataFrame({"month": months}).merge(
            pd.Series(accounts_present, name="account_code"), how="cross"
        )
        piece["version_name"] = version
        piece["scenario_name"] = scenario
        pieces.append(piece)
    grid = pd.concat(pieces, ignore_index=True)
    by_month = grid.merge(
        by_month, on=["month", "account_code", "version_name", "scenario_name"], how="left"
    ).fillna({"amount": 0.0})

    by_month["classification"] = by_month["account_code"].map(CLASSIFICATION)
    by_month = by_month.sort_values("month")
    by_month["balance"] = by_month.groupby(["account_code", "version_name", "scenario_name"])[
        "amount"
    ].cumsum()
    return by_month


def retained_earnings(ledger: pd.DataFrame, accounts: pd.DataFrame) -> pd.DataFrame:
    """Cumulative net income by month, version and scenario.

    The ledger does not close P&L accounts to equity at period end, so the accumulated result has
    to be added to equity for the balance sheet to balance.
    """
    by_month = monthly(ledger)
    types = accounts.set_index("account_code")["account_type"]
    by_month["account_type"] = by_month["account_code"].map(types)
    pl = by_month[
        by_month["account_type"].isin(["revenue", "contra_revenue", "cogs", "opex", "other"])
    ]
    keys = ["month", "version_name", "scenario_name"]
    result = pl.groupby(keys, as_index=False)["amount"].sum().sort_values("month")
    result["accumulated_result"] = result.groupby(["version_name", "scenario_name"])[
        "amount"
    ].cumsum()
    return result[[*keys, "accumulated_result"]]


def balance_sheet_check(ledger: pd.DataFrame, accounts: pd.DataFrame) -> pd.DataFrame:
    """Assets less contra-assets, against liabilities plus equity — check 6a."""
    keys = ["month", "version_name", "scenario_name"]
    balances = balance_sheet(ledger)
    pivot = balances.pivot_table(
        index=["month", "version_name", "scenario_name"],
        columns="classification",
        values="balance",
        aggfunc="sum",
        fill_value=0.0,
    ).reset_index()
    for column in (
        CURRENT_ASSET,
        NON_CURRENT_ASSET,
        CONTRA_ASSET,
        CURRENT_LIABILITY,
        NON_CURRENT_LIABILITY,
        EQUITY,
    ):
        if column not in pivot:
            pivot[column] = 0.0
    pivot["total_assets"] = pivot[CURRENT_ASSET] + pivot[NON_CURRENT_ASSET] + pivot[CONTRA_ASSET]
    # Retained earnings has to absorb the accumulated P&L result. The ledger never closes revenue
    # and expense accounts to equity, so without this the identity is short by exactly cumulative
    # net income and the balance sheet cannot balance by construction.
    pivot = pivot.merge(retained_earnings(ledger, accounts), on=keys, how="left").fillna(0.0)
    pivot[EQUITY] = pivot[EQUITY] + pivot["accumulated_result"]
    # Liabilities and equity carry credit balances, which are negative in this ledger's sign
    # convention, so the identity is a sum rather than a difference.
    pivot["total_liabilities_and_equity"] = -(
        pivot[CURRENT_LIABILITY] + pivot[NON_CURRENT_LIABILITY] + pivot[EQUITY]
    )
    pivot["difference"] = pivot["total_assets"] - pivot["total_liabilities_and_equity"]
    return pivot


def cash_flow(ledger: pd.DataFrame, accounts: pd.DataFrame) -> pd.DataFrame:
    """Indirect cash flow from EBITDA — ADR 0018.

    Working capital movements appear on their own lines because that movement is what Northlake's
    story turns on; the direct method would bury it in the difference between two gross flows.
    """
    keys = ["month", "version_name", "scenario_name"]
    # The opening balance sheet is a position, not a period movement. Leaving it in makes the
    # first forecast month look like $1.16M of cash generation that never happened; it is the
    # cash the business already had.
    opening = ledger[ledger["memo"] == OPENING_MEMO]
    ledger = ledger[ledger["memo"] != OPENING_MEMO]
    series = metric_series(ledger, accounts)
    balances = balance_sheet(ledger)

    wc = balances[balances["account_code"].isin(WORKING_CAPITAL)].copy()
    wc["signed"] = wc["amount"] * wc["account_code"].map(WORKING_CAPITAL)
    movement = wc.groupby(keys, as_index=False)["signed"].sum()
    movement = movement.rename(columns={"signed": "Working capital movement"})

    by_month = monthly(ledger)
    non_cash = by_month[by_month["account_code"].isin(NON_CASH_ACCOUNTS)]
    non_cash = non_cash.groupby(keys, as_index=False)["amount"].sum()
    non_cash = non_cash.rename(columns={"amount": "Non-cash items added back"})

    interest = by_month[by_month["account_code"].isin(INTEREST_ACCOUNTS)]
    interest = interest.groupby(keys, as_index=False)["amount"].sum()
    interest = interest.rename(columns={"amount": "Interest and financing fees"})

    capex = by_month[by_month["account_code"] == CAPEX_ACCOUNT]
    capex = capex.groupby(keys, as_index=False)["amount"].sum()
    capex = capex.rename(columns={"amount": "Capital expenditure"})

    financing = by_month[by_month["account_code"].isin(FINANCING_ACCOUNTS)]
    financing = financing.groupby(keys, as_index=False)["amount"].sum()
    financing = financing.rename(columns={"amount": "Financing"})

    out = series[[*keys, "EBITDA"]].copy()
    for frame in (movement, non_cash, interest, capex, financing):
        out = out.merge(frame, on=keys, how="left")
    out = out.fillna(0.0)

    out["Cash generated from operations"] = (
        out["EBITDA"] + out["Non-cash items added back"] + out["Working capital movement"]
    )
    out["Free cash flow"] = (
        out["Cash generated from operations"]
        - out["Interest and financing fees"]
        - out["Capital expenditure"]
    )
    out["Movement in cash"] = out["Free cash flow"] - out["Financing"]
    out["Movement in cash"] = out["Free cash flow"] - out["Financing"]
    opening_cash = (
        opening[opening["account_code"] == "1000"]
        .groupby(["version_name", "scenario_name"], as_index=False)["amount"]
        .sum()
        .rename(columns={"amount": "Opening cash"})
    )
    out = out.merge(opening_cash, on=["version_name", "scenario_name"], how="left").fillna(
        {"Opening cash": 0.0}
    )
    out["Closing cash"] = (
        out["Opening cash"]
        + out.groupby(["version_name", "scenario_name"])["Movement in cash"].cumsum()
    )
    return out


def cash_tie(ledger: pd.DataFrame, accounts: pd.DataFrame) -> pd.DataFrame:
    """Cash flow closing cash against balance sheet cash — check 6b, §9 check 5."""
    flow = cash_flow(ledger, accounts)
    balances = balance_sheet(ledger)
    cash = balances[balances["account_code"] == "1000"]
    keys = ["month", "version_name", "scenario_name"]
    cash = cash.groupby(keys, as_index=False)["balance"].sum()
    cash = cash.rename(columns={"balance": "Balance sheet cash"})
    tie = flow[[*keys, "Closing cash"]].merge(cash, on=keys, how="outer").fillna(0.0)
    tie["difference"] = tie["Closing cash"] - tie["Balance sheet cash"]
    return tie
