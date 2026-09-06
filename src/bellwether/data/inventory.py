"""Inventory, purchasing and stockouts — contract §5.4, §5.5, §5.6, §6.6.

Purchasing is a constrained, lumpy process, not a balancing figure. MOQ rounding, a 90-day lead
time and a cancellation cut-off all bind, which is what makes the February 2025 launch failure
arithmetically forced rather than narrated: orders placed in October–December 2024 keep arriving
after demand weakness is visible in April–June 2025.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from bellwether.data import config as C


def landed_cost_series(products: pd.DataFrame, dates: pd.DatetimeIndex) -> np.ndarray:
    """Effective-dated landed cost per SKU per day — ADR 0003.

    Returns an array shaped (days, skus). The April 2025 step lifts product cost only, which is
    78% of landed, so the landed increase is ~6.2% rather than the headline 8%.
    """
    base = np.array([C.ACTUALS[2023].landed_cost] * len(dates))
    step = 1 + C.SUPPLIER_COST_INCREASE_PCT * C.LANDED_COST_SPLIT["product"]
    after = dates >= pd.Timestamp(C.SUPPLIER_COST_INCREASE_DATE)
    base = np.where(after, C.ACTUALS[2023].landed_cost * step, base)
    # Mild post-2025 drift, per §7.6 shared inputs.
    for year, cost in ((2026, 15.15), (2027, 15.30), (2028, 15.45)):
        base = np.where(dates.year == year, cost, base)
    return np.outer(base, products["cost_index"].to_numpy())


def daily_demand(
    dtc: pd.DataFrame, ws: pd.DataFrame, products: pd.DataFrame, dates: pd.DatetimeIndex
) -> np.ndarray:
    """Unit demand by day and SKU, both channels combined."""
    n_days, n_sku = len(dates), len(products)
    key_to_col = {k: i for i, k in enumerate(products["product_key"].to_numpy())}
    date_to_row = {d: i for i, d in enumerate(dates)}
    demand = np.zeros((n_days, n_sku))

    for frame, date_col, qty_col in (
        (dtc, "order_date", "quantity"),
        (ws, "shipment_date", "units"),
    ):
        rows = frame[date_col].map(date_to_row).to_numpy()
        cols = frame["product_key"].map(key_to_col).to_numpy()
        np.add.at(demand, (rows.astype(int), cols.astype(int)), frame[qty_col].to_numpy())
    return demand


def simulate(
    products: pd.DataFrame,
    suppliers: pd.DataFrame,
    demand: np.ndarray,
    dates: pd.DatetimeIndex,
    returns: pd.DataFrame,
    rng: np.random.Generator,
    wos_scale: dict[int, float] | None = None,
    class_multiplier: dict[str, float] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run the daily inventory simulation.

    Returns ``(inventory_daily, po_lines, stockouts)``. Inventory grain is SKU × location × day;
    daily balances are mandatory because stockouts last one to three weeks and a month-end
    balance cannot see them (§5.4).
    """
    n_days, n_sku = len(dates), len(products)
    sku_keys = products["product_key"].to_numpy()
    moq = products["moq"].to_numpy()
    classes = products["sku_class"].to_numpy()
    class_multiplier = class_multiplier or {"A": 1.00, "B": 1.00, "C": 1.00}
    wos_scale = wos_scale or {}
    safety_weeks = np.array([C.SAFETY_STOCK_WEEKS[c] * class_multiplier[c] for c in classes])
    lead = np.where(
        products["lifecycle_state"].to_numpy() == "launch",
        C.LAUNCH_LEAD_DAYS,
        C.REPLENISHMENT_LEAD_DAYS,
    )
    launch_day = np.array([(pd.Timestamp(d) - dates[0]).days for d in products["launch_date"]])

    # Returns that come back into sellable stock, by day and SKU.
    key_to_col = {k: i for i, k in enumerate(sku_keys)}
    date_to_row = {d: i for i, d in enumerate(dates)}
    recovered = np.zeros((n_days, n_sku))
    scrapped = np.zeros((n_days, n_sku))
    r_rows = pd.to_datetime(returns["return_receipt_date"]).map(date_to_row)
    valid = r_rows.notna()
    np.add.at(
        recovered,
        (
            r_rows[valid].to_numpy().astype(int),
            returns.loc[valid, "product_key"].map(key_to_col).to_numpy().astype(int),
        ),
        returns.loc[valid, "recoverable_quantity"].to_numpy(),
    )
    np.add.at(
        scrapped,
        (
            r_rows[valid].to_numpy().astype(int),
            returns.loc[valid, "product_key"].map(key_to_col).to_numpy().astype(int),
        ),
        returns.loc[valid, "non_sellable_quantity"].to_numpy(),
    )

    # Target weeks of supply is set from the contract's turns target for the year, so inventory
    # calibrates by construction rather than by tuning safety stock until turns happen to land.
    wos_target = np.zeros(n_days)
    for i, d in enumerate(dates):
        year = d.year
        turns = (
            C.ACTUALS[year].inventory_turns
            if year in C.ACTUALS
            else C.SCENARIOS["Balanced Base"][year]["inventory_turns"]
        )
        wos_target[i] = (52.0 / turns) * wos_scale.get(year, 1.0)

    on_hand = np.zeros(n_sku)
    in_transit = np.zeros((n_days + 400, n_sku))
    balances = np.zeros((n_days, n_sku))
    receipts_arr = np.zeros((n_days, n_sku))
    shipments_arr = np.zeros((n_days, n_sku))
    stockout_units = np.zeros((n_days, n_sku))
    po_rows: list[dict] = []
    po_id = 1

    trailing = demand[:56].mean(axis=0) if n_days > 56 else demand.mean(axis=0)
    cycle_days = 60.0
    supplier_for_family = {"Drinkware": 1, "Food storage": 3, "Accessories": 4, "Seasonal": 5}
    fam = products["product_family"].to_numpy()
    is_launch = products["lifecycle_state"].to_numpy() == "launch"
    is_finite_run = products["sku_class"].to_numpy() == "C"

    # Seed opening stock at roughly the target so the first quarter is not artificially starved.
    on_hand[:] = np.maximum(trailing * 7 * wos_target[0], 20)
    on_hand = np.where(is_finite_run, trailing * C.SEASONAL_RUN_DAYS * 0.5, on_hand)

    for day in range(n_days):
        on_hand += in_transit[day]
        receipts_arr[day] = in_transit[day]
        on_hand += recovered[day]
        on_hand -= np.minimum(on_hand, scrapped[day])

        want = demand[day]
        shipped = np.minimum(on_hand, want)
        stockout_units[day] = want - shipped
        on_hand -= shipped
        shipments_arr[day] = shipped
        balances[day] = on_hand

        # Replenishment is reviewed monthly, but ordering is reorder-point driven, not a
        # monthly top-up. Topping up to a target every month keeps every long-tail SKU
        # permanently at its MOQ and makes the turns target unreachable — a slow SKU has to be
        # allowed to run down between orders, which is what actually happens.
        if dates[day].day == 1:
            lo = max(0, day - 56)
            trailing = demand[lo : day + 1].mean(axis=0) if day > lo else trailing
            # Plan against the demand the order will actually cover, not the demand just past.
            # A November that carries 15% of annual DTC volume cannot be served from an October
            # trailing average on a 90-day lead time — which is why the contract has holiday POs
            # placed in May-July. Forward demand stands in for the planner's forecast, degraded
            # by a forecast error so the plan is good rather than clairvoyant.
            # Each SKU forecasts over its own lead window. Using the longest lead for every
            # SKU makes a 90-day item plan from a window starting 135 days out, so it misses
            # the 45 days of demand its own order actually has to cover.
            forward = np.zeros(n_sku)
            for lead_days in np.unique(lead):
                grp = lead == lead_days
                h0 = min(day + int(lead_days), n_days - 1)
                h1 = min(h0 + int(cycle_days), n_days)
                forward[grp] = demand[h0:h1, grp].mean(axis=0) if h1 > h0 else trailing[grp]
            forward = forward * rng.normal(1.0, 0.15, size=n_sku).clip(0.6, 1.5)
            weekly = np.maximum(forward, trailing * 0.4) * 7
            pipeline = in_transit[day + 1 : day + 1 + int(lead.max())].sum(axis=0)
            position = on_hand + pipeline
            lead_weeks = lead / 7.0
            reorder_point = weekly * (lead_weeks + safety_weeks)
            order_up_to = reorder_point + weekly * wos_target[day]
            need = order_up_to - position
            # A launch SKU has nothing to reorder against until it exists.
            active = (launch_day <= day + lead) & (position < reorder_point) & (need > 0)
            order_units = np.where(active, np.ceil(need / moq) * moq, 0.0)

            # Class C is bought as finite seasonal runs, not continuously replenished (§4.1,
            # Q14). Two buys a year, each sized to the season the receipt will serve, and the
            # stock is allowed to run to zero before the next buy. Replenishing these on a
            # reorder point is what put a permanent floor of lead-time cover plus safety stock
            # under fifty slow SKUs, and that floor is most of why inventory turns could not
            # reach target.
            season_units = np.zeros(n_sku)
            if dates[day].month in C.SEASONAL_BUY_MONTHS:
                s0 = min(day + int(lead.max()), n_days - 1)
                s1 = min(s0 + C.SEASONAL_RUN_DAYS, n_days)
                if s1 > s0:
                    season_demand = demand[s0:s1].sum(axis=0)
                    season_demand = season_demand * rng.normal(1.0, 0.15, n_sku).clip(0.6, 1.5)
                    # The February 2025 launch was bought to plan, and plan was 35% above what
                    # actually sold (§1.3). Sizing the buy to realised demand would erase the
                    # event: the overhang is the whole point, and it has to arrive as inventory
                    # ordered before the miss was visible.
                    first_buy = is_launch & (launch_day > day) & (launch_day <= day + lead)
                    season_demand = np.where(
                        first_buy,
                        season_demand / (1.0 - C.LAUNCH_SHORTFALL_VS_PLAN),
                        season_demand,
                    )
                    shortfall = season_demand - position
                    season_units = np.where(shortfall > 0, np.ceil(shortfall / moq) * moq, 0.0)
            order_units = np.where(is_finite_run, season_units, order_units)
            for col in np.nonzero(order_units)[0]:
                arrive = day + int(lead[col])
                if arrive >= n_days + 399:
                    continue
                in_transit[arrive, col] += order_units[col]
                po_rows.append(
                    dict(
                        po_id=po_id,
                        line_number=1,
                        supplier_key=supplier_for_family[fam[col]],
                        product_key=int(sku_keys[col]),
                        order_date=dates[day],
                        quantity=int(order_units[col]),
                        expected_receipt_date=dates[min(arrive, n_days - 1)],
                        shipment_mode="Air" if is_launch[col] and rng.random() < 0.25 else "Ocean",
                        is_launch_order=bool(is_launch[col]),
                    )
                )
                po_id += 1

    inv = pd.DataFrame(
        {
            "date": np.repeat(dates.to_numpy(), n_sku),
            "product_key": np.tile(sku_keys, n_days),
            "location_key": np.int32(1),
            "closing_units": balances.ravel(),
            "receipts": receipts_arr.ravel(),
            "shipments": shipments_arr.ravel(),
            "returns_in": recovered.ravel(),
            "write_offs": scrapped.ravel(),
        }
    )
    inv["opening_units"] = (
        inv["closing_units"]
        - inv["receipts"]
        - inv["returns_in"]
        + inv["shipments"]
        + inv["write_offs"]
    )

    pos = pd.DataFrame(po_rows)
    if not pos.empty:
        terms = suppliers.set_index("supplier_key")[["deposit_pct", "balance_days", "term_type"]]
        pos = pos.join(terms, on="supplier_key")
        pos["shipment_date"] = pos["expected_receipt_date"] - pd.Timedelta(days=32)
        pos["deposit_date"] = pos["order_date"]
        pos["balance_due_date"] = pos["shipment_date"] + pd.to_timedelta(
            pos["balance_days"], unit="D"
        )
        pos["cancellation_date"] = pos["expected_receipt_date"] - pd.Timedelta(
            days=C.PO_CANCELLATION_DAYS_BEFORE_RECEIPT
        )
        pos["actual_receipt_date"] = pos["expected_receipt_date"]
        pos["actual_shipment_date"] = pos["shipment_date"]
        pos["outstanding_quantity"] = 0
        pos["commitment_status"] = "received"

    stock = pd.DataFrame(
        {
            "date": np.repeat(dates.to_numpy(), n_sku),
            "product_key": np.tile(sku_keys, n_days),
            "suppressed_units": stockout_units.ravel(),
            "demand_units": demand.ravel(),
        }
    )
    stock = stock[stock["suppressed_units"] > 0].reset_index(drop=True)
    stock["lost_units"] = stock["suppressed_units"] * C.STOCKOUT_LOST_SHARE
    stock["deferred_units"] = stock["suppressed_units"] - stock["lost_units"]
    return inv, pos, stock


def _metrics(products, suppliers, demand, dates, returns, seed, wos_scale, class_mult, lc):
    """One simulation run, reduced to the two numbers the contract calibrates against."""
    rng = np.random.default_rng(seed)
    inv, pos, stock = simulate(
        products, suppliers, demand, dates, returns, rng, wos_scale, class_mult
    )
    n_sku = len(products)
    closing = inv["closing_units"].to_numpy().reshape(len(dates), n_sku)
    shipments = inv["shipments"].to_numpy().reshape(len(dates), n_sku)
    value = (closing * lc).sum(axis=1)
    cogs = (shipments * lc).sum(axis=1)

    turns = {}
    for year in sorted({d.year for d in dates}):
        mask = dates.year == year
        avg_inv = value[mask].mean()
        turns[year] = (cogs[mask].sum() / avg_inv if avg_inv else 0.0, avg_inv)

    is_hero = products["is_hero"].to_numpy()
    hero_demand = demand[:, is_hero].sum()
    hero_short = 0.0
    if len(stock):
        hero_keys = set(products.loc[is_hero, "product_key"])
        hero_short = stock.loc[stock["product_key"].isin(hero_keys), "suppressed_units"].sum()
    return inv, pos, stock, turns, (hero_short / hero_demand if hero_demand else 0.0)


def target_turns(year: int) -> float:
    return (
        C.ACTUALS[year].inventory_turns
        if year in C.ACTUALS
        else C.SCENARIOS["Balanced Base"][year]["inventory_turns"]
    )


def simulate_calibrated(
    products: pd.DataFrame,
    suppliers: pd.DataFrame,
    demand: np.ndarray,
    dates: pd.DatetimeIndex,
    returns: pd.DataFrame,
    rng_seed: int,
    iterations: int = 12,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """Solve the two inventory knobs against their two contract targets.

    Inventory turns (§7.3) and the hero-SKU stockout rate (§6.6) are both calibration targets and
    they pull against each other: more cover lifts service and depresses turns.

    The two knobs are solved jointly rather than by independent proportional feedback. Independent
    feedback diverges here — the service knob has more authority over class A inventory than the
    weeks-of-supply knob has over the total, so it wins every exchange and both ends up pinned at
    their clips with neither target met.

    Outer search is over the class-A safety multiplier; for each candidate the per-year
    weeks-of-supply scale is solved by damped iteration with the multiplier held fixed. The
    candidate whose stockout rate is closest to target, among those meeting the turns tolerance,
    wins; if none meets it, the best joint error wins and the caller can see the gap.
    """
    lc = landed_cost_series(products, dates)
    years = sorted({d.year for d in dates})
    best = None

    for class_a in (1.0, 1.25, 1.5, 1.75, 2.0, 2.5):
        class_mult = {"A": class_a, "B": 1.0, "C": 1.0}
        wos_scale = dict.fromkeys(years, 1.0)
        result = None
        for _ in range(iterations):
            result = _metrics(
                products, suppliers, demand, dates, returns, rng_seed, wos_scale, class_mult, lc
            )
            _, _, _, turns, hero = result
            moved = False
            for year in years:
                realised, _ = turns[year]
                target = target_turns(year)
                if realised > 0 and abs(realised - target) > 0.10:
                    step = (realised / target) ** 0.6
                    wos_scale[year] = float(np.clip(wos_scale[year] * step, 0.05, 4.00))
                    moved = True
            if not moved:
                break

        inv, pos, stock, turns, hero = result
        turns_err = max(abs(r - target_turns(y)) for y, (r, _) in turns.items())
        hero_err = abs(hero - C.STOCKOUT_DEMAND_SHARE)
        score = (turns_err > 0.20, hero_err, turns_err)
        if best is None or score < best[0]:
            best = (score, inv, pos, stock, turns, hero, dict(wos_scale), dict(class_mult))

    _, inv, pos, stock, turns, hero, wos_scale, class_mult = best
    report = {y: (r, target_turns(y), a) for y, (r, a) in turns.items()}
    report["hero_stockout_rate"] = hero
    report["wos_scale"] = wos_scale
    report["class_multiplier"] = class_mult
    return inv, pos, stock, report
