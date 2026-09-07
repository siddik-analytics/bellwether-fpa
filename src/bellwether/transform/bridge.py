"""Variance bridge — why a movement happened, not just how large it was.

`semantic.decompose` returns three **magnitudes**: performance variance, forecast revision,
scenario difference. A magnitude is not an explanation. The charter asks for commentary that says
*"gross margin fell 240bp, of which 180bp is channel mix"*, and that needs effects which sum to
the movement.

Gross profit is revenue at a margin rate, and revenue has a channel mix:

    GP = Σ_channel  revenue_c × rate_c

so a movement decomposes into three things, each measurable on **both** sides:

| Effect | What moved | Computed as |
|---|---|---|
| Revenue | how much was sold | Δ total revenue × the base's blended margin rate |
| Channel mix | where it was sold | actual revenue × Δ share × (base rate_c − blended rate) |
| Margin rate | what it earned per dollar | actual revenue_c × Δ rate_c, per channel |
| **Residual** | everything else | the movement, less the three above |

**Why revenue and not units.** The first version of this decomposed volume and price from unit
counts, and it produced effects of ±$1.5M on a −$239k movement — an artifact, not a finding. The
cause is that units are *measured* on the actual side and *reconstructed* on the budget side,
from an average order value and a wholesale net price. The two are not the same quantity, so
their difference is mostly reconstruction error, and splitting it into "volume" and "price" gave
two large numbers that cancelled and neither of which was true.

Revenue, margin rate and channel share are reported by both sides. Nothing here is reconstructed,
so nothing here is an artifact. Unit counts are still carried, as supporting detail where both
sides measure them, and are never used to compute an effect.

**The residual is never absorbed.** It is computed last and reported at its full size.
Interaction terms are deliberately not allocated: a rate change on revenue that also moved is
genuinely joint, and both allocating it and splitting it evenly are choices the data does not
support.

**The grain is not always channel.** Forecast periods post their cost of sales unallocated —
units are measured from transaction facts, and the forecast has none, so the §6.7 split cannot
run (ADR 0020). Channel gross profit is then meaningless: every channel shows a margin of 100%
and the whole cost sits in a corporate bucket. When that happens the bridge **drops to a blended
rate** and says so, and the residual carries what the grain cannot separate. A channel-mix effect
computed from a 100% margin would be a number with no meaning presented as an explanation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from bellwether.transform.units import money

#: Below this, a movement is not worth a sentence — criterion 6.17. Stated in the pack rather
#: than applied silently, because an undisclosed materiality filter is one the reader cannot see.
MATERIALITY = 25_000.0

CHANNELS = ("DTC", "Wholesale")


@dataclass(frozen=True)
class Quantities:
    """One side of a comparison: revenue and gross profit per channel, as reported.

    ``units`` is optional supporting detail. It is never used to compute an effect — see the
    module docstring for why.
    """

    label: str
    revenue: dict[str, float]
    gross_profit: dict[str, float]
    units: dict[str, float] = field(default_factory=dict)
    #: Gross profit that no channel owns — forecast cost of sales, which has no measured units
    #: behind it to split by. Included in the total; excluded from every channel rate.
    unallocated_gross_profit: float = 0.0

    @property
    def total_revenue(self) -> float:
        return sum(self.revenue.values())

    @property
    def total_gross_profit(self) -> float:
        return sum(self.gross_profit.values()) + self.unallocated_gross_profit

    @property
    def has_channel_grain(self) -> bool:
        """Whether channel margins mean anything on this side.

        They do not when a material share of gross profit is unallocated, because each channel
        then shows revenue with no cost against it.
        """
        total = abs(self.total_gross_profit)
        return total > 0 and abs(self.unallocated_gross_profit) / total < 0.05

    def rate(self, channel: str) -> float:
        revenue = self.revenue.get(channel, 0.0)
        return self.gross_profit.get(channel, 0.0) / revenue if revenue else 0.0

    @property
    def blended_rate(self) -> float:
        return self.total_gross_profit / self.total_revenue if self.total_revenue else 0.0

    def share(self, channel: str) -> float:
        total = self.total_revenue
        return self.revenue.get(channel, 0.0) / total if total else 0.0

    @property
    def measures_units(self) -> bool:
        return bool(self.units) and sum(self.units.values()) > 0


@dataclass(frozen=True)
class Effect:
    """One named cause, with the quantity that moved and by how much."""

    name: str
    amount: float
    driver: str
    detail: dict[str, float] = field(default_factory=dict)
    #: The figures printed inside ``driver``, declared so commentary can carry them and the
    #: prose test can find them. A number a reader sees that nothing declared is a number
    #: nothing can check — which is how "10,738,185" reached the pack alongside "$10.60M".
    driver_numbers: tuple[float, ...] = ()

    @property
    def is_material(self) -> bool:
        return abs(self.amount) >= MATERIALITY


@dataclass(frozen=True)
class Bridge:
    """A movement, its named causes, and what is left over."""

    metric: str
    base: Quantities
    comparison: Quantities
    effects: list[Effect]
    residual: Effect
    #: "channel" when both sides can attribute cost to a channel, "blended" when either cannot.
    grain: str = "channel"

    @property
    def movement(self) -> float:
        return self.comparison.total_gross_profit - self.base.total_gross_profit

    @property
    def explained(self) -> float:
        return sum(effect.amount for effect in self.effects)

    @property
    def material_effects(self) -> list[Effect]:
        ordered = sorted(self.effects, key=lambda e: abs(e.amount), reverse=True)
        return [effect for effect in ordered if effect.is_material]

    def frame(self) -> pd.DataFrame:
        rows = [{"effect": e.name, "driver": e.driver, "amount": e.amount} for e in self.effects]
        rows.append(
            {
                "effect": self.residual.name,
                "driver": self.residual.driver,
                "amount": self.residual.amount,
            }
        )
        return pd.DataFrame(rows)


def build(metric: str, base: Quantities, comparison: Quantities) -> Bridge:
    """Decompose the movement from ``base`` to ``comparison``.

    ``base`` is what was expected — the budget, or the prior period. ``comparison`` is what
    happened. Effects are signed so a positive amount raised gross profit.
    """
    effects: list[Effect] = []
    grain = "channel" if base.has_channel_grain and comparison.has_channel_grain else "blended"

    revenue_effect = (comparison.total_revenue - base.total_revenue) * base.blended_rate
    effects.append(
        Effect(
            "Revenue",
            revenue_effect,
            f"net revenue {money(base.total_revenue)} to {money(comparison.total_revenue)}",
            {"base": base.total_revenue, "comparison": comparison.total_revenue},
            driver_numbers=(base.total_revenue, comparison.total_revenue),
        )
    )

    if grain == "channel":
        mix = 0.0
        mix_detail: dict[str, float] = {}
        for channel in CHANNELS:
            shift = comparison.share(channel) - base.share(channel)
            mix_detail[channel] = shift
            mix += comparison.total_revenue * shift * (base.rate(channel) - base.blended_rate)
        leader = max(CHANNELS, key=lambda c: abs(mix_detail[c]))
        effects.append(
            Effect(
                "Channel mix",
                mix,
                f"{leader} share of revenue {base.share(leader):.1%} to "
                f"{comparison.share(leader):.1%}",
                mix_detail,
            )
        )

        rate_detail = {c: comparison.rate(c) - base.rate(c) for c in CHANNELS}
        rate = sum(comparison.revenue.get(c, 0.0) * rate_detail[c] for c in CHANNELS)
        worst = max(CHANNELS, key=lambda c: abs(rate_detail[c]))
        effects.append(
            Effect(
                "Margin rate",
                rate,
                f"{worst} margin {base.rate(worst):.1%} to {comparison.rate(worst):.1%}",
                rate_detail,
            )
        )
    else:
        # Cost of sales is unallocated on at least one side, so a channel margin is revenue with
        # no cost against it. One blended rate is the most this grain supports.
        shift = comparison.blended_rate - base.blended_rate
        effects.append(
            Effect(
                "Margin rate",
                comparison.total_revenue * shift,
                f"blended margin {base.blended_rate:.1%} to {comparison.blended_rate:.1%}",
                {"blended": shift},
            )
        )

    movement = comparison.total_gross_profit - base.total_gross_profit
    residual = Effect(
        "Unexplained at this grain",
        movement - sum(e.amount for e in effects),
        "interaction between effects, and anything the available grain cannot separate",
    )
    return Bridge(
        metric=metric,
        base=base,
        comparison=comparison,
        effects=effects,
        residual=residual,
        grain=grain,
    )


def quantities_from_ledger(
    label: str,
    revenue: dict[str, float],
    gross_profit: dict[str, float],
    unallocated_gross_profit: float = 0.0,
    units: dict[str, float] | None = None,
) -> Quantities:
    """A posted period, entirely from the ledger. Units are optional supporting detail.

    ``unallocated_gross_profit`` is the corporate bucket — forecast cost of sales that no channel
    owns, because the §6.7 split runs on measured units and the forecast has none.
    """
    return Quantities(
        label=label,
        revenue=revenue,
        gross_profit=gross_profit,
        units=units or {},
        unallocated_gross_profit=unallocated_gross_profit,
    )


def quantities_from_plan(label: str, plan: pd.DataFrame, drivers: dict) -> Quantities:
    """A planned period, from the plan and the drivers that produced it.

    The plan states revenue by channel and gross profit in total, so the channel split of gross
    profit comes from the **plan's own channel economics** — the per-channel margins its drivers
    imply — scaled so the total equals the gross profit the plan reports.

    Splitting it by revenue share instead was tried first and gave both channels an identical
    margin rate, which makes the mix effect structurally zero. A zero that cannot be anything
    else is worse than no number: it reads as a finding.
    """
    from bellwether.data.forecast import _unit_economics

    dtc_revenue = float(plan["dtc_revenue"].sum())
    ws_revenue = float(plan["wholesale_revenue"].sum())
    total_gp = float(plan["gross_profit"].sum())

    dtc_gm, ws_gm = _unit_economics(drivers)
    implied = {"DTC": dtc_revenue * dtc_gm, "Wholesale": ws_revenue * ws_gm}
    scale = total_gp / sum(implied.values()) if sum(implied.values()) else 0.0

    return Quantities(
        label=label,
        revenue={"DTC": dtc_revenue, "Wholesale": ws_revenue},
        gross_profit={c: implied[c] * scale for c in CHANNELS},
    )
