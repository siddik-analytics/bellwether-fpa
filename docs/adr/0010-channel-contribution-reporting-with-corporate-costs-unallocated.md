# ADR 0010 — Channel contribution reporting with corporate costs unallocated

- **Status:** Accepted
- **Date:** 2026-09-05
- **Phase:** 1 (data contract)

## Context

Northlake's board compares DTC and wholesale constantly, and the comparison drives the largest
strategic decision the company faces. The comparison is only as good as the cost allocation behind
it.

The difficulty is that department is not channel, deliberately and correctly. Marketing supports
primarily DTC but incurs brand spend benefiting both. Supply Chain serves both. Wholesale Sales is
a department while Wholesale is a channel. Finance and Executive are corporate and attach naturally
to neither.

Any rule that pushes corporate cost down to channel must invent a driver, and the driver chosen
determines the answer. Allocating on revenue makes wholesale look worse simply because wholesale
revenue grew. That is an artefact of the allocation basis being presented as a finding about the
business.

## Decision

**Allocate only directly attributable costs to channel.**

- Marketing to DTC
- Account management to wholesale
- Fulfilment and freight by actual activity
- Payment processing to DTC

**Supply Chain, Finance, Executive, People and Technology remain in a single unallocated corporate
block** presented below channel contribution.

Reporting stops at Contribution Profit by channel. Below that line, the corporate block is shown
once, undivided.

## Rationale

This matches the three-tier hierarchy established in ADR 0004, where Contribution Profit is already
the level at which channel economics become comparable. Extending the same logic to allocation
means the reported channel comparison is composed entirely of costs that would genuinely disappear
if the channel did.

It also makes the comparison defensible under challenge. Every number in the channel contribution
statement can be traced to an activity in that channel. There is no line a sceptical reader can
attack as arbitrary, which matters because this comparison is the one the board will argue about.

The cost of the choice is real: there is no full channel P&L, and nobody can say what wholesale
"earns" after overhead. That is the honest position. Northlake's overhead does not vary with channel
mix in any way the data supports, so an allocated answer would be precision without accuracy.

## Alternatives considered

**Hybrid — direct costs plus driver-based allocation of shared operations.** Supply Chain and
Customer Experience pushed to channel on PO lines, order volume and units shipped. Genuinely
attractive: those drivers are defensible and the result is a fuller channel P&L management could
act on. Rejected for this phase as the weaker trade — it requires an allocation policy for each
driver, each of which becomes something a reviewer can contest, in exchange for pushing roughly
$600k of cost across a line that does not change any decision the board is making. Worth revisiting
if channel-level operating leverage becomes a live question.

**Full absorption to channel.** Everything allocated, typically on revenue or units. Rejected: the
corporate allocation is arbitrary by construction, and on a revenue basis it would make wholesale
appear progressively less profitable purely as a function of its growth — actively misleading in
the exact comparison the model exists to inform.

## Consequences

The board pack shows channel contribution, then a single corporate block, then EBITDA. Anyone
looking for "wholesale net profit" will not find it, and the pack should say why rather than
leaving the absence unexplained.

Corporate cost becomes highly visible as a single number, which is a useful side effect: it makes
operating leverage legible, since the block is largely fixed and step-fixed while revenue grows.

Because contribution excludes overhead, contribution margin percentages are not comparable to
externally quoted net margins. The basis must be labelled wherever the measure appears.
