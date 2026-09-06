# ADR 0004 — COGS boundary: outbound shipping and variable fulfilment in COGS, payment processing in opex

- **Status:** Accepted
- **Date:** 2026-09-05
- **Phase:** 1 (data contract)

## Context

Where the line falls between cost of goods sold and operating expense is genuinely contested in
direct-to-consumer businesses. The three disputed items are outbound shipping, fulfilment labour
and payment processing. Together they move reported gross margin by well over ten points.

The choice matters more than usual here because it is not channel-neutral. Outbound parcel cost and
payment processing are overwhelmingly DTC costs; wholesale ships pallets on partly customer-routed
freight and does not pay card fees. Putting all three in COGS narrows the reported DTC-versus-
wholesale margin gap; putting all three in opex widens it. The entire argument of the board pack
rests on the size of that gap, so the classification cannot be inherited by accident.

## Decision

**In COGS:**

- Landed product cost (product, inbound freight, duty), capitalised into inventory and released
  when units are sold
- Outbound shipping — DTC parcel net of carrier credits; wholesale freight where Northlake bears it
  under the shipping terms
- Variable fulfilment — pick-and-pack, per-order handling, packaging materials, variable warehouse
  handling and other transaction-based 3PL charges

**In operating expense:**

- Payment processing, as a variable selling expense within Sales and Marketing
- Fixed 3PL storage, retainers and account management

Customer-paid DTC shipping is recognised as revenue on its own line and is **never netted** against
outbound freight expense.

This produces three margin tiers rather than two:

```
Revenue - landed cost - outbound shipping - variable fulfilment      = Gross Profit
        - payment processing - variable marketing - variable selling = Contribution Profit
        - fixed operating expense                                    = EBITDA
```

The classification is **frozen across historical and forecast periods**.

## Rationale

Reported gross margin is intended to show the economic cost of producing and physically delivering
the product. Outbound shipping and transaction-based fulfilment are costs of delivery. Payment
processing arises from the customer's chosen method of payment, not from sourcing, manufacturing,
inventory or physical fulfilment, and belongs with the selling costs it resembles.

The test applied throughout is **variability with order volume, not department**. This is why the
same 3PL invoice splits across two lines: pick-and-pack varies with orders, the storage retainer
does not.

## Alternatives considered

**Payment processing in COGS.** The other common treatment, and defensible — the fee is unavoidable
on a DTC sale. Rejected because it conflates a payment-method cost with a fulfilment cost, and
because it would compress reported DTC gross margin by a further ~2.8 points, narrowing the channel
gap for a reason unrelated to how the two channels actually differ.

**All three in operating expense, gross margin on landed cost alone.** Produces the cleanest
product-margin figure (56.2% blended) and is common in wholesale-first businesses. Rejected: it
reports a DTC gross margin of 67% for a business that spends $10.50 per order getting the product
to the customer, which flatters DTC in exactly the comparison the model exists to inform.

## Consequences

Blended gross margin is 47.6% rather than the 56.2% product margin, and the channel gap is 18.5
points rather than 27. Both figures are stated in the data contract so the difference is never
mistaken for an error.

Contribution Profit becomes the tier at which channels are actually comparable, because it is where
marketing and payment processing land. Wholesale's contribution margin is far closer to DTC's than
the gross margin gap suggests — which is the substance of why the wholesale pivot was a reasonable
decision rather than a mistake.

Freezing the classification means gross margin movement is attributable to real drivers. This is
asserted, not assumed: the validation suite requires the gross-to-net and margin bridges to be
reconstructable from ledger accounts alone, without management adjustment.
