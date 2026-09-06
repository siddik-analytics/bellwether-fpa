# Phase 1 — Data contract interview

**Run this before writing any code or any part of `docs/data-contract.md`.**

## How to run it

Ask one question at a time and wait for the answer. Do not batch them. Do not propose answers
before asking.

If an answer is vague or the user says they don't know, offer two or three concrete options
with the downstream consequence of each, and let them choose. Never fill a gap with a default
of your own — every convention in this document becomes a rule the whole system inherits, and
a silently invented one is the difference between a model that reflects a real business and
one that reads as generated.

Record answers verbatim in `docs/phases/phase-01-answers.md` as you go. When the interview is
complete, draft `docs/data-contract.md` from those answers, plus ADRs for any question where a
real alternative was rejected.

Business: DTC brand with a wholesale channel. Roughly $8–12M revenue, three years of history,
36 months forward.

---

## A. Shape of the business

1. Revenue for the most recent complete year, and the two years before it. Is the story growth,
   flat, or recovery? *(This decides what the board pack argues. A growth story and a margin
   recovery story need different data.)*

2. Channel mix today — DTC versus wholesale as a share of revenue — and how that split has moved
   over the three years.

3. What does the company sell? Category, and roughly how many active SKUs. Is revenue
   concentrated in a few hero SKUs or spread across the catalogue?

4. Wholesale account structure: how many accounts, and how concentrated? One large retailer plus
   a long tail behaves very differently from fifty even accounts.

## B. The story the numbers should tell

5. **What is the central financial tension in this business?** Something a CFO would open the
   board meeting with. For example: gross margin compressing because wholesale is growing faster
   than DTC and carries materially lower margin, while wholesale simultaneously improves cash
   conversion. There must be a real trade-off in the data, visible in the numbers, or the
   variance commentary has nothing to say.

6. What went wrong in the last twelve months? One or two specific, dateable events — a supplier
   price increase, a failed product launch, a channel that underperformed plan, a freight spike.
   Clean data with no incidents produces a board pack no one would ever have needed to write.

## C. Revenue mechanics

7. DTC order economics: average order value, units per order, and repeat purchase rate.

8. Discounting: is there a promotional calendar? Roughly what share of DTC revenue moves on
   promotion, and is discounting site-wide or targeted?

9. Wholesale pricing: what is the wholesale discount off retail, and does it vary by account
   size? Are there chargebacks, co-op marketing deductions, or markdown allowances?

10. Returns: rate by channel, typical lag between sale and return, and whether returned units
    go back into sellable inventory.

## D. Cost of goods and inventory

11. Landed cost build: product cost, inbound freight, duty — roughly what share is each?

12. **What sits in COGS versus opex?** Specifically: outbound shipping, fulfilment labour,
    payment processing. This is genuinely contested, it moves gross margin by several points,
    and a reviewer will check whether the choice was made deliberately. State the convention and
    hold to it everywhere.

13. Purchasing: supplier lead times, minimum order quantities, and how far ahead purchase orders
    are placed.

14. Inventory: target turns, whether safety stock is held, and whether the business experiences
    stockouts or writes off obsolete stock.

## E. Working capital

15. DTC cash timing: settlement lag from the payment processor.

16. Wholesale receivables: stated terms versus actual DSO, and whether there is bad debt.

17. Payables: supplier terms, and whether deposits are required at PO.

## F. Operating expenses

18. Marketing: spend as a share of revenue, paid versus owned split, and whether it is managed
    to a CAC target or a fixed budget. *(This determines whether marketing is a revenue driver
    or a fixed cost in the model — a structural choice.)*

19. Headcount: approximate total, by function, and how it steps with revenue rather than
    scaling smoothly.

20. Fixed cost base: 3PL or own warehouse, office, software, and anything else that does not
    flex with volume.

## G. Structure and planning

21. Chart of accounts: roughly how many accounts, and are departments or cost centres needed?
    Single legal entity and single currency, or not?

22. Budget: how was the current-year budget set — top-down or bottom-up — and what is the
    reforecast cadence? What are the two or three scenarios leadership actually cares about?

23. Grain: what is the lowest level of detail that matters? Order line, daily SKU, something
    else? Is customer-level data needed for cohort and CAC analysis, or is channel-level enough?

---

## Output

When complete, produce:

- `docs/phases/phase-01-answers.md` — answers, verbatim
- `docs/data-contract.md` — entities, grain per fact table, keys, SCD handling, date spine,
  currency and rounding conventions, scenario dimension
- ADRs for any rejected alternative, particularly the COGS boundary in Q12 and the marketing
  treatment in Q18

Do not begin the generator until the user has read and approved `docs/data-contract.md`.
