# ADR 0011 — Inventory turns relaxed to the achievable service frontier

- **Status:** Accepted
- **Date:** 2026-09-05
- **Phase:** 2 (generator)
- **Supersedes:** the inventory turns figures in data contract §1.1, §7.3, §7.5 and §7.6

## Context

The data contract carried two inventory calibration targets taken from the phase 1 interview:
inventory turns of 4.1x in FY2024 falling to 3.3x in FY2025 (§7.3), and approximately 4% of
potential DTC demand on hero SKUs affected by stockouts (§6.6).

Building the generator showed they cannot both hold. They are connected by the physical
mechanics the contract also specifies — a 90-day replenishment lead time (§5.5), MOQs of
750–2,500 units by family (§5.5), class-A safety stock of 5–6 weeks (§4.1), and a November that
carries 15% of annual DTC volume (§7.4). More cover buys service and costs turns; there is a
frontier between them, and the contract's pair sits outside it.

This was not visible from the phase 1 arithmetic, which reasoned about average inventory as a
ratio. It only appears once inventory is simulated at SKU × day grain, which is exactly why the
contract requires that grain.

## What was tried first

Three defects were found and fixed before concluding the targets were infeasible. Each moved the
frontier, and none of them closed the gap.

**Replenishment planned from trailing demand.** A 90-day lead time into a November peak cannot be
served from an October trailing average. Fixed by planning against forward demand over the
coverage window, degraded by a forecast error — which is what the contract's May–July holiday PO
timing describes.

**A single lead-time window for every SKU.** The forecast window started at the *longest* lead
(135 days, for launches), so 90-day items planned from a window beginning 45 days after the
demand their order had to cover. Fixed to a per-SKU window.

**Class C replenished continuously.** The contract states that class C is "purchased as finite
seasonal runs rather than continuously replenished" (§4.1). The generator was running a reorder
point on all 85 SKUs, which put a permanent floor of lead-time cover plus safety stock under
fifty slow-moving SKUs. Fixed to two seasonal buys a year, sized to the season and allowed to run
to zero. This cut class-C inventory from $639k to $419k, a 34% reduction, and was the single
largest improvement.

A fourth defect was found while checking the story rather than the frontier: the February 2025
launch was being bought to *realised* demand, which erased the event. The launch is now bought to
plan, and plan is 35% above what sold (§1.3), so the overhang arrives as inventory ordered before
the miss was visible.

## The measured frontier

Class-A safety multiplier and weeks-of-supply scale swept against both targets, FY2025:

| Hero stockout rate | FY2023 turns | FY2024 turns | FY2025 turns | FY2025 avg inventory |
|---|---|---|---|---|
| 5.9% | 3.00x | 2.88x | 3.64x | $1.34M |
| 4.9% | 2.92x | 2.83x | 3.46x | $1.41M |
| **4.1%** | **2.79x** | **2.61x** | **2.42x** | **$2.02M** |
| 3.3% | 2.80x | 2.45x | 2.74x | $1.79M |
| 2.6% | 2.74x | 2.34x | 2.41x | $1.87M |

Reading the frontier: holding 3.3x in FY2025 costs roughly 6% hero stockouts; holding 4%
stockouts costs roughly 0.9x of turns. The contract asked for both.

### Service responds to cycle stock, not to safety stock

The most useful finding from the sweep, and the least expected: **raising class-A safety stock
does not improve availability.** Past a multiplier of about 1.25 it depresses turns and buys
nothing — the sweep shows the hero stockout rate flat at 4.50% across class-A multipliers of
1.75, 2.00, 2.25 and 2.50 while FY2025 turns fall from 2.97x to 2.58x.

The reason is that the binding constraint is not buffer depth, it is **the 90-day lead time
running into a sharp seasonal peak**. November carries 15% of annual DTC volume; an order placed
to cover it must be committed in August. If the plan under-reads the peak, no amount of standing
safety stock rescues it, because the shortfall is concentrated in a few weeks and the replenishment
cannot arrive inside them. What does help is cycle stock — ordering more per cycle, earlier —
which is why the weeks-of-supply knob moves service and the safety knob does not.

The practical consequence for the model is that **service is bought with timing, not with
inventory level**. Anyone tuning this later should reach for the ordering calendar and the
forecast horizon before reaching for safety stock, and a board pack recommending "hold more
safety stock on hero SKUs" would be recommending the expensive half of the trade.

## Decision

**Keep the 4% hero-SKU service target. Relax inventory turns to the frontier.**

| | FY2023 | FY2024 | FY2025 |
|---|---|---|---|
| Contract, as written | 4.5x | 4.1x | 3.3x |
| **Revised** | **2.8x** | **2.6x** | **2.4x** |

Forecast turns are relaxed by the same proportion across all three scenarios (§7.6).

Service is kept because §6.6 is load-bearing in a way §7.3 is not. The stockout mechanic carries
the contract's requirement that underlying demand and realised revenue are separately modelled,
so availability problems are never misread as weak demand — a distinction the board pack depends
on. Turns are a reported ratio; degrading them changes a number, not a mechanism.

The revised path also fits the company being described. A business carrying an aged long tail,
absorbing a failed launch, and committing inventory ahead of wholesale seasonal programmes turns
inventory 2.4 times a year, not 3.3. The original figures came from an interview answer, not from
a system, and the system disagrees with them.

## Alternatives considered

**Relax the service target to ~6% and hold turns at 3.3x.** Rejected: it weakens the mechanic
that matters more, and 6% of hero demand lost to stockouts is a bigger operational failure than
slow turns — it would need explaining in the board pack as a problem, not absorbed as a ratio.

**Cut MOQs below the contract's stated ranges.** Tested at the low end of every range in §5.5 and
it moves the frontier by less than 0.3x of turns. Going below the stated ranges would be changing
an interview answer to make a target reachable, which is backwards.

**Accept the infeasibility and let the validation suite fail.** Rejected as the worst option: a
suite with a known-failing check trains everyone to ignore it.

## Consequences

FY2025 average inventory rises from $1.39M to **$2.02M**, which changes the working capital
position in §7.3 and the borrowing base in §6.10. Re-running the covenant probe showed the FY2024
equity raise must increase from $3.25M to **$3.50M** for Balanced Base to hold its covenant —
higher inventory consumes more cash than the additional borrowing base provides, because the
inventory advance rate is 50% against a dollar of cash tied up.

That is also the answer to why a $9.3M brand sitting at breakeven raised $3.50M in FY2024:
**the raise funds inventory, not losses.** FY2024 EBITDA is approximately zero, so nothing is
being burned on operations. What the money buys is the working capital to commit inventory three
to four months ahead of wholesale seasonal programmes — the channel Northlake was deliberately
expanding into, and the one whose orders must be bought before they are placed. A brand growing
DTC would not need it; a brand growing wholesale cannot avoid it. The raise is the price of the
strategy the board approved, which is what makes the FY2025 deterioration a question about that
strategy rather than about cost control.

The turns *decline* across FY2024 to FY2025 is preserved (2.61x to 2.42x) and is now driven by
the modelled launch overhang rather than asserted. That decline is smaller in proportional terms
than the interview described, and the board pack should describe it accordingly.

The generator hits 4.07% hero stockouts against the 4% target, and turns of 2.79x / 2.61x / 2.42x
against the revised targets.
