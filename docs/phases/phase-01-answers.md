# Phase 1 — Data contract interview: answers

> **Illustrative company, synthetic data.** Northlake is not a real business. Nothing in this
> document describes a real company, real people or real trading activity.

Interview conducted against `docs/phases/phase-01-interview.md`. Answers are recorded
verbatim. Where an answer was chosen from options offered in response to "I don't know", that
is noted alongside it.

- **Brand:** Northlake
- **Reporting entity:** Northlake, Inc.
- **Interview started:** 2026-09-05

**Naming convention.** *Northlake* is the modelled business — the brand, and "Northlake, Inc." as
the reporting entity. *Bellwether* is this project: the repository, the Python package and the
build tooling. The two are never interchangeable, and no artifact uses Bellwether as a company
name. Several answers as given used "Bellwether" for the company; they are recorded here with that
single substitution applied and are otherwise verbatim.

---

## A. Shape of the business

### Q1. Revenue history and business trajectory

> FY2023 revenue: $8.1M
> FY2024 revenue: $9.3M
> FY2025 revenue: $10.6M
>
> The business has been growing, but growth has begun to moderate. Revenue increased
> approximately 15% in FY2024 and 14% in FY2025. The company is still expanding, but the
> composition of growth is changing, with wholesale becoming a larger contributor. This
> creates a more complicated growth story because wholesale adds scale and improves cash
> conversion, but at a lower gross margin than DTC.

### Q2. Channel mix

> FY2023:
>
> * DTC: 72%
> * Wholesale: 28%
>
> FY2024:
>
> * DTC: 66%
> * Wholesale: 34%
>
> FY2025:
>
> * DTC: 59%
> * Wholesale: 41%
>
> Wholesale has grown materially faster than DTC over the last three years. DTC revenue has
> continued to grow in absolute dollars, but at a much slower rate, while wholesale expansion
> has driven most of the company's incremental revenue.
>
> The shift is intentional rather than purely demand-driven. Management has been expanding
> into larger retail accounts to diversify customer acquisition away from increasingly
> expensive paid digital channels and to improve inventory throughput. However, wholesale
> carries lower gross margins and introduces additional deductions, longer receivable terms,
> and greater customer concentration.

**Implied channel revenue** (derived, not stated by the interviewee):

| $M | FY2023 | FY2024 | FY2025 | CAGR |
|---|---|---|---|---|
| DTC | 5.83 | 6.14 | 6.25 | +3.5% |
| Wholesale | 2.27 | 3.16 | 4.35 | +38.4% |
| **Total** | **8.10** | **9.30** | **10.60** | **+14.4%** |

DTC is close to flat in dollar terms; essentially all incremental revenue is wholesale.

### Q3. Product category, SKU count, and concentration

> Northlake is a premium home and lifestyle brand selling reusable drinkware, food storage,
> and related accessories.
>
> The active assortment consists of approximately 85 SKUs:
>
> * Drinkware: ~35 SKUs
> * Food storage: ~25 SKUs
> * Accessories and replacement parts: ~15 SKUs
> * Seasonal / limited-edition products: ~10 SKUs
>
> Revenue is moderately concentrated rather than evenly spread across the catalogue.
>
> Approximately:
>
> * Top 5 SKUs: 38% of revenue
> * Top 10 SKUs: 55% of revenue
> * Remaining catalogue: 45% of revenue
>
> The largest products are a small group of core drinkware SKUs that sell consistently across
> both DTC and wholesale. Seasonal colours and limited editions are more important within DTC
> and are used to drive launches, promotional activity, and repeat purchases.
>
> The long tail is commercially relevant but creates inventory complexity. Slower-moving
> colour and size variants account for a disproportionate share of aged inventory and markdown
> risk, while the hero SKUs periodically experience stockouts during peak demand periods.

### Q4. Wholesale account structure and concentration

> Northlake sells through approximately 38 active wholesale accounts.
>
> The account base is concentrated, with a small number of national and regional retailers
> accounting for most wholesale revenue.
>
> Approximate FY2025 wholesale concentration:
>
> * Largest account: 24% of wholesale revenue
> * Second-largest account: 15%
> * Third-largest account: 10%
> * Top 5 accounts combined: 62%
> * Remaining ~33 accounts: 38%
>
> The largest customer is a national specialty retailer that expanded Northlake into additional
> stores during FY2025. This account has been the single biggest contributor to wholesale
> growth and is expected to remain important in the forward plan.
>
> The next four major accounts are a mix of regional lifestyle retailers and premium
> department-store groups. The remaining customer base is fragmented across independent stores
> and smaller regional chains.
>
> The concentration creates a genuine commercial risk. Losing or materially reducing orders
> from the largest account would have a noticeable impact on revenue, inventory purchasing, and
> cash flow. At the same time, larger wholesale accounts provide more predictable order volumes
> and lower customer-acquisition costs than DTC.
>
> Wholesale contracts are not fully guaranteed. Most large accounts provide seasonal purchase
> orders rather than binding annual volume commitments, so forecast visibility improves
> materially only once purchase orders are received.

**Implied scale** (derived): the largest account is ~$1.04M, close to 10% of total FY2025
revenue. Large enough that its loss is a board-level risk and worth a scenario, not large
enough that the business is a single-customer contractor.

## B. The story the numbers should tell

### Q5. Central financial tension

> Northlake's central financial tension is that the company can continue growing revenue
> through wholesale, but that growth is becoming less profitable and more working-capital
> intensive than management originally planned.
>
> Wholesale has increased from 28% of revenue in FY2023 to 41% in FY2025 and has become the
> main source of incremental growth. This has helped Northlake diversify away from expensive
> paid DTC acquisition and has improved inventory throughput, particularly for core products.
>
> However, wholesale carries structurally lower gross margins because of retailer pricing,
> promotional allowances, chargebacks, and account-specific deductions. As the channel mix
> shifts, consolidated gross margin is declining even though total revenue is increasing.
>
> At the same time, the economics are not simply "DTC good, wholesale bad."
>
> DTC has materially higher gross margin, but customer acquisition costs have risen and
> paid-media efficiency has weakened. Incremental DTC growth therefore requires increasingly
> expensive marketing spend.
>
> Wholesale has lower gross margin, but customer acquisition costs are minimal and large
> purchase orders create better forward demand visibility. It also helps Northlake move higher
> volumes of core inventory.
>
> The complication is cash.
>
> Northlake must commit to inventory several months before wholesale orders are delivered and
> paid. Large retailers then pay on extended terms, creating a period where growth consumes
> cash despite appearing profitable in the P&L.
>
> Management therefore faces a genuine trade-off:
>
> **Should Northlake continue pursuing wholesale-led growth and accept margin dilution and
> higher working-capital requirements, or slow wholesale expansion and focus on rebuilding
> higher-margin DTC growth despite weaker paid-media economics?**
>
> The board is particularly focused on whether Northlake can maintain double-digit revenue
> growth while stabilising gross margin and avoiding another material build in inventory and
> receivables.
>
> The forward plan should therefore be judged on four linked outcomes:
>
> * Revenue growth
> * Gross margin
> * Inventory productivity
> * Operating cash flow
>
> A plan that achieves revenue growth but misses materially on any of the other three would not
> be considered successful.

**Downstream consequences of this answer** (noted at interview time, to be honoured by the
data contract and the model):

- Gross margin must be decomposable into channel mix, price/discount, and landed cost effects.
  A single consolidated GM% line cannot support the argument above.
- Wholesale deductions (allowances, chargebacks, markdown support) must be modelled as
  distinct contra-revenue or COGS items, not netted invisibly into price.
- The cash conversion cycle is a first-class output, not a derived afterthought: inventory
  commitment lead time, DSO split by channel, and DPO all have to be explicit drivers.
- The four judged outcomes above are the executive summary page of the board pack and the
  top-line KPI set in Power BI.

### Q6. What went wrong in the last twelve months?

> Two material events affected Northlake during FY2025.
>
> #### 1. Supplier cost increase — effective April 2025
>
> Northlake's primary drinkware supplier implemented an average 8% product cost increase
> effective April 2025, driven by higher stainless-steel input costs, labour, and packaging.
>
> Management did not immediately pass the full increase through to customers.
>
> DTC retail pricing was increased selectively during Q3 2025, while wholesale pricing remained
> largely unchanged for existing seasonal orders that had already been quoted or committed.
>
> As a result, gross margin compressed during the middle of FY2025, particularly in wholesale.
>
> The impact was most visible in Northlake's core drinkware range, which represents the largest
> share of company revenue.
>
> Management expects part of the margin pressure to recover through:
>
> * selective DTC price increases,
> * higher wholesale pricing on new purchase orders,
> * supplier renegotiation,
> * packaging simplification,
> * and improved freight consolidation.
>
> However, the business does not expect to recover the full cost increase immediately.
>
> #### 2. Spring product launch underperformed — February to June 2025
>
> Northlake launched a new insulated food-storage range in February 2025.
>
> The launch was planned as one of the company's major DTC growth initiatives for the year and
> inventory was purchased ahead of an expected spring marketing campaign and wholesale rollout.
>
> Actual consumer demand was materially below plan.
>
> By the end of June 2025:
>
> * launch revenue was approximately 35% below plan,
> * sell-through was substantially weaker than the core drinkware range,
> * inventory remained above target,
> * and management reduced planned replenishment orders.
>
> Northlake began targeted promotional activity in Q3 2025 to clear slower-moving colours and
> configurations.
>
> The launch did not become a total write-off: several core SKUs continue to sell, and selected
> wholesale customers have reordered them. However, the breadth of the original assortment
> proved too aggressive.
>
> The result was a build in aged inventory and additional markdown pressure during the second
> half of FY2025.
>
> These two events are important because they affected different parts of the financial model.
>
> The supplier increase reduced unit margin on Northlake's strongest products, while the failed
> launch tied up cash in weaker inventory.
>
> Together, they explain why FY2025 revenue could still grow strongly while gross margin,
> inventory turns, and operating cash conversion deteriorated versus plan.

**Downstream consequences** (noted at interview time):

- Landed cost must be effective-dated, not a static per-SKU constant. The April 2025 step
  change is the single most visible driver in the FY2025 margin bridge.
- Price and cost move on *different* dates and by *different* amounts per channel. Wholesale
  price is fixed at the point a seasonal PO is quoted, so already-committed orders carry the
  higher cost at the old price — the mechanism that concentrates the margin hit in wholesale.
- SKUs need a launch date and a lifecycle state, so the February 2025 cohort can be isolated
  and its sell-through compared with the core range.
- Inventory needs ageing, and markdown/promotional activity needs to be attributable to
  specific SKUs, so the Q3 2025 clearance is visible rather than assumed.

## C. Revenue mechanics

### Q7. DTC order economics

> Northlake's current DTC order economics are approximately:
>
> * Average order value: $78
> * Average units per order: 1.7
> * Implied average selling price per unit: approximately $46
> * 12-month repeat purchase rate: approximately 29%
>
> AOV has increased modestly over the last three years, driven by selective price increases,
> bundles, and a larger mix of premium drinkware products.
>
> Units per order have remained relatively stable. Most first-time customers purchase one core
> product plus an accessory or secondary item, while larger baskets are more common during
> gifting periods and promotional events.
>
> Repeat behaviour is meaningful but not exceptionally high.
>
> Approximately 29% of first-time DTC customers place another order within 12 months. Repeat
> customers tend to have:
>
> * higher average order values,
> * lower marketing acquisition costs,
> * more accessory purchases,
> * and stronger participation in new colour and limited-edition launches.
>
> The remaining customer base is relatively acquisition-dependent. Many customers purchase a
> durable core product and do not need to repurchase frequently, meaning Northlake cannot rely
> on subscription-like repeat behaviour.
>
> Repeat purchase also varies materially by cohort.
>
> Customers acquired organically, through referrals, or from the email/SMS database typically
> repeat at a higher rate than customers acquired through broad paid-social campaigns.
>
> This distinction is important for the model because DTC revenue should not be forecast solely
> from total marketing spend. Revenue growth depends on a combination of:
>
> * new customer acquisition,
> * acquisition channel mix,
> * repeat customer behaviour,
> * average order value,
> * and promotional activity.
>
> Management's planning objective is to increase the 12-month repeat purchase rate from
> approximately 29% toward the low-to-mid 30% range over the forecast period rather than
> assuming a dramatic improvement.

**Implied DTC order volume** (derived): FY2025 DTC revenue of ~$6.25M at a $78 AOV is roughly
**80,000 orders per year**, about 220 per day before seasonality. That is the order-line volume
the generator must produce for the most recent year.

**Downstream consequences:**

- Customer-level data is required, not just channel-level: cohorts, acquisition channel, and
  first-versus-repeat order flags all carry model logic. This largely settles Q23 for DTC.
- DTC revenue is driven bottom-up from new customers x acquisition mix x repeat rate x AOV,
  **not** as a function of total marketing spend. Marketing is therefore not a simple revenue
  driver — see Q18.
- Acquisition channel must be an attribute of the customer, since repeat rate varies by it.

**Open point carried forward:** whether the $78 AOV is gross or net of discounts, and whether
it includes shipping revenue. Raised with Q8.

### Q8. Discounting and promotional calendar

> Northlake operates a structured promotional calendar, but the brand does not rely on
> continuous site-wide discounting.
>
> Approximately 27% of annual DTC gross revenue is generated during some form of promotional
> activity.
>
> Promotions are concentrated around a small number of major commercial periods:
>
> * Spring campaign: March / April
> * Summer event: June
> * Back-to-school / fall launch: August / September
> * Black Friday / Cyber Monday: November
> * Holiday gifting: December
>
> Black Friday / Cyber Monday is the single largest promotional period and accounts for
> approximately 12% of annual DTC revenue.
>
> Most promotions are targeted rather than fully site-wide.
>
> Typical promotional mechanics include:
>
> * 15%–20% discounts on selected products
> * bundle offers
> * free shipping thresholds
> * loyalty / email subscriber offers
> * markdowns on discontinued colours
> * selective site-wide promotions during Black Friday
>
> The average realised discount on promoted orders is approximately 16%.
>
> Northlake generally avoids discounting its newest launches and strongest hero SKUs outside
> major events. Promotions are used more heavily on:
>
> * slower-moving colour variants,
> * seasonal products,
> * older inventory,
> * and products with excess weeks of supply.
>
> Promotional demand creates meaningful seasonality in both revenue and gross margin.
>
> DTC revenue typically spikes during November and December, while gross margin percentage
> declines because of heavier discounting, free-shipping offers, and a higher mix of
> promotional orders.
>
> Management therefore plans DTC revenue using both baseline demand and an explicit promotional
> calendar rather than applying a flat monthly growth rate.
>
> Promotions are also subject to an internal profitability threshold. Marketing and
> merchandising teams can use discounting to accelerate inventory sell-through, but campaigns
> expected to reduce contribution margin below an approved threshold require finance review.
>
> The 36-month forecast should therefore model promotional intensity as a driver of:
>
> * DTC conversion
> * average selling price
> * gross margin
> * inventory sell-through
> * and marketing efficiency

**Downstream consequences:**

- A promotional calendar is a modelled input with its own dimension, not a seasonality factor
  baked into a monthly index. It has to be visible as a driver the forecast can be flexed on.
- Discount is contra-revenue at order-line grain, so gross-to-net is reconstructable. At ~27%
  of revenue promoted and ~16% realised discount, discount is roughly 4% of gross DTC revenue.
- Promotion targeting is a function of inventory state (weeks of supply, colour variant age),
  which links the promotional calendar to the inventory module rather than leaving it exogenous.
- November and December carry both a revenue spike and a gross margin trough. The seasonality
  in the generator must move revenue and margin in opposite directions in those months.

### Q8a. AOV basis and shipping revenue (clarification)

Asked as a rider to Q8, not answered in prose, then put as options with their consequences.
Chosen:

- **The $78 AOV is net of discounts.** Gross AOV is therefore ~$81.50. This matches how
  Shopify and comparable platforms report AOV. *(The order count first derived here was
  superseded at Q12c once the revenue basis was pinned down — see that section.)*
- **Shipping charged to the customer is recognised as revenue on its own line**, excluded from
  the $78 merchandise AOV. Free-shipping thresholds are consequently a visible revenue give-up
  during promotions rather than a pure cost effect.

### Q9. Wholesale pricing, account discounts, and deductions

> Northlake does not use one fixed wholesale discount across all accounts.
>
> Wholesale pricing is generally set as a discount to suggested retail price, with the discount
> increasing for larger customers.
>
> Typical pricing structure:
>
> * Small independent retailers: 40% discount to MSRP
> * Regional chains: 45% discount to MSRP
> * Large national accounts: 48%–50% discount to MSRP
>
> The weighted-average wholesale discount across the portfolio is approximately 46% of MSRP.
>
> Larger accounts receive deeper discounts because of higher order volumes, broader store
> coverage, and stronger negotiating leverage.
>
> In addition to the invoice discount, larger retailers can generate several off-invoice
> deductions.
>
> Typical deductions include:
>
> * Co-op marketing: 1%–3% of gross wholesale sales
> * Markdown allowances: approximately 1%–2%
> * Freight or routing deductions: approximately 0.5%
> * Compliance / chargebacks: approximately 0.5%–1.0%
> * New-store or promotional support: negotiated separately for selected accounts
>
> Across the wholesale channel, total deductions average approximately 3% of gross invoiced
> sales.
>
> For the largest national account, deductions can reach 5%–6% in heavily promotional periods.
>
> Chargebacks arise mainly from:
>
> * late shipments,
> * routing-guide non-compliance,
> * short shipments,
> * incorrect carton or labelling requirements,
> * and agreed promotional support.
>
> Management historically budgeted wholesale revenue primarily on invoice value and treated
> several deductions as period expenses or forecast adjustments.
>
> As wholesale became a larger part of the business, finance moved toward forecasting net
> wholesale revenue at the account level:
>
> Gross wholesale billings
> less contractual discounts
> less expected co-op / markdown allowances
> less expected chargebacks
> = Net wholesale revenue
>
> Large accounts are therefore forecast individually, while smaller accounts are grouped into
> tiers with common pricing and deduction assumptions.
>
> The model should retain both gross billings and net revenue rather than storing only the net
> amount, because changes in deductions are an important driver of wholesale margin variance.

**Downstream consequences:**

- Wholesale accounts carry a **pricing tier** (independent / regional / national) as a
  dimension attribute, driving the MSRP discount. Tier is the mechanism by which growth in the
  largest accounts dilutes margin even at constant SKU mix.
- **Both gross billings and net revenue are stored**, with each deduction type as its own
  contra-revenue line. Deductions are a named driver of wholesale margin variance, so they
  cannot be netted at source.
- Deduction rates vary by account, not just by tier — the largest account reaches 5–6% in
  promotional periods against a 3% channel average.
- The top five accounts are forecast individually; the remaining ~33 are forecast by tier.
  That is a modelling grain decision, not just a presentation one.

**Implied unit economics** (derived, to be confirmed once landed cost is known at Q11):

| Per unit | DTC | Wholesale |
|---|---|---|
| MSRP | ~$48 | ~$48 |
| Realised price | ~$46 (net of ~4% blended discount) | ~$25.90 (54% of MSRP) |
| Less deductions | — | ~$0.80 (3%) |
| **Net realised** | **~$46.00** | **~$25.10** |

Wholesale realises roughly **55% of the DTC net price per unit**. That spread is what makes the
channel mix shift move consolidated gross margin, and it is large enough for the mix effect to
dominate the margin bridge.

### Q10. Returns policy, rate, timing, and inventory treatment

> Northlake experiences materially different return behaviour between DTC and wholesale.
>
> #### DTC returns
>
> DTC return rate is approximately **7% of net merchandise sales**.
>
> Return rates vary by product category:
>
> * Core drinkware: approximately 5%–6%
> * Food storage: approximately 7%–8%
> * Seasonal / limited-edition items: approximately 9%–10%
> * Accessories: approximately 3%–4%
>
> Most DTC returns occur within **30 days of purchase**, with an average lag of approximately
> **18 days** between the original sale and the return being processed.
>
> Approximately **80% of returned DTC units are recoverable into sellable inventory** after
> inspection and repackaging.
>
> The remaining 20% is split between:
>
> * damaged or used products,
> * cosmetic defects,
> * packaging damage,
> * and items that are uneconomic to rework.
>
> Recoverable units are returned to available inventory at their original inventory cost.
> Non-recoverable units are written off through inventory shrink / obsolescence.
>
> Refunds are recorded as a reduction of revenue rather than an operating expense.
>
> #### Wholesale returns
>
> Wholesale returns are much lower and are approximately **1.5% of net wholesale sales**.
>
> Wholesale customers generally cannot return normal sell-through inventory. Returns typically
> relate to:
>
> * damaged shipments,
> * product defects,
> * retailer-approved markdown or return-to-vendor arrangements,
> * and discontinued seasonal inventory.
>
> The lag is longer than DTC, typically **45–90 days** after the original shipment.
>
> Approximately **50% of wholesale returned units are recoverable into sellable inventory**.
>
> Returned product from larger retailers is more likely to have packaging damage, store
> stickers, or handling wear, so a larger share is either:
>
> * sold through clearance channels,
> * written down,
> * or written off.
>
> #### Forecasting convention
>
> Returns are modelled separately by channel rather than using a single blended rate.
>
> DTC returns are driven by:
>
> * merchandise sales,
> * category mix,
> * promotional intensity,
> * and the return lag.
>
> Wholesale returns are driven by:
>
> * account mix,
> * seasonal programmes,
> * product quality issues,
> * and specific return-to-vendor arrangements.
>
> The model should use an explicit lag so that returns in one month can relate to revenue
> recognised in a prior month rather than simply reducing current-month sales at a flat
> percentage.

**Downstream consequences:**

- A return is a **fact row linked to the originating sale**, carrying its own date. The lag is
  a modelled distribution (DTC ~18 days mean, mostly inside 30; wholesale 45–90 days), not a
  percentage applied to the current month.
- Return rate is a **product-category attribute**, not a channel constant, so category mix
  shifts move the blended rate on their own.
- Returned units split into a recoverable path (back to inventory at original cost: 80% DTC,
  50% wholesale) and a write-off path through shrink/obsolescence. Both must be traceable.
- Refunds reduce revenue; they are not an operating expense. This is consistent with the
  gross-to-net treatment established at Q9.

### Q10a. Period-end treatment of expected returns (raised, not in the script)

An 18-day mean DTC return lag means a material share of each month's returns arrives in the
following month. After Black Friday that distortion is large enough to change the story the
November and December numbers tell. The convention was not documented, so it was put as
options rather than defaulted.

**Chosen: refund liability and right-of-return asset, ASC 606 basis.** Revenue is recognised
net of expected returns; a refund liability and a return asset (recoverable inventory at cost)
are carried on the balance sheet and unwind as returns arrive.

Rejected: recording returns only as processed (overstates revenue and margin in every growing
or seasonally peaking month), and reserving only at year-end (leaves a visible December
distortion and makes monthly gross margin non-comparable).

> **ADR required.** Revenue recognition timing for returns, with both rejected alternatives.

## D. Cost of goods and inventory

### Q11. Landed cost build

> Northlake's landed inventory cost is made up of three primary components:
>
> * Product cost: approximately 78%
> * Inbound freight: approximately 12%
> * Import duty and customs: approximately 10%
>
> These percentages are averages across the portfolio and vary by product family, supplier, and
> shipment method.
>
> Core drinkware generally has the most stable landed-cost profile because volumes are high and
> production runs are predictable.
>
> Seasonal products and new launches have a higher freight burden because:
>
> * order quantities are smaller,
> * shipment consolidation is weaker,
> * and expedited freight is sometimes used when launch timing is at risk.
>
> Northlake sources most finished goods from overseas contract manufacturers.
>
> Standard purchasing assumes ocean freight. Air freight is treated as an exception and is
> approved only where the commercial impact of a stockout or delayed launch is expected to
> exceed the incremental freight cost.
>
> Air freight can increase landed cost materially and therefore is tracked separately as a
> management variance rather than blended into the standard freight assumption.
>
> Landed cost is capitalised into inventory and expensed through COGS when the related units are
> sold.
>
> For planning purposes, landed cost is modelled at SKU or product-family level using:
>
> * supplier unit cost,
> * expected freight rate,
> * duty rate,
> * shipment mode,
> * and purchase volume.
>
> The model should distinguish between:
>
> * standard landed cost,
> * purchase price variance,
> * freight variance,
> * and duty / customs variance.
>
> This is important because Northlake's April 2025 supplier price increase primarily affected
> product cost, while freight volatility and expedited shipments can create separate
> gross-margin pressure.

**Downstream consequences:**

- This specifies a **standard cost system with variance accounting**, not actual costing.
  Inventory is carried at standard landed cost; purchase price, freight and duty variances are
  captured separately. That is a substantive choice and needs an ADR.
- Landed cost is effective-dated at SKU or product-family level, with three separately
  movable components. The April 2025 event moves product cost only, which is what allows the
  margin bridge to separate supplier price from freight volatility.
- Shipment mode (ocean / air) is an attribute of a purchase order, and air freight is a
  reportable exception rather than an averaged assumption.

**Gap:** the answer gives the *composition* of landed cost but not its *level*. Raised below.

### Q11b. Average landed cost per unit

> Northlake's average landed inventory cost is approximately **$15 per unit**.
>
> This represents the blended landed cost across the active product portfolio and includes:
>
> * supplier product cost,
> * inbound freight,
> * duty and customs.
>
> At the current realised selling economics, this implies approximately:
>
> * DTC realised merchandise revenue per unit: ~$46
> * DTC product gross margin before Q12 classification: ~67%
> * Wholesale realised revenue per unit: ~$25.10
> * Wholesale product gross margin before Q12 classification: ~40%
> * Blended product gross margin at the current 59% DTC / 41% wholesale mix: ~56%
>
> The $15 figure is a portfolio average rather than a standard cost applied uniformly across all
> SKUs.
>
> Indicative landed-cost ranges are:
>
> * Core drinkware: $14–$17 per unit
> * Food storage: $12–$16 per unit
> * Accessories / replacement parts: $3–$9 per unit
> * Seasonal and limited-edition products: generally 5%–15% above comparable core products
>   because of smaller production runs and less efficient freight.
>
> Hero SKUs tend to have better landed-cost economics because Northlake can place larger
> production runs and consolidate freight more efficiently.
>
> The model should therefore retain landed cost at SKU or product-family level while using
> approximately $15 per unit as the company-level FY2025 anchor.

**Implied FY2025 unit volumes** (derived; these size the generator):

| | Net revenue | Net price/unit | Units |
|---|---|---|---|
| DTC | $6.25M | ~$46.00 | ~136,000 |
| Wholesale | $4.35M | ~$25.10 | ~173,000 |
| **Total** | **$10.60M** | | **~315,000 shipped** |

Restated after the post-return review: **141,723 DTC units and 173,307 wholesale units shipped,
~315,000 in total**. Of these, 12,521 are returned and 9,237 recovered to inventory, so landed COGS
is $15 × (315,030 − 9,237) = **$4.587M**, a blended *product* gross margin of **56.7%**.

Product gross margin is not reported gross margin. It excludes outbound shipping and variable
fulfilment, which the COGS boundary at Q12 places in cost of sales. Reported blended gross margin is
**47.0% before shrink, 46.7% after** — see Q12b and Q20a as restated.

Note that **wholesale moves more units than DTC on less revenue** (173k vs 136k). That is the
quantitative form of the "wholesale improves inventory throughput" claim in Q5, and it means
the inventory and fulfilment modules are driven mostly by wholesale volume while the revenue
and marketing modules are driven mostly by DTC.

### Q12. COGS versus operating expense convention

> Northlake uses the following classification consistently across actuals, budget, forecast,
> management reporting, and channel profitability analysis.
>
> #### Included in COGS
>
> **1. Landed product cost** — supplier product cost, inbound freight, import duty and customs.
> These costs are capitalised into inventory and released to COGS when the related units are
> sold.
>
> **2. Outbound shipping** — outbound freight paid by Northlake to deliver customer orders is
> included in COGS. For DTC this includes parcel-carrier charges net of any carrier credits.
> For wholesale this includes freight paid by Northlake where the contractual shipping terms
> make Northlake responsible for delivery.
>
> Customer-paid DTC shipping is recorded separately as shipping revenue and is not netted
> against outbound freight expense.
>
> This means free-shipping promotions reduce shipping revenue and/or increase the amount of
> freight absorbed by Northlake, making their gross-margin impact visible.
>
> **3. Fulfilment expense** — third-party fulfilment costs directly associated with processing
> customer orders: pick-and-pack fees, per-order handling charges, packaging materials,
> variable warehouse handling, and other transaction-based 3PL charges.
>
> Storage fees, fixed warehouse retainers, and other costs that do not vary directly with orders
> are classified in operating expenses.
>
> #### Included in operating expenses
>
> **Payment processing fees** — credit-card and ecommerce payment-processing fees are classified
> as a variable selling expense within Sales & Marketing rather than COGS.
>
> These fees are directly related to DTC revenue, but Northlake does not include them in
> reported gross margin. They are included in DTC contribution margin and customer-acquisition
> economics.
>
> This creates a reporting hierarchy of:
>
> Revenue
> Less product and landed cost
> Less outbound shipping
> Less variable fulfilment
> = **Gross Profit**
>
> Less payment processing
> Less variable marketing / acquisition spend
> Less other channel-variable selling costs
> = **Contribution Profit**
>
> Less fixed operating expenses
> = **EBITDA / Operating Profit**
>
> #### Rationale
>
> The purpose of reported gross margin is to show the economic cost of producing and physically
> fulfilling the products Northlake sells.
>
> Outbound shipping and transaction-based fulfilment are therefore treated as costs of
> delivering the product to the customer.
>
> Payment processing is treated as a selling-channel cost because it arises from the method of
> customer payment rather than from manufacturing, sourcing, inventory, or physical fulfilment.
>
> The classification is held constant across historical and forecast periods so changes in gross
> margin reflect genuine changes in channel mix, product mix, pricing, promotional discounting,
> landed cost, freight, and fulfilment efficiency.
>
> Management does not reclassify costs between COGS and operating expense to achieve a target
> gross-margin presentation.

**Downstream consequences:**

- The P&L has **three margin tiers**, not two: Gross Profit, Contribution Profit, EBITDA.
  Contribution Profit is where channel economics are actually compared, since payment
  processing and acquisition spend are overwhelmingly DTC costs.
- The COGS/opex split turns on **variability with order volume**, not on department. Variable
  3PL charges are COGS; the fixed 3PL retainer and storage fees are opex. The same 3PL invoice
  therefore splits across two lines, and the generator must produce it that way.
- Shipping revenue is gross, never netted against outbound freight — so a free-shipping
  promotion shows up on both sides and its margin cost is visible.
- Classification is frozen across historical and forecast periods, which is what makes the
  gross margin bridge attributable to real drivers rather than to reclassification.

> **ADR required.** The COGS boundary, with the rationale above and the rejected alternative
> (payment processing in COGS, which is the other common treatment and would narrow the
> reported DTC/wholesale margin gap further).

### Q12b. Shipping, fulfilment and payment-processing economics

Recorded in condensed form; the full answer gives ranges and planning cases as well as the
base rates below.

**DTC outbound parcel cost** — $7.25 per order blended (ground, zone mix, dimensional weight,
residential surcharges, occasional expedited). Peak-period assumption $7.60–$7.90; long-term
efficiency target ~$7.00 via carrier negotiation and shipment consolidation. Recorded gross in
COGS, before customer shipping revenue. Multi-unit orders are more efficient per unit.

**DTC shipping revenue** — ~35% of orders pay shipping, at ~$6.95 each; the other 65% clear the
~$75 free-shipping threshold, receive a promotional waiver, or hold a loyalty benefit. Blended
**~$2.43 per DTC order**, recorded separately from the $78 merchandise AOV. The paying share
falls materially during BFCM and holiday campaigns.

**Variable fulfilment** —
DTC $3.25 per order (pick-and-pack $2.20, packaging $0.70, handling/consumables $0.35).
Wholesale $4.25 per carton (~12 units, varies by SKU) plus ~$18 per pallet for preparation,
wrapping, labelling and handling — roughly **$0.35–$0.45 per wholesale unit** before pallet
handling. Fixed 3PL storage and account-management charges are excluded and sit in opex.

**Wholesale outbound freight** — ~35% of wholesale revenue ships on Northlake-paid terms; the
other ~65% is retailer collect, customer-routed, or moved under retailer routing guides.
Channel-wide, Northlake-paid outbound freight is **~1.8% of net wholesale revenue**, which is
~5% on the shipments Northlake actually pays for. Large national accounts are the most likely
to control routing, which lowers direct freight expense but generates compliance costs,
chargebacks, detention/appointment fees and non-compliance deductions. Those deductions stay
separate from outbound freight so logistics execution problems remain visible.

**Payment processing** — ~2.9% of gross customer payments, all-in (percentage fees, fixed
per-transaction charges, payment-method mix, minor leakage). Classified below gross profit as a
variable selling expense. Base 2.9%, upside 2.7%, downside 3.1%.

**Resulting channel economics, as given:** DTC gross margin in the mid-50s before the returns
reserve and mix effects; wholesale ~37–39%; sustainable channel gap ~16–18 points rather than
the ~27 points implied by product cost alone.

**Verification** (derived; the stated economics reconcile):

*Superseded — the table below is stated **pre-returns** and does not reconcile to the P&L. It is
retained because it is what the answer as given implies, and because the gap between the two
versions is itself the finding. The corrected post-return figures follow.*

| Per DTC order (pre-return) | | Per wholesale unit (pre-return) | |
|---|---|---|---|
| Merchandise revenue | $78.00 | Net revenue | $25.10 |
| Shipping revenue | $2.43 | | |
| **Total revenue** | **$80.43** | **Total revenue** | **$25.10** |
| Landed cost (1.7 × $15) | $25.50 | Landed cost | $15.00 |
| Outbound parcel | $7.25 | Outbound freight (1.8%) | $0.45 |
| Variable fulfilment | $3.25 | Variable fulfilment | $0.45 |
| **Gross profit** | **$44.43** | **Gross profit** | **$9.20** |
| **Gross margin** | **55.2%** | **Gross margin** | **36.7%** |

Pre-return channel gap 18.5 points, at the top of the stated 16–18 range.

**Corrected, post-return** — returns reduce revenue *and* restore recoverable units to inventory at
cost, so both sides of the margin move:

| Per DTC order | | Per wholesale unit shipped | |
|---|---|---|---|
| Merchandise revenue, net of discount | $78.00 | Gross billings | $26.26 |
| Less returns | ($5.46) | Less deductions (3.0% of gross) | ($0.79) |
| Plus shipping revenue | $2.43 | Less returns (1.5% of net) | ($0.38) |
| **Net revenue** | **$74.97** | **Net revenue** | **$25.10** |
| Product cost, net of recoveries | ($24.07) | Product cost, net of recoveries | ($14.89) |
| Outbound parcel | ($7.25) | Outbound freight | ($0.45) |
| Variable fulfilment | ($3.25) | Variable fulfilment | ($0.45) |
| **Gross profit** | **$40.40** | **Gross profit** | **$9.31** |
| **Gross margin** | **53.9%** | **Gross margin** | **37.1%** |

**Channel gap 16.8 points**, inside the stated 16–18 range rather than at the top of it. Blended
gross margin **47.0% before shrink, 46.7% after**.

**Downstream consequences:**

- Parcel cost is per *order*, fulfilment is per *order* for DTC but per *carton and pallet* for
  wholesale. The generator needs carton quantities and pallet builds, not just units.
- Freight terms are an **account attribute** (Northlake-paid vs collect/routed), not a channel
  constant. The ~35%/65% split is what makes wholesale freight look cheap in aggregate while
  costing ~5% on the shipments it applies to.
- Promotions move four things at once and in conflicting directions: order volume up,
  merchandise ASP down, shipping revenue down, outbound freight up. The generator must produce
  all four effects together in November and December, not just a revenue spike.
- Payment processing at 2.9% of gross payments is ~2.8 points of DTC contribution margin, which
  is why the contribution tier exists.

### Q12c. Revenue basis (clarification)

Adding shipping revenue to $6.25M of DTC merchandise gives $6.44M, which overshoots the $10.6M
headline — so the channel figures and the headline could not both be on the same basis. Put as
options rather than resolved by assumption. Chosen:

- **$10.6M is reported net revenue**: merchandise net of discounts, less returns, plus shipping
  revenue. This is the income statement top line and is consistent with the ASC 606 treatment
  at Q10a.
- **The 41% wholesale share is measured on net revenue after deductions**, so the ~$4.35M is
  already net of contractual discounts, co-op, markdown allowances and chargebacks.

**Revised FY2025 DTC build** (supersedes the ~80,100 order figure derived at Q8a):

| | |
|---|---|
| Merchandise revenue, net of discounts, before returns | ~$6.50M |
| Less returns (7%) | ~($0.46M) |
| Plus shipping revenue (~$2.43/order) | ~$0.20M |
| **Reported DTC net revenue** | **~$6.25M** |
| **Orders** | **~83,400** |
| Units (1.7/order) | ~142,000 |

Wholesale at ~$25.10 net per unit gives ~173,000 units; gross billings before deductions and
returns are ~$4.55M. Total reported revenue $6.25M + $4.35M = **$10.60M**, which ties.

**Open detail for the data contract:** whether returns are computed before or after wholesale
deductions changes the gross-to-net ladder by a few basis points. To be fixed as an explicit
ordering in the contract rather than left to implementation.

### Q13. Supplier lead times, MOQs, and purchase-order timing

> Northlake sources most finished goods from overseas contract manufacturers, primarily in Asia.
>
> Typical end-to-end supplier lead times are:
>
> * Production lead time: **45–60 days**
> * Quality inspection / export preparation: **5–10 days**
> * Ocean freight and port-to-warehouse transit: **25–35 days**
> * Total normal replenishment lead time: approximately **80–100 days**
>
> For planning purposes, Northlake assumes a standard lead time of approximately **90 days**
> from purchase-order placement to inventory becoming available for sale.
>
> Lead times are longer for new product launches, custom colours, new packaging formats, first
> production runs, and periods surrounding Lunar New Year or other supplier-capacity
> constraints. New launches can require **120–150 days** from final product approval to
> inventory receipt.
>
> #### Minimum order quantities
>
> * Core drinkware: **1,000–1,500 units per SKU / colour**
> * Food storage: **800–1,200 units**
> * Accessories and replacement parts: **500–1,000 units**
> * Custom seasonal colours / limited editions: typically **1,500–2,500 units**
>
> Suppliers may allow Northlake to combine multiple colours or related SKUs within a broader
> production run, but this generally requires a minimum total factory commitment.
>
> Higher-volume hero SKUs are routinely ordered well above MOQ because of predictable demand and
> freight efficiency. The MOQ constraint is more significant for new or seasonal SKUs, where
> Northlake must commit inventory before actual consumer demand is known.
>
> #### Purchase-order timing
>
> Northlake typically places purchase orders approximately **three to four months ahead of
> expected sell-through**.
>
> Core replenishment POs are raised monthly using a rolling inventory plan based on forecast
> unit demand, current inventory, open purchase orders, safety stock, supplier lead time, and
> target weeks of supply.
>
> Seasonal and launch inventory is committed earlier:
>
> * Holiday / BFCM inventory: initial POs typically placed **May–July**
> * Spring launches: initial POs typically placed **October–December of the prior year**
> * Fall launches: initial POs typically placed **April–June**
>
> Purchase commitments are therefore partially locked before management has full visibility into
> the corresponding sales period.
>
> #### Forecasting convention
>
> The purchasing model should calculate required purchase orders as forecast demand, plus target
> ending inventory / safety stock, less beginning inventory, less open confirmed purchase
> orders, giving **required new purchases**.
>
> However, purchase orders cannot be generated as a perfectly flexible balancing item.
>
> The model must incorporate supplier lead times, SKU-level MOQ constraints, order-rounding,
> existing committed POs, and seasonal ordering cut-off dates.
>
> Once a purchase order has passed the supplier's cancellation or production-commitment point,
> the base forecast should treat the units as committed inventory even if the sales forecast
> subsequently declines.
>
> This is important to Northlake's economics because forecast misses can create excess inventory
> several months after management first sees demand weakening.

**Downstream consequences:**

- Purchasing is a **constrained, lumpy process**, not a smooth balancing figure. MOQ rounding,
  a 90-day lead time and a cancellation cut-off give the inventory module step behaviour, and
  the model must reproduce it rather than solving for a frictionless ending balance.
- A purchase order needs a **state machine**: raised → confirmed → past cancellation point →
  in transit → received. Only the pre-cancellation states are flexible in a reforecast.
- This is the mechanism behind the Q6 launch failure and it is arithmetically forced, not a
  narrative overlay. Spring 2025 launch POs were placed **October–December 2024**; demand
  weakness was visible **April–June 2025**; committed units continued arriving afterwards.
  The H2 2025 aged-inventory build follows from the lead time, and the data will show it.
- Lead time varies by SKU lifecycle state (90 days replenishment, 120–150 days for a first
  production run), so lifecycle state earns its place as a dimension attribute.

### Q14. Inventory targets, safety stock, stockouts, and obsolescence

> Northlake manages inventory using a combination of **inventory turns, weeks of supply, SKU
> velocity, and service level** rather than one company-wide inventory target.
>
> #### Inventory turns
>
> Long-term target approximately **4.0x–4.5x** annual inventory turns. FY2025 actual declined to
> approximately **3.3x**, versus approximately **4.1x in FY2024**.
>
> The deterioration was primarily driven by excess inventory from the underperforming
> food-storage launch, larger wholesale inventory commitments, slower sell-through of seasonal
> colours, and purchases placed before demand softened.
>
> Near-term objective is to recover to approximately **3.8x turns in FY2026**, with a
> longer-term target above **4.0x**.
>
> Inventory turns should be calculated using average inventory at landed cost rather than retail
> value.
>
> #### Safety stock
>
> **A — Hero / core SKUs.** ~55% of revenue. Target safety stock **5–6 weeks** of forecast
> demand. Highest service-level priority, replenished continuously.
>
> **B — Core secondary SKUs.** ~30% of revenue. Target safety stock **3–4 weeks**. Replenished
> regularly, but with tighter MOQ discipline.
>
> **C — Seasonal / long-tail SKUs.** ~15% of revenue. Target safety stock **0–2 weeks**. Often
> purchased as finite seasonal runs rather than continuously replenished.
>
> Safety stock is held in addition to inventory required to cover the approximately 90-day
> supplier lead time.
>
> Northlake does not attempt to maintain the same service level across the full catalogue
> because doing so would create excessive working-capital requirements.
>
> #### Stockouts
>
> Northlake does experience stockouts despite carrying excess inventory in aggregate.
>
> During FY2025, approximately **4% of potential DTC demand on hero SKUs was affected by
> temporary stockouts**, concentrated in several high-volume drinkware colours and sizes. Most
> stockouts lasted between **one and three weeks**.
>
> Only part of affected demand is permanently lost — customers may purchase another colour,
> select a substitute SKU, wait for replenishment, or purchase through a wholesale partner. For
> planning purposes, approximately **50% of stockout demand is assumed to be lost**, with the
> remainder substituted or deferred.
>
> Stockout impact should therefore be modelled separately from underlying demand so that poor
> availability is not mistaken for weaker consumer demand.
>
> #### Aged and obsolete inventory
>
> Inventory ageing is reviewed monthly: 0–180 days current; 181–270 days watch list; 271–365
> days aged; more than 365 days potential obsolescence.
>
> Management actions for aged inventory include targeted DTC promotion, bundle offers, wholesale
> clearance programmes, outlet / off-price sales, and SKU discontinuation.
>
> Normal annual inventory shrink, damage, and obsolescence is approximately **1% of average
> inventory cost**. FY2025 was elevated to approximately **2.5%** because of the underperforming
> food-storage launch and slower-moving seasonal inventory.
>
> Northlake maintains an inventory reserve based on SKU-level age, expected future selling price,
> and estimated recovery value. Indicative reserve rates: current 0%; 181–270 days 10%; 271–365
> days 25%; more than 365 days 50%–100% depending on expected recoverability.
>
> Inventory is written down when estimated net realisable value falls below landed cost.
>
> #### Planning convention
>
> The model should distinguish between healthy inventory required to support forecast demand,
> safety stock, committed inbound inventory, excess inventory, aged inventory, and inventory at
> risk of write-down.
>
> Management's objective is not simply to minimise inventory. The operating goal is to improve
> inventory turns **without materially increasing stockouts on hero SKUs**.

**Verification** (derived, re-checked post-return): 315,030 units shipped less 9,237 recovered to
inventory gives 305,793 units charged to COGS at $15 landed, or **$4.587M**. At 3.3x turns, average
inventory is **~$1.390M** (111 days on hand). FY2024 at ~4.1x on ~$4.0M landed COGS implies
**~$0.98M** (89 days). The **~$400k inventory build** is the working capital half of the Q5 tension,
and it is large relative to the business's cash generation. **This figure is unchanged by the
post-return restatement** — turns are computed on landed cost, which the restatement does not move.

**Return write-offs are separate from shrink.** Non-recoverable returned units are 1,984 DTC and
1,300 wholesale, **$49.3k at landed cost — 3.5% of average inventory**, which already exceeds the
2.5% FY2025 shrink rate on its own. The 1% / 2.5% rates therefore cannot be inclusive of return
write-offs; the two are separate charges to COGS, driven by inventory held and by return volume
respectively.

**Downstream consequences:**

- **SKU class (A/B/C) is a dimension attribute**, driving safety stock weeks, replenishment
  policy and reserve behaviour. The 55/30/15 revenue split maps onto the Q3 concentration
  figures and must be consistent with them.
- **Stockouts are modelled as a separate suppression layer on top of demand**, with a 50% loss
  and 50% substitution/deferral assumption. Realised revenue is therefore not the same as
  underlying demand, and the generator must carry both so availability problems are not
  misread as weak demand. This is unusual and is worth surfacing in the board pack.
- **Inventory ageing buckets and reserve rates are explicit**, so the reserve is computed from
  SKU-level age rather than applied as a percentage. This needs inventory held at cost layer /
  receipt-date granularity, not just a running balance.
- Shrink runs at 1% of average inventory normally and 2.5% in FY2025 — a modelled step, not a
  constant.
- Hero SKUs stock out at peak while the long tail ages simultaneously. The inventory policy must
  reproduce both at once; a single company-wide weeks-of-supply target cannot.

## E. Working capital

### Q15. DTC cash timing and payment processor settlement

> Northlake's DTC sales are collected primarily through credit cards and digital wallets. Cash
> is not received on the same day the customer places the order.
>
> The standard settlement assumption is:
>
> * Average payment processor settlement lag: **2 business days**
> * Weekend / holiday sales settle on the next available banking day
> * Chargebacks and refunds are deducted from subsequent processor settlements
>
> For planning purposes, Northlake uses a blended **3 calendar day cash-conversion lag** from DTC
> sale to cash receipt.
>
> The model should therefore distinguish between DTC revenue recognition, processor receivables
> / unsettled cash, and actual cash receipts.
>
> At month end, Northlake carries a small payment-processor receivable representing sales already
> recognised but not yet deposited into the bank account.
>
> Because the settlement cycle is short, this balance is not a major working-capital driver under
> normal conditions. However, the balance becomes more visible during Black Friday / Cyber
> Monday, holiday weekends, month-end promotional events, and periods of unusually high refund
> activity.
>
> Payment processor timing should therefore be modelled explicitly rather than assuming all DTC
> revenue converts to cash immediately.
>
> For the base case, use:
>
> * Standard settlement lag: **2 business days**
> * Planning equivalent: **3 calendar days**
> * No material bad debt on DTC transactions
> * Chargebacks treated separately from ordinary customer returns

**Downstream consequences:**

- A **processor receivable** is a distinct balance sheet line between revenue and cash, not an
  aggregation into trade receivables. At ~$17k/day of DTC revenue the normal balance is ~$50k,
  rising materially around BFCM — small, but it moves in step with everything else, which is
  what makes it worth modelling rather than assuming away.
- No rolling processor reserve or holdback, and no material DTC bad debt. DTC credit risk is
  therefore not modelled.
- Chargebacks are separate from ordinary returns, so the two cannot share a driver.
- The 2-business-day / 3-calendar-day distinction means the date spine needs a **banking day
  calendar**, not just calendar dates, if settlement is modelled at daily grain.

---

### Q16. Wholesale receivables, payment terms, DSO, and bad debt

> Northlake's wholesale customers purchase on credit terms rather than paying at shipment.
>
> Typical contractual payment terms:
>
> * Small independent accounts: **Net 30**
> * Regional chains: **Net 45**
> * Large national accounts: **Net 60**
>
> A small number of strategic accounts have negotiated terms extending to approximately **Net
> 75**, particularly where Northlake participates in larger seasonal programmes.
>
> Actual cash collection is slower than the contractual terms suggest. FY2025 actual wholesale
> DSO is approximately **52 days**.
>
> Indicative DSO by account group:
>
> * Small independent accounts: **35–40 days**
> * Regional chains: **45–50 days**
> * Large national accounts: **60–65 days**
>
> The difference between stated terms and actual collection is driven by retailer payment
> cycles, invoice matching delays, disputed deductions, chargebacks, proof-of-delivery
> requirements, and occasional short-pays that require manual resolution.
>
> Large customers generally have low credit risk but can be operationally slow to pay because
> deductions and claims delay invoice settlement.
>
> #### Bad debt
>
> Normal bad-debt expense is approximately **0.4% of wholesale net revenue**.
>
> Most write-offs arise from smaller independent retailers, business closures, disputed balances
> that become uneconomic to pursue, and occasional insolvencies. Large national accounts are
> assumed to have minimal default risk.
>
> Northlake maintains an allowance for doubtful accounts based on account credit quality,
> receivable ageing, historical collection experience, specific known disputes, and customer
> financial condition.
>
> Indicative ageing categories: current 0–30 days; 31–60 days past due monitor; 61–90 days past
> due elevated collection focus; more than 90 days past due specific reserve review.
>
> #### Forecasting convention
>
> Wholesale cash receipts should be modelled separately from revenue recognition, using
> account-specific contractual terms for major customers, historical actual payment behaviour,
> and a blended DSO assumption for the long-tail customer base.
>
> For company-level planning: FY2025 actual DSO **52 days**; base forward **50 days**; downside
> **58–60 days**; upside / collections-improvement **45–47 days**.
>
> Bad debt should be forecast separately from DSO rather than embedded in the collection lag.
>
> The increase in wholesale mix therefore creates a structural increase in accounts receivable
> even when customers remain creditworthy.

**Verification** (derived): $4.35M wholesale net revenue at 52 days DSO gives **~$620k** of
wholesale receivables. At FY2023 wholesale of $2.27M and comparable terms the balance would have
been ~$300k. Together with the ~$400k inventory build at Q14, the channel mix shift has absorbed
roughly **$720k of working capital** in a $10.6M-revenue business. This is the Q5 tension stated
in cash rather than in narrative.

**Downstream consequences:**

- **Payment terms are an account attribute; realised DSO is a separate behavioural attribute.**
  The gap between them (Net 60 stated vs 60–65 days actual on national accounts) is caused by
  deduction disputes and short-pays, so collection lag must be modelled as terms plus a
  behavioural delay, not as terms alone.
- Deductions therefore appear **twice** in the model: as contra-revenue at Q9, and as a cause of
  collection delay here. A short-paid invoice stays open until reconciled.
- Bad debt is forecast separately from DSO and is concentrated in the long tail, so credit risk
  is an attribute of account tier — inverted relative to deduction risk, which concentrates in
  the largest accounts.
- Receivables ageing buckets are explicit, so AR needs invoice-level granularity with an
  open/settled state, not a period-end balance derived from a DSO ratio.


### Q17. Supplier payment terms and PO deposits

> Northlake's supplier terms vary by supplier maturity, product type, and whether the order is
> standard replenishment or a new/custom production run.
>
> For established core suppliers, the standard arrangement is **30% deposit at purchase-order
> confirmation, 70% balance due 30 days after shipment**.
>
> For the largest and longest-standing supplier relationships, some core replenishment orders
> have improved to **20% deposit at PO, 80% due 30 days after shipment**.
>
> New suppliers, first production runs, and highly customised seasonal products generally
> require less favourable terms: **50% deposit at PO, 50% prior to shipment**.
>
> Northlake does not generally receive full Net 60 or Net 90 unsecured supplier terms because the
> company is still relatively small and most production is made specifically for Northlake.
>
> #### Cash-flow consequence
>
> The deposit structure means a meaningful portion of inventory cash outflow occurs well before
> the related revenue is recognised. For a standard core purchase order:
>
> 1. Deposit is paid approximately **90 days before inventory is available for sale**
> 2. Remaining balance is paid approximately **30 days after shipment**
> 3. Inventory may then remain on hand for several weeks before being sold
> 4. Wholesale sales may not convert to cash for another **50+ days**
>
> This creates a significant cash-conversion cycle for wholesale-led growth.
>
> #### Planning convention
>
> The purchasing and cash-flow model should separate PO commitment date, deposit payment date,
> supplier shipment date, inventory receipt date, and final supplier payment date — rather than
> forecasting accounts payable simply as a fixed percentage of COGS.
>
> Supplier deposits are recorded as **prepaid inventory / supplier advances** until the related
> goods are received. Once goods are received, the deposit becomes part of inventory cost and any
> unpaid balance is recorded in accounts payable.
>
> #### Accounts payable profile
>
> Because deposits are common, reported accounts payable understates the total amount of cash
> Northlake has committed to future inventory.
>
> Management therefore monitors both recorded accounts payable and open purchase-order
> commitments, including deposits already paid and remaining contractual obligations.
>
> This distinction is important in the board cash forecast because Northlake can appear to have
> manageable AP while still carrying substantial future inventory commitments.

**Verification — effective DPO is negative** (derived, indicative):

On core 30/70 terms against a 90-day PO-to-availability lead time, with shipment at ~day 55 and
the balance due 30 days later at ~day 85:

| Payment | Timing vs inventory receipt | Weight |
|---|---|---|
| Deposit | 90 days **before** | 30% |
| Balance | 5 days **before** | 70% |
| **Weighted average** | **~30 days before receipt** | |

Northlake **funds its suppliers rather than being funded by them**, then carries ~111 days of
inventory and waits ~52 days for wholesale collection on top. On new-launch 50/50 terms the
position is worse still, since the entire balance is paid before shipment.

Indicative working capital at FY2025 levels: inventory ~$1.39M, receivables ~$0.67M, supplier
advances ~$0.37M, accounts payable ~$0.29M — roughly **$2.1M of net working capital on $10.6M of
revenue**, about 20% of revenue. (The processor receivable is $55k rather than the $51k first
derived, once DTC gross customer payments are taken as merchandise plus shipping. Immaterial to the
total.)

**Downstream consequences:**

- Accounts payable **cannot be forecast as a percentage of COGS**. It has to be built from
  purchase-order events, and the model must carry five distinct dates per PO (commitment,
  deposit, shipment, receipt, final payment).
- **Supplier advances are a balance sheet line** — prepaid inventory, not part of AP and not
  part of inventory until goods are received.
- **Open PO commitments are a disclosure, not just an internal control.** Reported AP understates
  committed cash, so the board pack needs a commitments note alongside the balance sheet or the
  cash position reads as healthier than it is.
- Supplier terms are an attribute of the **supplier–product relationship**, not a company
  constant: three distinct term structures (20/80, 30/70, 50/50) apply by supplier maturity and
  order type. New launches carry the worst terms *and* the longest lead times *and* the highest
  MOQ risk — the same combination that produced the Q6 launch failure.


## F. Operating expenses

### Q18. Marketing spend, channel mix, and planning treatment

> Northlake's FY2025 marketing spend is approximately **$1.45M**, equivalent to approximately
> **13.7% of total company net revenue** and approximately **23% of DTC net revenue**.
>
> Marketing is primarily used to support DTC demand generation rather than wholesale acquisition.
>
> #### Marketing spend mix
>
> Approximately **68% paid / performance-oriented**, **32% owned, retention, brand and
> supporting activity**. Indicative FY2025 mix: paid social 38%; paid search / shopping 15%;
> affiliate and creator acquisition 8%; retargeting / other paid digital 7%; email / SMS /
> loyalty 7%; organic content and social 5%; creative production 8%; brand partnerships / PR /
> seeding 6%; testing, tools and other 6%.
>
> November and December carry significantly higher paid-media spend.
>
> #### Performance marketing treatment
>
> Performance marketing is **not managed as a fixed percentage of revenue**. Northlake sets a
> quarterly spending envelope, but paid acquisition is released or reduced based on customer
> economics. The primary management metric is **new-customer CAC**, supported by
> contribution-margin and payback analysis.
>
> FY2025 baseline economics:
>
> * Blended paid new-customer CAC: **$34**
> * FY2024 comparable CAC: approximately **$29**
> * Management target range: **$30–$33**
> * Downside threshold requiring intervention: **>$38**
> * Target first-order contribution payback: **within 12 months**
>
> As paid-media spend increases, marginal acquisition efficiency generally deteriorates. The
> forecast should therefore use a **response curve or tiered CAC assumption** rather than a simple
> linear `marketing spend × fixed ROAS = revenue`.
>
> #### New versus repeat customer economics
>
> Paid marketing is primarily used to acquire new customers. Repeat revenue is driven more
> heavily by existing customer cohorts, email and SMS, organic traffic, product launches,
> replenishment / replacement behaviour, referrals, and promotional reactivation.
>
> Northlake tracks new customers, repeat customers, paid CAC, blended CAC, repeat purchase rate,
> AOV, and contribution margin by customer type.
>
> #### Owned and retention marketing
>
> Email, SMS, loyalty and organic channels are not treated as free — their direct platform,
> agency, creative and programme costs remain within marketing expense. But management does not
> assign a conventional acquisition CAC to them, because much of the activity monetises the
> existing base rather than acquiring new customers.
>
> The strategic objective is to increase the share of DTC revenue from repeat and owned-channel
> customers, reducing dependence on increasingly expensive paid acquisition.
>
> #### Planning convention
>
> **Variable performance marketing** (paid social, paid search, affiliate, creator, retargeting)
> is driven by new-customer targets, CAC assumptions, the promotional calendar, channel
> saturation, and management efficiency thresholds.
>
> **Semi-fixed / planned marketing** (creative production, CRM / loyalty tools, PR, brand
> partnerships, content, baseline agency costs) is budgeted directly and steps periodically
> rather than flexing automatically with revenue.
>
> The base forecast should model **new customer demand × CAC = performance marketing
> requirement**, subject to a management spending ceiling and CAC efficiency constraint.
>
> If required spend exceeds the approved CAC threshold, the model should **reduce assumed
> new-customer acquisition rather than silently increasing marketing efficiency**.
>
> #### Management objective
>
> Return paid CAC toward the low-$30s; increase repeat purchase rate from ~29% into the
> low-to-mid 30% range; increase owned-channel contribution; grow DTC while maintaining
> acceptable contribution margin.
>
> This makes marketing a genuine economic driver rather than a plug used to force the revenue
> forecast to balance.

**Verification** (derived): performance marketing at 68% of $1.45M is ~$986k; at a $34 paid CAC
that implies **~29,000 paid-acquired new customers** in FY2025. CAC rising from $29 to $34 is a
**17% deterioration year on year** — the DTC half of the Q5 tension, and the reason wholesale
expansion is defensible rather than merely convenient.

**Downstream consequences:**

- Marketing splits into **two distinct behaviours** in the model: variable performance spend
  solved from a new-customer target and a CAC curve, and semi-fixed programme spend that steps.
  These cannot share a driver.
- The CAC response curve means marketing is **non-linear**, and the constraint runs the "wrong"
  way on purpose: when CAC breaches threshold the model cuts acquisition rather than improving
  assumed efficiency. That is what stops marketing becoming a balancing plug.
- Acquisition channel is a **customer attribute** (already required by Q7 for repeat-rate
  variation) and now also drives CAC.
- Marketing is a DTC cost almost entirely, so it belongs in the contribution tier by channel —
  it is what makes wholesale contribution margin competitive with DTC despite the ~18-point
  gross margin gap.

> **ADR required.** Marketing as a constrained driver with a CAC response curve, rather than a
> percentage of revenue or a fixed-ROAS revenue driver.


### Q19. Headcount by function and scaling behaviour

> **Superseded in part by F2.** Year-end FY2025 headcount is **28 FTE**, not 31, and the history
> rebases to 22 / 25 / 28. The functional structure, hiring triggers and planning convention below
> stand unchanged. The answer is retained as given.

> Northlake had approximately **31 full-time employees at the end of FY2025**. Historical:
> FY2023 ~**25 FTE**; FY2024 ~**28 FTE**; FY2025 ~**31 FTE**.
>
> Because manufacturing and warehousing are outsourced, headcount grows materially slower than
> revenue.
>
> **FY2025 headcount by function:** Executive / People / Administration 3; Finance 3; Supply
> Chain / Operations 6; Product / Merchandising 5; Marketing / Ecommerce 7; Wholesale Sales /
> Account Management 4; Customer Experience 3. **Total 31 FTE.**
>
> **Executive / People / Admin (3)** — CEO, COO / operating lead, People / administration.
> Largely fixed at current scale. Next addition a dedicated senior People / HR role at
> approximately **40–45 employees**.
>
> **Finance (3)** — Controller / Head of Finance, Senior Accountant, FP&A / Finance Analyst.
> Supports monthly close, cash forecasting, inventory accounting, budgeting and forecasting,
> wholesale deductions, management reporting and board reporting. Next hire triggered at
> approximately **$14M–$16M of revenue**, or when transaction complexity or wholesale deductions
> and inventory accounting exceed existing capacity. That hire would be an additional accountant
> or AR / deductions specialist rather than another senior finance leader.
>
> **Supply Chain / Operations (6)** — Head of Supply Chain, demand / inventory planner,
> procurement / supplier manager, logistics coordinator, operations analyst, quality / product
> operations. Scales with active SKU count, supplier count, PO volume, wholesale complexity and
> inventory throughput. Next hire when active SKUs exceed approximately **100–110**, revenue
> exceeds approximately **$13M–$14M**, or PO and inbound shipment volume exceeds capacity.
>
> **Product / Merchandising (5)** — product / merchandising lead, product managers / developers,
> design / packaging, merchandising / assortment planning. Driven by assortment complexity and
> launch cadence rather than revenue. Additional role justified beyond approximately **110 active
> SKUs**, a major new category, or an expanded launch calendar.
>
> **Marketing / Ecommerce (7)** — head of marketing / ecommerce, performance marketing, CRM /
> retention, ecommerce merchandising, content / social, creative, marketing operations. Paid
> media can flex substantially without proportional internal headcount because agencies and
> freelancers are used. Base plan assumes one incremental hire only after DTC revenue reaches
> approximately **$7.5M–$8.0M**.
>
> **Wholesale Sales / Account Management (4)** — head of wholesale, 2 key / regional account
> managers, sales operations. Supports ~38 accounts. Coverage does not scale evenly by account
> count; the largest national retailers require disproportionately more time. New account manager
> triggered by another major national account, active accounts exceeding approximately **50**, or
> managers consistently carrying more than approximately **10–12 meaningful relationships each**.
> Smaller independents receive pooled coverage.
>
> **Customer Experience (3)** — DTC order enquiries, returns, replacements, product questions,
> service recovery. Driven by DTC order volume rather than total revenue. At approximately
> **83,000–84,000 FY2025 DTC orders** the three-person team is adequate with seasonal support.
> Temporary or outsourced coverage is used in November and December rather than carrying peak
> staffing year-round. Permanent additional hire once annual DTC orders sustainably exceed
> approximately **100,000–110,000**.
>
> #### Headcount planning convention
>
> The forecast should **not** calculate payroll as a constant percentage of revenue.
>
> Each position should instead have function, role, start date, annual salary, benefits /
> payroll burden, bonus assumption where applicable, vacancy status, and hiring trigger.
>
> Existing employees remain fixed unless an explicit departure or restructuring is modelled. New
> hires are activated when predefined operating thresholds are reached: DTC order volume → CX;
> wholesale accounts → account management; SKU count / PO complexity → supply chain; revenue and
> transaction complexity → finance; new categories / launches → product; DTC scale and channel
> expansion → marketing.
>
> The base forecast therefore produces periods where revenue grows without additional headcount,
> followed by discrete increases in payroll when capacity thresholds are crossed.
>
> Temporary labour, agencies and contractors are modelled separately from permanent FTE so the
> business can absorb seasonal peaks without assuming permanent staffing at peak demand levels.

**Downstream consequences:**

- Payroll is built from a **position-level roster**, not a ratio. Each row carries a start date,
  salary, burden, bonus and a hiring trigger; the roster is a modelled input in its own right.
- **Hiring triggers are operational, not financial**, for most functions — SKU count, PO volume,
  DTC orders, managed account count. Those operating metrics must therefore be first-class model
  outputs, not just reporting views, because payroll depends on them.
- Revenue per FTE moves from $324k (FY2023) to $342k (FY2025) — modest operating leverage,
  consistent with an outsourced manufacturing and warehousing model.
- Seasonal CX cover is contractor spend, modelled separately from FTE, so November and December
  opex steps without permanent headcount.


### Q20. Fixed cost base

> Northlake operates an outsourced logistics model and does not own or operate its own
> warehouse. Variable pick-and-pack and transaction-based fulfilment charges are classified in
> COGS under the convention established in Q12.
>
> **3PL fixed and storage costs** — approximately **$18,000–$22,000 per month**: warehouse
> storage, account-management fees, technology / integration fees, receiving minimums,
> cycle-count support, and other non-transactional warehouse charges. Storage expense increases
> when inventory levels materially exceed target, so the cost is not perfectly fixed. Base
> planning assumption **$19,000 per month**; storage surcharge driven by average pallet / cubic
> volume; peak-season incremental capacity charges modelled separately in Q4 and Q1. FY2025
> elevated inventory therefore increased storage expense even though unit sales did not increase
> proportionately.
>
> **Office and corporate facilities** — approximately **$150,000 annually** (rent, utilities,
> insurance, maintenance, basic office services). Sufficient until headcount reaches
> approximately 40–45 employees. No major expansion in the near-term base case.
>
> **Software and technology** — approximately **$280,000 annually**: ecommerce platform and
> applications, ERP / accounting, inventory and demand planning, CRM / email / SMS, BI and
> reporting, collaboration, cybersecurity, general corporate SaaS. Core fixed base ~**$225,000**;
> variable / usage-based ~**$55,000** at FY2025 scale. Steps upward at higher pricing tiers or
> new system implementations rather than scaling smoothly.
>
> **Professional fees** — approximately **$210,000 annually**: audit and accounting support, tax,
> legal, insurance advisory, regulatory / compliance, specialist consulting. Budgeted by contract
> or expected engagement rather than as a percentage of revenue; legal and consulting carry a
> modest contingency.
>
> **Insurance** — approximately **$95,000 annually**: general liability, product liability, D&O,
> cyber, property / inventory, other corporate policies. Relatively fixed within the current
> revenue range; steps with higher insured inventory, larger wholesale exposure, international
> expansion, and company scale.
>
> **Other corporate and administrative** — approximately **$180,000–$220,000 annually**: board
> and governance, travel not directly tied to sales, bank charges, recruitment, training, office
> supplies, subscriptions, general administrative.
>
> #### Fixed-cost planning convention
>
> Not modelled as a constant percentage of revenue. Each major cost is classified as **fixed**
> (office rent, core software licences, recurring insurance, audit retainers, base 3PL account
> fees), **step-fixed** (software pricing tiers, warehouse storage capacity, additional office
> space, insurance coverage levels, major professional-service needs), or **directly budgeted**
> (legal, consulting, recruitment, major technology projects, board / governance spend).
>
> The model should allow revenue to grow for periods without a corresponding increase in fixed
> overhead, followed by discrete cost steps when operational thresholds are reached. This
> operating leverage is an important part of Northlake's path to improved EBITDA margin.
>
> Management's objective is to grow revenue faster than the fixed corporate cost base while
> avoiding underinvestment in systems, planning capability, and supply-chain control.

**Fixed cost base total** (derived): ~**$1.16M annually** — 3PL $228k, office $150k, software
$280k, professional fees $210k, insurance $95k, other corporate ~$200k.

**Downstream consequences:**

- Three cost behaviours (fixed / step-fixed / directly budgeted) is a **classification attribute
  on the account**, so operating leverage emerges from the structure rather than being asserted.
- 3PL storage is **driven by inventory volume, not by sales**, which is the second-order cost of
  the Q14 inventory build: FY2025 carried higher storage expense on flat unit throughput. That
  link must exist in the model or the inventory story loses a consequence.
- Software splits fixed (~$225k) from usage-based (~$55k), so it cannot be a single line.


### Q20a. FY2025 EBITDA and payroll level (raised, not in the script)

Q19 specified the headcount roster and its hiring triggers but not compensation, and Q20 gave
the fixed cost base. With gross margin, marketing and fixed costs known, EBITDA reduced to a
single unknown, so it was put as options rather than defaulted.

**Bridge to the fork:**

| FY2025 | $M |
|---|---|
| Net revenue | 10.60 |
| Gross profit @ 47.6% blended *(pre-return basis — superseded, see below)* | 5.05 |
| Payment processing (2.9% of DTC gross payments) | (0.19) |
| Marketing | (1.45) |
| Fixed cost base | (1.16) |
| Bad debt (0.4% of wholesale net revenue) | (0.02) |
| **Available for payroll and EBITDA** | **2.23** |

**Chosen: loss-making, approximately $(600)k to $(900)k, or −6% to −8% of revenue.**

Anchored at a payroll cost of **~$2.98M**:

- **FY2025 EBITDA ~$(859)k, −8.1% of net revenue** *(restated)*

*The bridge above used a pre-return gross margin of 47.6%, which does not reconcile to a P&L stated
net of returns. On the corrected post-return basis blended gross margin is 47.0% before shrink and
46.7% after, giving:*

| FY2025, restated | $M |
|---|---|
| Net revenue | 10.600 |
| Gross profit before shrink @ 47.0% | 4.981 |
| Shrink and obsolescence (2.5% of average inventory) | (0.035) |
| **Gross profit @ 46.7%** | **4.947** |
| Payment processing | (0.194) |
| Marketing | (1.450) |
| Payroll | (2.981) |
| Fixed cost base | (1.163) |
| Bad debt | (0.017) |
| **EBITDA** | **(0.859)** |
| **EBITDA margin** | **(8.1%)** |

*This sits marginally outside the −6% to −8% band described when the option was chosen, though
comfortably inside the $(600)k–$(900)k dollar range. The payroll anchor, headcount, cost base and
revenue are all unchanged; only the margin basis was wrong.*

*(The headcount this is spread across was revised from 31 to 28 FTE at F2, holding the payroll
anchor constant. Average fully-loaded compensation is therefore **~$106,500**, not the ~$96,000
first derived here. EBITDA is unaffected.)*

Rejected: breakeven (~$71–78k loaded comp — plausible but a weaker story), and modestly
profitable (~$58–61k loaded comp — low for a team carrying a CEO, COO, Controller and three
function heads, and a figure a reviewer would question).

**Why this matters beyond the P&L.** A business losing ~$750k while absorbing ~$720k of
incremental working capital consumes roughly $1.5M of cash in FY2025. It therefore requires
external financing, which:

- makes the capital structure a required input rather than an afterthought (see open items);
- makes **ADR 0001 load-bearing** — beginning-of-period interest on a real revolver balance,
  rather than an academic convention on an empty debt line;
- gives the board pack genuine stakes. The Q5 trade-off is not a margin optimisation question,
  it is a funding question.


## G. Structure and planning

### Q21. Chart of accounts, departments, entity, currency, and fiscal year

> **Legal entity and currency.** One legal entity; functional and reporting currency **USD**; no
> consolidation requirement; no foreign subsidiaries. **Fiscal year end December 31**, 12 calendar
> months January through December.
>
> Northlake purchases inventory from overseas suppliers and therefore incurs some supplier
> invoices and freight charges denominated in foreign currencies, but those transactions are
> translated into USD within the single legal entity. Foreign exchange exposure should be
> retained where relevant to purchasing and landed cost, but the FP&A model does not require
> multi-entity consolidation or a separate reporting-currency layer.
>
> **Chart of accounts** — approximately **135 active GL accounts**: cash, receivables, inventory,
> prepaids and other assets ~20; payables, accruals, refund liabilities and other liabilities
> ~15; equity ~5; revenue and contra-revenue ~15; product COGS, freight and fulfilment ~20;
> payroll and people costs ~15; marketing and selling ~20; technology, facilities, professional
> fees and G&A ~20; other income / expense, interest and tax ~5.
>
> Accounts map into a management reporting hierarchy: Net Revenue, COGS, Gross Profit, Sales &
> Marketing, Product / Merchandising, Operations / Supply Chain, Customer Experience, G&A,
> EBITDA, Other Income / Expense, Net Income.
>
> Revenue retains separate accounts for DTC merchandise revenue, wholesale merchandise revenue,
> DTC shipping revenue, DTC returns, wholesale returns, promotional discounts, co-op marketing
> deductions, markdown allowances, and chargebacks / compliance deductions.
>
> COGS separately identifies product cost, inbound freight, duty and customs, outbound parcel
> freight, wholesale outbound freight, DTC pick-and-pack, wholesale fulfilment, packaging,
> inventory write-downs, and shrink / damage.
>
> This allows the gross-to-net and gross-margin bridges to be constructed **from the ledger**
> without relying on manually calculated management adjustments.
>
> **Department / cost-centre structure** — a department dimension **in the general ledger**, not
> merely an FP&A reporting overlay. Nine operating cost centres: Executive / Corporate; Finance;
> People / Administration; Supply Chain / Operations; Product / Merchandising; Marketing /
> Ecommerce; Wholesale Sales; Customer Experience; Technology / Shared Services.
>
> Used for payroll coding, budget ownership, vendor expenses, monthly variance reporting,
> headcount planning, purchase approvals, and management accountability. Employees have a home
> department; shared vendor costs are coded directly to the benefiting department or retained in
> a defined shared-services cost centre.
>
> Northlake does **not** create a cost centre for every wholesale customer, marketing campaign,
> product family or SKU — those are separate analytical dimensions or operational fact tables.
>
> **Management dimensions** — Channel (DTC, Wholesale); Product (SKU, product family, category,
> core / seasonal, hero / long-tail); Wholesale customer (account, account tier, national /
> regional / independent); Marketing (channel, campaign, promotion, acquisition / retention);
> Department (cost centre, functional owner); Scenario (Actual, Budget, Latest Forecast, Base,
> Upside, Downside).
>
> **Department versus channel are deliberately separate concepts.** Marketing supports primarily
> DTC but incurs brand spend benefiting both; Supply Chain supports both; Wholesale Sales is a
> department while Wholesale is also a revenue channel; Finance and Executive are corporate and
> not naturally attributable to either channel. Channel contribution reporting therefore uses
> **explicit allocation rules** rather than assuming cost centre equals channel.
>
> **Planning convention.** Budget and forecast input is primarily owned at **GL account ×
> department × month × scenario**. Operational models generate or support selected financial
> lines at lower grain: revenue at SKU / channel / customer / month; marketing at campaign /
> acquisition channel / month; inventory at SKU / location / month; headcount at employee or role
> / department / month; wholesale deductions at account / deduction type / month. These schedules
> map back to the chart of accounts and departments for the financial statements.

**Downstream consequences:**

- This largely **specifies the star schema**: one GL fact at account × department × month ×
  scenario, plus operational fact tables at their own declared grains, joined through conformed
  dimensions. It answers much of Q23 in advance.
- **Scenario is confirmed as a dimension** with six members, consistent with the standing rule
  that scenario is never a separate table or a column suffix.
- The gross-to-net and margin bridges must be constructible **from ledger accounts alone**. That
  is a testable assertion, not a presentation preference, and it constrains the contra-revenue
  and COGS account design set out above.
- **Cost centre ≠ channel.** Channel contribution requires documented allocation rules, and those
  rules are a financial convention that needs stating explicitly in the data contract.
- Fiscal year end **December 31** confirmed; the date spine is calendar months.


### Q22. Budget process, reforecast cadence, and leadership scenarios

> Northlake uses a **hybrid driver-based budgeting process**. The annual budget is built bottom-up
> from operating assumptions but constrained by top-down financial targets approved by leadership
> and the board. Operating teams do not receive a revenue number and backsolve expenses to fit
> it, and finance does not accept an unconstrained departmental wish list. The process is
> iterative.
>
> **Annual budget process.** The FY2026 budget was prepared **September through November 2025**
> and approved by the board in December. Finance establishes the planning framework from
> prior-year actuals, current run-rate, known wholesale commitments, inventory position, existing
> POs, historical customer behaviour, headcount, contractual fixed costs and strategic priorities.
>
> *DTC* — Marketing and Ecommerce provide traffic, conversion, new customer acquisition, CAC,
> repeat purchase behaviour, promotional calendar, AOV, product launches and marketing spend.
> Finance challenges these against historical cohort economics and contribution margin.
>
> *Wholesale* — the Wholesale team builds an account-level forecast from confirmed POs, retailer
> forecasts, expected reorder rates, new-door expansion, prospective accounts, promotional
> programmes and account-specific deductions. Confirmed orders and existing customers receive
> higher confidence weighting than uncommitted pipeline.
>
> *Inventory and supply chain* — Supply Chain converts demand into SKU demand, replenishment,
> safety stock, POs, supplier deposits, inbound freight and receipts, constrained by MOQs, lead
> times, already-committed POs and supplier production windows.
>
> *Headcount and opex* — department leaders submit existing headcount, proposed hires,
> compensation changes, vendor contracts, discretionary projects and departmental spend. New
> hires require an explicit operating trigger or business case rather than a percentage of
> revenue.
>
> **Top-down financial guardrails.** The bottom-up plan is evaluated against four board-level
> constraints: revenue growth; gross margin; EBITDA / path to breakeven; and minimum liquidity and
> borrowing capacity. The plan is revised if operational assumptions produce acceptable revenue
> growth but unacceptable margin dilution, inventory build, cash burn or financing requirement —
> particularly important for wholesale, where a large opportunity can look attractive in revenue
> terms while creating significant inventory and receivables requirements.
>
> **Reforecast cadence.** A **monthly rolling forecast**, with a formal reforecast each quarter.
>
> *Monthly latest estimate* — after each close, finance updates the current-year forecast for
> actual sales, DTC trends, paid-media efficiency, wholesale POs, returns, inventory, open POs,
> headcount, major opex, AR collections and cash. It answers: **where are we currently expected
> to land if management makes no major strategic change?** Assumptions are not rebuilt from
> scratch each month; near-term months receive detailed updates while later months remain
> driver-based.
>
> *Quarterly reforecast* — a full operating reforecast refreshing DTC acquisition assumptions,
> repeat cohorts, wholesale account forecasts, product mix, promotional calendar, pricing, landed
> cost, inventory requirements, hiring plan, marketing investment and cash requirements. It
> replaces the prior forecast as management's primary outlook. **The annual budget remains frozen
> for variance reporting.** Management reports Actual, Budget, Prior Forecast and Latest Forecast
> rather than overwriting the original budget.
>
> **Forecast horizon** — a **36-month forward view** with declining precision. Months 1–6:
> detailed monthly operational forecast, known wholesale POs, open POs, named hires, promotional
> calendar, SKU-level inventory planning. Months 7–18: monthly driver-based forecast, account and
> category assumptions, planned hiring thresholds, expected inventory and working-capital
> requirements. Months 19–36: strategic monthly forecast, category/channel growth, margin
> progression, headcount capacity steps, capital and liquidity outlook. The outer years exist for
> strategic capacity and cash planning rather than false precision.
>
> **Leadership scenarios** — three scenarios representing actual strategic choices rather than
> generic upside / base / downside percentages.
>
> *Scenario 1 — Balanced Base Case.* Management's operating plan: continued wholesale growth at a
> moderated pace, selective expansion with existing national accounts, gradual DTC growth, paid
> CAC improving toward the low-$30s, repeat purchase rate increasing gradually, gross margin
> stabilising, inventory turns recovering, disciplined hiring, EBITDA approaching breakeven as
> fixed-cost leverage improves. Objective: preserve double-digit growth without another major
> working-capital build.
>
> *Scenario 2 — Wholesale Acceleration.* Management accepts additional large-account
> opportunities and expands wholesale faster than plan. Produces higher near-term revenue,
> stronger unit volume, better utilisation of core inventory, lower blended gross margin, higher
> inventory purchases, higher receivables, greater customer concentration, and materially higher
> peak funding requirements. Central question: **how much wholesale growth can Northlake finance
> before the incremental revenue creates an unacceptable cash requirement?** Not a conventional
> "upside" — revenue is higher while several other financial outcomes may be worse.
>
> *Scenario 3 — DTC Recovery / Margin Case.* Northlake deliberately limits marginal wholesale
> expansion and reallocates attention toward higher-quality DTC growth: slower total revenue
> growth, stronger DTC mix, improved repeat purchase rate, tighter promotional discipline,
> improving paid CAC, higher consolidated gross margin, lower wholesale receivables, lower
> inventory commitments. Central question: **can improved DTC economics create a better cash and
> EBITDA outcome even if headline revenue growth is lower?** A strategic alternative rather than
> a simple optimistic case.
>
> **Downside sensitivity.** Finance maintains sensitivities for specific risks — DTC CAC remaining
> above $38; a major wholesale customer reducing orders; gross margin failing to recover after
> supplier inflation; inventory sell-through below plan; wholesale DSO extending toward 60 days;
> further supplier cost or freight increases. These apply to the primary scenarios without
> creating a separate full forecast for every risk.
>
> **Planning convention.** Maintain **separate scenario and version dimensions**. Versions:
> Budget, Prior Forecast, Latest Forecast, Actual. Scenarios: Balanced Base, Wholesale
> Acceleration, DTC Recovery / Margin. Budget and forecast are never overwritten by actuals.
> Variance reporting must preserve the original approved budget and prior forecasts so management
> can distinguish **performance variance, forecast revision, and strategic scenario differences**.

**Downstream consequences:**

- **Version and Scenario are two dimensions, not one.** This supersedes the single six-member
  scenario dimension listed at Q21, and it contradicts the standing rule in `CLAUDE.md` and
  `.claude/rules/powerbi-pbip.md` that scenario is one dimension carrying actual / budget /
  forecast. Those files need updating and the change needs an ADR.
- The three-way decomposition — performance variance vs forecast revision vs scenario difference
  — is the **structural requirement behind the automated variance commentary** in phase 5. A
  single "variance vs budget" column cannot express it.
- The scenarios are **strategic alternatives, not percentage bands**. Scenario 2 has higher
  revenue and worse cash; a model that treats scenarios as monotonic upside/downside cannot
  represent it. This directly serves the Q5 trade-off.
- **Forecast precision declines by horizon band** (1–6 / 7–18 / 19–36 months), so the model needs
  different driver granularity by period, not one uniform calculation across 36 months.
- Budget frozen, forecasts versioned and retained — an append-only fact pattern, never an update
  in place.


### Q23. Grain and customer-level data requirements

> The lowest level of detail that matters varies by process. Northlake does **not** use one
> universal grain for every fact table. The data model should retain transactional detail where it
> materially affects revenue, margin, inventory, customer behaviour or working capital, while
> financial planning outputs roll up to monthly reporting.
>
> **DTC revenue grain — order line.** Each DTC order line retains: order ID; order date /
> timestamp; customer ID; SKU; quantity; gross merchandise value; promotional discount; net
> merchandise value; shipping revenue allocated at order level; tax; return status; return amount;
> return date; promotion / campaign identifier where available; acquisition channel / source;
> first-time versus repeat customer flag.
>
> Required because Northlake analyses AOV, units per order, product mix, discounting, return
> behaviour, promotion performance, new versus repeat customers, cohort retention, CAC and
> contribution margin. Daily SKU-level data alone would destroy the linkage between customer
> acquisition, repeat behaviour, basket economics and returns.
>
> **Customer-level data is required for DTC**, with a persistent anonymised customer key. The
> model does **not** require personally identifiable information — no name, email address, phone
> number or street address. The analytical customer dimension needs only: customer key; first
> order date; acquisition channel; acquisition campaign where available; first-order cohort;
> geography at an appropriate non-identifying level; lifetime order count; new / repeat status;
> customer segment where derived.
>
> This supports first-time customer acquisition, 30 / 90 / 180 / 365-day repeat behaviour, cohorts,
> repeat purchase rate, cohort revenue, cohort contribution margin, CAC and lifetime economics.
> Customer identity must remain stable across transactions.
>
> **Wholesale revenue grain — invoice line / shipment line by account and SKU.** Fields: invoice /
> shipment ID; wholesale account; invoice date; shipment date; SKU; units; gross invoice amount;
> contractual discount; co-op allowance; markdown allowance; chargeback; other deduction; net
> revenue; payment terms; due date; collection date where paid; purchase-order reference;
> promotion / programme identifier where relevant.
>
> Wholesale customer-level analysis is required at **account level**, not end-consumer level,
> supporting account profitability, net realised price, deduction analysis, customer concentration,
> DSO, order cadence, reorder behaviour and account-level contribution margin.
>
> **Inventory grain — SKU × location × day**, with monthly snapshots for management reporting.
> Movements: opening inventory; purchases / receipts; DTC shipments; wholesale shipments; customer
> returns; transfers; write-offs; adjustments; closing inventory. The underlying event data can be
> transactional, but the core analytical inventory fact must support **daily balances** — required
> to distinguish stockouts, excess inventory, ageing, turns, weeks of supply, safety stock and
> inbound commitments. **Inventory should not exist only as a month-end GL balance.**
>
> **Purchase-order grain — PO line × SKU.** Fields: PO ID; supplier; SKU; order date; quantity;
> unit cost; currency; deposit percentage; deposit date; expected shipment date; actual shipment
> date; expected receipt date; actual receipt date; outstanding quantity; remaining commitment;
> cancellation / commitment status.
>
> **Returns grain — linked to the original order / invoice line.** Fields: original sale; customer
> / wholesale account; SKU; return initiation date; return receipt date; refund date; refund
> amount; recoverable inventory quantity; damaged / non-sellable quantity; return reason where
> available. The return fact must preserve the original sale period so return-lag and reserve
> adequacy can be analysed.
>
> **Marketing grain — date × campaign × acquisition channel.** Where platform data permits, spend
> should also connect to the acquired customer cohort. Metrics: spend; impressions; clicks;
> conversions; new customers; attributed orders; attributed revenue; campaign; channel; promotion;
> acquisition / retention classification. The FP&A model should **not rely solely on
> platform-reported ROAS** — finance combines spend with actual order and customer data to
> calculate paid CAC, blended CAC, new-customer contribution, cohort repeat economics and payback.
>
> **Financial ledger grain — GL account × department × posting date / accounting period**,
> aggregating to **GL account × department × month × version × scenario**. Operational schedules
> reconcile into the GL rather than replacing it.
>
> **Forecast grain.** Near-term: DTC at SKU / category × customer type × month; wholesale at named
> major account × SKU / category × month; inventory at SKU × month; purchasing at PO / planned PO ×
> SKU; marketing at channel / campaign × month; headcount at employee / role × department × month;
> opex at GL account × department × month. Longer-dated forecast progressively aggregates — months
> 19–36 do not require artificial order-line precision and operate at channel, product category,
> major wholesale account group, department and key operating-driver level.
>
> **Data-retention principle.** Retain detail where it supports a real management decision. The
> model must drill from **board KPI → financial statement line → channel / department → product or
> account → underlying transaction** without forcing every board report to operate at transaction
> level. The required architecture is a **multi-grain analytical model**, not one large
> denormalised monthly table.

**Downstream consequences:**

- **Seven distinct fact grains**, each declaring its own grain and each needing a uniqueness test:
  DTC order line; wholesale invoice/shipment line; inventory SKU × location × day; PO line × SKU;
  returns linked to originating sale line; marketing date × campaign × channel; GL account ×
  department × period. This is what the standing rule about declaring grain in a module docstring
  is for.
- **No PII, by design.** A persistent anonymised customer key with cohort and acquisition
  attributes only. This aligns with the project rule that no real personal names appear anywhere,
  and it removes a whole class of concern from a public repository.
- **Daily inventory balances, not month-end snapshots.** Stockouts last one to three weeks (Q14),
  so a month-end balance cannot detect them. This is the single most demanding grain requirement
  in the contract and it drives the size of the generated dataset.
- **Returns carry two dates and a link** — originating sale line, initiation, receipt, refund — so
  reserve adequacy is testable rather than assumed.
- **Marketing must reconcile to actual orders and customers**, not to platform ROAS, which makes
  attributed revenue a derived quantity the model owns rather than an input it trusts.
- The drill path from board KPI to transaction is an **acceptance criterion**, not a UI
  preference, and it constrains the Power BI model design in phase 4.

---

**Interview complete — all 23 scripted questions answered, 2026-09-05.**

## Post-interview decisions

Four items were unresolved after the scripted questions. Three arose because the script does not
cover them; one was a direct conflict between an answer and `docs/charter.md`. All were put as
options with their consequences rather than defaulted.

### D1. Capital structure — ABL revolver plus equity already raised

**Chosen:** an asset-based revolver with a borrowing base on eligible accounts receivable and
inventory, alongside seed / founder equity already on the balance sheet.

Rejected: a term loan or venture debt (fixed amortisation, but debt capacity disconnected from
working capital, losing the feedback loop); and equity-only funding (leaves ADR 0001 academic and
removes any financing constraint on Scenario 2).

**Why this matters.** The borrowing base contracts exactly when the business needs it most —
ageing inventory becomes ineligible, and stretched receivables reduce availability. That gives
Scenario 2 (Wholesale Acceleration) a hard funding ceiling rather than an arbitrary one, and it
makes the Q22 question "how much wholesale growth can Northlake finance" answerable from the
model rather than by assertion.

It also makes **ADR 0001 load-bearing**: interest accrues on a real, moving revolver balance, so
the beginning-of-period convention has genuine consequences rather than being a technicality on
an empty debt line.

Still to specify in the data contract: advance rates on AR and inventory, ineligibility rules
(aged inventory, past-due AR, concentration limits), the interest rate, and any covenants.

### D2. FX — supplier contracts denominated in USD, no FX machinery

**Chosen:** supplier contracts are denominated in USD. Foreign exchange surfaces only as supplier
price movement, which the purchase price variance from Q11 already captures.

Rejected: modelling FX explicitly on PO lines with rate tables and payables revaluation.

This resolves the conflict between Q21 (which asked that FX exposure be retained) and
`docs/charter.md` (which puts multi-currency out of scope) **in favour of the charter, unamended**.
The `currency` field on the PO line at Q23 is retained as USD-only for shape, not as a live
dimension. The April 2025 supplier cost increase works exactly as described without it.

### D3. Channel allocation — contribution only, corporate unallocated

**Chosen:** allocate only directly attributable costs to channel — marketing to DTC, account
management to wholesale, fulfilment and freight by actual activity. Supply chain, finance,
executive and technology remain in a single unallocated corporate block below channel
contribution.

Rejected: a hybrid pushing shared operations down on stated drivers (fuller channel P&L, but an
allocation policy a reviewer can argue with); and full absorption (arbitrary by construction, and
it would make wholesale look worse purely as a function of the allocation basis chosen).

This matches the Gross Profit → Contribution Profit → EBITDA hierarchy established at Q12, and it
means channel comparisons in the board pack are defensible without an allocation debate.

### D4. Prior-year profitability — profitable FY2023, breakeven FY2024, loss FY2025

**Chosen:** approximately +2–3% EBITDA in FY2023, near zero in FY2024, −8.1% in FY2025
(restated from −7.1% — see Q20a).

Rejected: loss-making throughout (reads as a business that never found its economics, making the
board question existential rather than strategic); and breakeven across FY2023–24 (less
explanatory power).

**Why this matters.** It makes the deterioration attributable. The business worked at a 72% DTC
mix; the wholesale shift, the April 2025 supplier increase and CAC rising from $29 to $34
progressively broke it. That is a "what changed" argument the variance commentary can actually
construct from the data, and it makes the three scenarios a recovery question rather than a
survival question.

### D5. Gross-to-net ordering — resolved arithmetically, no choice required

Listed as an open item at Q12c, but the stated bases resolve it without a decision. Q9 defines
wholesale deductions as a percentage of **gross invoiced sales**; Q10 defines wholesale returns as
a percentage of **net wholesale sales**. Each therefore has its own declared base and the two do
not compound ambiguously:

| Wholesale FY2025 | $M |
|---|---|
| Gross billings | 4.552 |
| Less deductions (3.0% of gross) | (0.137) |
| Less returns (1.5% of net) | (0.065) |
| **Net wholesale revenue** | **4.350** |

The ladder is fixed in the contract in this form so the ordering is explicit in code rather than
implicit in an implementation detail.

---

## Final conventions

Confirmed after the post-interview decisions, closing the remaining open items. Where these
conflict with an earlier answer, **these supersede it**.

### F1. Customer acquisition mix and CAC definitions

Non-paid share of new customers, by year:

| | FY2023 | FY2024 | FY2025 |
|---|---|---|---|
| Non-paid share of new customers | ~38% | ~34% | ~30% |

FY2025 therefore:

- Paid-acquired new customers: **~29,000**
- Organic / referral / owned new customers: **~12,400**
- **Total new customers: ~41,400**

**Three CAC definitions, used explicitly and never interchangeably:**

| Measure | FY2025 | Definition |
|---|---|---|
| Paid media CAC | ~$34 | Performance media spend ÷ paid-acquired new customers |
| Blended acquisition CAC | ~$24 | **Performance** media spend ÷ all new customers |
| Fully loaded acquisition CAC | ~$32–$34 target | Adds acquisition-attributable payroll, agencies, creative and tools |

*Corrected: the second measure was first defined as total media spend ÷ all new customers, which is
$1,450k ÷ 41,400 = $35.02, not $24. The $24 figure is performance media spend ÷ all new customers
($986k ÷ 41,400 = $23.82). The definition was wrong, not the figure.*

Reported alongside these, and **explicitly not a CAC**:

| Measure | FY2025 | Definition |
|---|---|---|
| Total marketing spend per new customer | ~$35 | Total marketing spend ÷ all new customers |

All three CAC measures share the same numerator base — performance media spend of $986k. Total
marketing spend includes brand, retention and owned-channel programme costs, which acquire no
customers; dividing them across new customers gives a marketing-intensity ratio, not an acquisition
cost.

**Do not allocate all marketing payroll or all brand/retention spend to acquisition.** The fully
loaded measure includes only the acquisition-attributable portion; retention, brand and
owned-channel programme costs are excluded from it by design.

The declining non-paid share (38% → 30%) is itself a finding: the business has become *more*
dependent on paid acquisition over the three years, at the same time as paid CAC rose from $29 to
$34. That is the DTC deterioration stated in customer terms rather than in spend terms, and it is
what the Scenario 3 "DTC Recovery" case is trying to reverse.

> **ADR required.** CAC definitions, and the rejected alternative of a single blended CAC or a
> fully loaded measure that absorbs all marketing cost.

### F2. Headcount — 28 FTE, superseding the 31 FTE at Q19

FY2025 year-end headcount is **28 FTE**, not 31. The fully loaded payroll anchor of **$2.981M** is
preserved, so FY2025 EBITDA is unaffected by the headcount change (it was separately restated
to ~$(859)k on the corrected post-return margin basis — see Q20a).

| Cost centre | FTE | Fully loaded $k |
|---|---|---|
| Executive / Corporate | 2 | 395 |
| People / Administration | 1 | 80 |
| Finance | 3 | 350 |
| Supply Chain / Operations | 4 | 420 |
| Product / Merchandising | 5 | 480 |
| Marketing / Ecommerce | 7 | 701 |
| Wholesale Sales | 3 | 365 |
| Customer Experience | 3 | 190 |
| **Total** | **28** | **2,981** |

Finance explicitly contains **Controller / Head of Finance, Senior Accountant, FP&A Manager**.

**The employee fact must carry:** hire date, departure date, department, role, salary,
benefits / payroll burden, bonus eligibility, and planned-hire status — so headcount steps
through the forecast rather than scaling as a percentage of revenue.

**Consequential revisions** (derived, applied for internal consistency):

- Q19's named roles must be trimmed to fit the revised counts. Supply Chain / Operations goes from
  six roles to four — Head of Supply Chain, demand / inventory planner, procurement / supplier
  manager, logistics coordinator — with the operations analyst and quality / product operations
  roles absorbed. Wholesale Sales goes from four to three: Head of Wholesale plus two key /
  regional account managers, with sales operations absorbed.
- Q19's headcount history (25 / 28 / 31) is rebased to **22 / 25 / 28** for FY2023 / FY2024 /
  FY2025, preserving the stated +3 per year progression to the confirmed FY2025 endpoint.
- Revenue per FTE becomes $368k / $372k / $379k across the three years — still modest operating
  leverage, consistent with outsourced manufacturing and warehousing.
- Q21's ninth cost centre, Technology / Shared Services, carries **no headcount**. It exists to
  hold software and shared technology cost, which is legitimate but must be explicit so a
  zero-FTE cost centre is not read as a data error.
- All Q19 hiring triggers stand unchanged.

### F3. ABL revolver — $2.0M committed facility

**Facility:** $2.0M committed asset-based revolver.

**Borrowing base:**

- 85% of eligible wholesale accounts receivable
- 50% of eligible finished-goods inventory
- **$1.0M inventory advance sublimit**
- less lender reserves

**AR eligibility:**

- Over 90 days past due is ineligible
- **25% individual account concentration cap**
- Specific disputed amounts and known credits are ineligible
- General **dilution reserve of ~2%** of otherwise eligible AR, able to increase if trailing
  dilution deteriorates

**Inventory eligibility** excludes or reserves against obsolete, damaged, aged, and
weak-liquidation-value inventory.

**Pricing:**

- SOFR + 3.50%
- 0.50% unused-line fee
- **SOFR is an explicit monthly model input**, not an embedded all-in rate

**Liquidity requirements:**

- Internal minimum cash: **$500k** — a management policy, not a covenant
- **Minimum excess availability of $250k**, tested monthly — the live financial covenant
- **FCCR minimum 1.10x** trailing twelve months, **springing: applicable only once TTM EBITDA is
  positive**

*Corrected from the first draft, which sprang the FCCR when excess availability fell below $300k.
With FY2025 EBITDA of −$859k a coverage ratio cannot reach 1.10x, so a continuously applicable test
would fail in month one of every scenario and every version — decorative rather than binding.
Availability is what actually constrains a borrower in this position, and it is what the model
tests until profitability arrives. See ADR 0008.*

**Five separately reported lines:** facility commitment; borrowing base; revolver drawn; excess
availability; minimum availability / covenant status.

The **~$650k FY2025 revolver draw** stands as the opening forecast balance, subject to
reconciliation against the final generated borrowing base.

> **Superseded.** That reconciliation was performed and the answer changed. With the $3.25M FY2024
> equity raise in place, Northlake funds the FY2025 loss and working capital build from the raise
> and never draws the revolver during FY2025. The opening forecast position at 1 January 2026 is
> **revolver drawn $0, cash $1.54M**. See `docs/data-contract.md` §6.10.

**Scenario 2 must not use debt as an unlimited balancing plug.** Where borrowing-base capacity is
exhausted, the model surfaces the **first funding-gap month and the additional capital required**.

**Why this is the sharpest part of the model.** The borrowing base is built from the same AR and
inventory that the Q5 tension degrades. Ageing inventory becomes ineligible; stretched receivables
and the 25% concentration cap reduce availability; the dilution reserve rises with deductions.
Availability therefore contracts precisely when the business most needs it, and the largest
account at 24% of wholesale sits immediately below the concentration cap — so growth in that
account starts consuming availability rather than creating it.

That converts the Q22 question "how much wholesale growth can Northlake finance" from a rhetorical
framing into a computed answer with a date attached.

> **ADR required.** Revolver capacity as a binding constraint that surfaces a funding gap, rather
> than debt as a balancing plug.

---

## Open items

**None.** All items raised during the interview were closed by the post-interview decisions (D1–D5)
and the final conventions (F1–F3).

## ADRs to be written

Numbered here so the contract and the ADR files agree. ADR 0001 (beginning-balance interest)
already exists from phase 0 and is unaffected, though D1 makes it load-bearing.

| # | Decision | Source |
|---|---|---|
| 0002 | Returns recognised on an ASC 606 basis: refund liability and right-of-return asset | Q10a |
| 0003 | Standard landed cost with PPV / freight / duty variances, rather than actual costing | Q11 |
| 0004 | COGS boundary: outbound shipping and variable fulfilment in COGS, payment processing in opex | Q12 |
| 0005 | Marketing as a constrained driver with a CAC response curve, not % of revenue or fixed ROAS | Q18 |
| 0006 | Three explicit CAC definitions: paid media, blended acquisition, fully loaded acquisition | F1 |
| 0007 | Version and Scenario as two separate dimensions | Q22 |
| 0008 | ABL revolver with a borrowing base, treated as a binding constraint that surfaces a funding gap | D1, F3 |
| 0009 | Supplier contracts denominated in USD; FX out of scope, charter unamended | D2 |
| 0010 | Channel contribution reporting with corporate costs unallocated | D3 |

ADR 0007 additionally requires updating the standing rule in `CLAUDE.md` and
`.claude/rules/powerbi-pbip.md`, both of which currently describe scenario as a single dimension
carrying actual / budget / forecast.
