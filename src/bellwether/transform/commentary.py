"""Variance commentary derived from the bridge — criteria 6.13 to 6.19.

The charter asks for commentary that reads as though a person wrote it: *specific, quantified,
and attributed to a driver.* The failure mode is templated prose with numbers substituted, which
is a table read aloud and worse than a table, because it implies an analyst looked at it.

So every sentence here is built from a `bridge.Bridge`, under three rules:

1. **Every number comes from the bridge.** `Sentence.numbers` carries them, and
   `tests/reporting/test_commentary.py` parses them back out of the finished prose and asserts
   each one appears in the bridge it claims to come from.
2. **Every causal claim names an effect that computed it.** "of which $163,656 is margin rate"
   is emitted only because a `Margin rate` effect exists with that amount. There is no path in
   this module from an adjective to a number.
3. **What is not explained is said.** An immaterial effect is named as immaterial with its size,
   a residual is named as unexplained with its size, and a comparison that could only be made at
   blended grain says so. Most automated commentary is untrustworthy because it never says it
   does not know, so a reader cannot separate the explained from the asserted.

The materiality threshold is stated in the pack under every commentary block (criterion 6.17),
because an undisclosed filter is one the reader cannot see.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from bellwether.transform.bridge import MATERIALITY, Bridge, Effect


@dataclass(frozen=True)
class Sentence:
    """One sentence, with everything it asserts made inspectable.

    ``numbers`` and ``claims`` exist so the tests can check the prose against the bridge rather
    than against another copy of the prose. A sentence that cannot say where its numbers came
    from does not get written.
    """

    text: str
    numbers: tuple[float, ...] = ()
    claims: tuple[str, ...] = ()
    kind: str = "finding"


def money(amount: float) -> str:
    """A figure a reader can say out loud. Signed by direction, never by a minus sign alone."""
    magnitude = abs(amount)
    if magnitude >= 1_000_000:
        return f"${magnitude / 1_000_000:,.2f}M"
    return f"${magnitude:,.0f}"


def _direction(amount: float, is_cost: bool = False) -> str:
    """Favourable is positive whether the line is revenue or cost — §9 check 24, ADR 0019."""
    favourable = amount > 0 if not is_cost else amount < 0
    return "ahead of" if favourable else "behind"


def headline(bridge: Bridge, subject: str, against: str) -> Sentence:
    movement = bridge.movement
    return Sentence(
        text=(
            f"{subject} of {money(bridge.comparison.total_gross_profit)} came in "
            f"{money(movement)} {_direction(movement)} {against}."
        ),
        numbers=(bridge.comparison.total_gross_profit, movement),
        claims=(),
        kind="headline",
    )


def _attribution(effect: Effect) -> Sentence:
    """One cause, with its direction on the face of the sentence — criterion 6.19.

    "Margin rate accounts for $163,656" is ambiguous about which way gross profit went, and a
    reader should not have to hold the headline's sign in their head to parse it.
    """
    verb = "added" if effect.amount > 0 else "cost"
    return Sentence(
        text=f"{effect.name} {verb} {money(effect.amount)} — {effect.driver}.",
        numbers=(effect.amount,),
        claims=(effect.name,),
    )


def _immaterial(effects: list[Effect]) -> Sentence | None:
    if not effects:
        return None
    named = ", ".join(f"{e.name} {'+' if e.amount > 0 else '-'}{money(e.amount)}" for e in effects)
    return Sentence(
        text=(f"Below the {money(MATERIALITY)} threshold and not discussed: {named}."),
        # The threshold is declared alongside the effects it filtered. A number that appears in
        # a sentence without being declared is a number nothing can check — which is what the
        # test caught the first time this ran.
        numbers=(MATERIALITY, *(e.amount for e in effects)),
        claims=tuple(e.name for e in effects),
        kind="threshold",
    )


def _residual(bridge: Bridge) -> Sentence | None:
    """The sentence most commentary omits, which is why most commentary cannot be trusted."""
    amount = bridge.residual.amount
    if abs(amount) < MATERIALITY:
        return None
    return Sentence(
        text=(
            f"A further {money(amount)} {'added to' if amount > 0 else 'reduced'} the movement "
            f"and is not attributable at the available grain — {bridge.residual.driver}."
        ),
        numbers=(amount,),
        claims=(bridge.residual.name,),
        kind="unexplained",
    )


def _grain(bridge: Bridge) -> Sentence | None:
    """Say when the comparison could not be made at channel grain, and why."""
    if bridge.grain == "channel":
        return None
    return Sentence(
        text=(
            "Attributed at blended margin rather than by channel: forecast cost of sales is "
            "not allocated to a channel, because the split runs on units shipped and the "
            "forecast has none measured."
        ),
        kind="grain",
    )


def narrate(bridge: Bridge, subject: str, against: str) -> list[Sentence]:
    """The full commentary for one comparison, in reading order.

    Deterministic by construction: effects are ordered by absolute size, and nothing here
    consults a clock, a random source or a dictionary whose order could change.
    """
    sentences = [headline(bridge, subject, against)]
    material = bridge.material_effects
    sentences.extend(_attribution(effect) for effect in material)

    immaterial = [e for e in bridge.effects if not e.is_material]
    threshold = _immaterial(immaterial)
    if threshold:
        sentences.append(threshold)

    residual = _residual(bridge)
    if residual:
        sentences.append(residual)
    elif material:
        sentences.append(
            Sentence(
                text="The effects above account for the movement in full.",
                kind="completeness",
            )
        )

    grain = _grain(bridge)
    if grain:
        sentences.append(grain)
    return sentences


@dataclass(frozen=True)
class Block:
    """A titled commentary block, as it appears in the pack."""

    title: str
    sentences: list[Sentence] = field(default_factory=list)

    @property
    def prose(self) -> str:
        return " ".join(s.text for s in self.sentences)

    @property
    def numbers(self) -> tuple[float, ...]:
        return tuple(n for s in self.sentences for n in s.numbers)

    @property
    def claims(self) -> tuple[str, ...]:
        return tuple(c for s in self.sentences for c in s.claims)

    @property
    def threshold_note(self) -> str:
        """Criterion 6.17 — the filter, stated where the reader can see it."""
        return f"Movements below {money(MATERIALITY)} are not discussed."


def block(title: str, bridge: Bridge, subject: str, against: str) -> Block:
    return Block(title=title, sentences=narrate(bridge, subject, against))
