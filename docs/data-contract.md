# Data contract — Northlake, Inc.

> **Illustrative company, synthetic data.** Northlake, Inc. is not a real business. Every figure
> below is a modelling assumption for a generated dataset. No real company, no real people, no
> scraped or proprietary data.
>
> *Northlake* is the modelled business. *Bellwether* is this project. The two are never
> interchangeable.

**Status:** draft, awaiting approval. Derived from `docs/phases/phase-01-answers.md`.
**Phase:** 1. The generator is not to be built until this document is approved.

Everything downstream inherits from this document. Getting a grain wrong means rebuilding the
oracle, the workbook and the Power BI model, so a change here is a documented decision rather than
an implementation detail.

---

## 1. The business

Northlake is a premium home and lifestyle brand selling reusable drinkware, food storage and
related accessories, direct to consumers and through wholesale retail accounts. Single legal
entity, single currency, fiscal year ending 31 December.

### 1.1 Three-year history

| | FY2023 | FY2024 | FY2025 |
|---|---|---|---|
| Net revenue | $8.10M | $9.30M | $10.60M |
| Growth | — | +14.8% | +14.0% |
| DTC share | 72% | 66% | 59% |
| Wholesale share | 28% | 34% | 41% |
| DTC net revenue | $5.83M | $6.14M | $6.25M |
| Wholesale net revenue | $2.27M | $3.16M | $4.35M |
| EBITDA margin | +2% to +3% | ~0% | −7.1% |
| Inventory turns | — | 4.1x | 3.3x |
| Paid CAC | — | $29 | $34 |
| Non-paid share of new customers | 38% | 34% | 30% |
| Headcount (year end) | 22 | 25 | 28 |

DTC grows at a 3.5% CAGR in dollar terms while wholesale grows at 38.4%. Substantially all
incremental revenue is wholesale.

### 1.2 The central tension

Wholesale growth is real but structurally dilutive and working-capital intensive. Wholesale
realises ~55% of the DTC net price per unit, and the channel mix shift is therefore the dominant
term in the consolidated gross margin bridge. At the same time DTC's own economics have weakened:
paid CAC rose 17% and the non-paid share of new customers fell eight points over three years.

The forward plan is judged on four linked outcomes — **revenue growth, gross margin, inventory
productivity, and operating cash flow**. A plan that delivers revenue and misses materially on any
of the other three is not a successful plan.

### 1.3 Two dateable FY2025 events

| Event | Date | Effect |
|---|---|---|
| Primary drinkware supplier cost increase, +8% average on product cost | Effective April 2025 | Compresses margin, concentrated in wholesale because wholesale price is fixed at PO quote while cost is not |
| Insulated food-storage range launch underperforms | Launched February 2025; ~35% below plan by June 2025 | Aged inventory build in H2 2025, markdown pressure, elevated shrink |

Both are required to be visible in the generated data as consequences of modelled mechanics, not
as narrative overlays. The launch failure in particular is arithmetically forced: POs for a
February launch are placed October–December 2024, and units past the cancellation point continue
arriving after demand weakness becomes visible in April–June.

---

## 2. Global conventions

### 2.1 Currency and rounding

- Single functional and reporting currency: **USD**. No consolidation, no foreign subsidiaries.
- Supplier contracts are **denominated in USD** (ADR 0009). FX appears only as supplier price
  movement, captured by purchase price variance. There is no rate dimension and no revaluation.
- Monetary values are stored as **integer minor units (cents)** in fact tables. Rates and
  percentages are stored as decimals.
- **Rounding is applied at presentation only, never in intermediate calculation.**

### 2.2 Dates and periods

- Fiscal year end **31 December**; 12 calendar months, January through December.
- Periods are **closed-open date ranges**: `[period_start, period_end)`. A monthly period covers
  `[2025-03-01, 2025-04-01)`.
- **Date spine:** contiguous daily calendar from **2023-01-01 to 2028-12-31** — 36 months of
  actuals (FY2023–FY2025) and 36 months of forecast (FY2026–FY2028). No gaps.
- The date dimension carries a **banking-day flag**, required by the payment-processor settlement
  lag (2 business days), which cannot be expressed on a pure calendar.

### 2.3 Determinism

- The generator is seeded; the seed lives in configuration, never at a call site.
- No `datetime.now()`, no unseeded RNG, no dependence on dict or filesystem ordering.
- The same seed produces byte-identical output. Regenerating data must never change a committed
  test expectation.

### 2.4 Keys

- Dimensions carry **surrogate integer keys**; natural keys are retained as attributes.
- Every fact declares its grain in a one-sentence module docstring, and a test asserts uniqueness
  at that grain.
- Referential integrity: zero orphan keys across every fact-to-dimension join.

---

## 3. Scenario and version

**These are two separate dimensions** (ADR 0007), which supersedes the earlier project rule
treating scenario as one dimension carrying actual / budget / forecast.

### 3.1 `dim_version` — what kind of number this is

| Member | Meaning |
|---|---|
| Actual | Posted results |
| Budget | The approved annual plan, **frozen**; never overwritten |
| Prior Forecast | The immediately preceding formal reforecast, retained |
| Latest Forecast | Management's current outlook |

### 3.2 `dim_scenario` — which strategic choice this represents

| Member | Central question |
|---|---|
| Balanced Base | Management's operating plan: moderated wholesale growth, CAC recovering to the low $30s, margin stabilising, turns recovering, EBITDA approaching breakeven |
| Wholesale Acceleration | How much wholesale growth can Northlake finance before incremental revenue creates an unacceptable cash requirement? |
| DTC Recovery / Margin | Can improved DTC economics produce a better cash and EBITDA outcome even with lower headline revenue growth? |

Scenarios are **strategic alternatives, not monotonic bands**. Wholesale Acceleration has higher
revenue *and* worse cash; any model treating scenarios as ordered upside/downside cannot represent
it.

Downside sensitivities (CAC above $38, a major account reducing orders, margin failing to recover,
sell-through below plan, DSO extending to 60 days, further cost or freight increases) are applied
*to* scenarios rather than being scenarios themselves.

### 3.3 Why both are needed

Variance reporting must decompose into three distinct things:

1. **Performance variance** — Actual vs Budget, same scenario
2. **Forecast revision** — Latest Forecast vs Prior Forecast, same scenario
3. **Scenario difference** — Balanced Base vs Wholesale Acceleration, same version

A single "variance vs budget" column cannot express this, and the automated commentary in phase 5
depends on the decomposition.

---

## 4. Dimensions

| Dimension | Grain | SCD | Notes |
|---|---|---|---|
| `dim_date` | One row per calendar day, 2023-01-01 to 2028-12-31 | n/a | Banking-day flag; fiscal month/quarter/year; promotional period flag |
| `dim_product` | One row per SKU version | **Type 2** | Effective-dated on `sku_class`, `lifecycle_state`, `category` |
| `dim_customer` | One row per anonymised DTC customer | **Type 1** | Acquisition attributes are immutable once set |
| `dim_wholesale_account` | One row per account version | **Type 2** | Effective-dated on `tier`, `payment_terms`, `freight_terms` |
| `dim_supplier` | One row per supplier version | **Type 2** | Effective-dated on payment-term structure |
| `dim_employee` | One row per employee version | **Type 2** | Effective-dated on department, role, compensation |
| `dim_gl_account` | One row per GL account (~135) | Type 1 | Carries cost behaviour: fixed / step-fixed / directly budgeted / variable |
| `dim_department` | One row per cost centre (9) | Type 1 | |
| `dim_campaign` | One row per marketing campaign | Type 1 | |
| `dim_promotion` | One row per promotional event | Type 1 | |
| `dim_location` | One row per stock location | Type 1 | 3PL warehouse(s); in-transit treated as a location |
| `dim_version` | 4 members | Type 1 | §3.1 |
| `dim_scenario` | 3 members | Type 1 | §3.2 |

### 4.1 `dim_product`

~85 active SKUs across four families.

| Family | SKUs | Landed cost range |
|---|---|---|
| Drinkware | ~35 | $14–$17 |
| Food storage | ~25 | $12–$16 |
| Accessories / replacement parts | ~15 | $3–$9 |
| Seasonal / limited edition | ~10 | 5–15% above comparable core |

Attributes: `sku_code` (natural key), `product_family`, `category`, `sku_class` (A/B/C),
`lifecycle_state` (launch / core / seasonal / discontinued), `launch_date`, `msrp`,
`case_pack_units` (~12, varies by SKU), `moq`, `return_rate_class`, `is_hero`.

**SKU class drives inventory policy** and maps onto revenue concentration:

| Class | Share of revenue | Safety stock target | Replenishment |
|---|---|---|---|
| A — hero / core | 55% | 5–6 weeks | Continuous, highest service level |
| B — core secondary | 30% | 3–4 weeks | Regular, tighter MOQ discipline |
| C — seasonal / long tail | 15% | 0–2 weeks | Finite seasonal runs |

Revenue concentration must satisfy: top 5 SKUs ≈ 38% of revenue, top 10 ≈ 55%.

Return rate is a **product-category attribute**, not a channel constant:

| Category | DTC return rate |
|---|---|
| Core drinkware | 5–6% |
| Food storage | 7–8% |
| Seasonal / limited edition | 9–10% |
| Accessories | 3–4% |

`lifecycle_state` also drives supplier lead time: 90 days for replenishment, 120–150 days for a
first production run.

### 4.2 `dim_customer`

**No personally identifiable information.** No name, email address, phone number or street
address. A persistent anonymised `customer_key` only.

Attributes: `customer_key`, `first_order_date`, `acquisition_channel`, `acquisition_campaign`,
`first_order_cohort` (year-month), `geography` (non-identifying level), `lifetime_order_count`,
`customer_segment`.

Acquisition channel is immutable once set and drives **both** repeat rate and CAC. Customers
acquired organically, by referral, or from the email/SMS base repeat at a materially higher rate
than those acquired through broad paid social.

Identity must remain stable across transactions so a customer can be followed through multiple
orders and cohorts computed at 30 / 90 / 180 / 365 days.

### 4.3 `dim_wholesale_account`

~38 active accounts. Concentration must satisfy: largest 24% of wholesale revenue, second 15%,
third 10%, top 5 combined 62%.

| Tier | MSRP discount | Payment terms | Typical DSO |
|---|---|---|---|
| Independent | 40% | Net 30 | 35–40 days |
| Regional chain | 45% | Net 45 | 45–50 days |
| National account | 48–50% | Net 60 (some Net 75) | 60–65 days |

Weighted average discount across the portfolio: **46% of MSRP**.

Additional attributes: `freight_terms` (Northlake-paid vs collect/customer-routed — ~35% of
wholesale revenue ships Northlake-paid), `deduction_profile`, `credit_quality`,
`is_individually_forecast` (top 5 accounts).

Two risks run in **opposite directions** across the account base and must not share a driver:
deduction risk concentrates in the largest accounts (5–6% in promotional periods against a 3%
channel average), while credit risk concentrates in the long tail.

### 4.4 `dim_department` and cost behaviour

Nine cost centres: Executive / Corporate; Finance; People / Administration; Supply Chain /
Operations; Product / Merchandising; Marketing / Ecommerce; Wholesale Sales; Customer Experience;
Technology / Shared Services.

**Technology / Shared Services carries no headcount.** It holds software and shared technology
cost. A zero-FTE cost centre is correct here, not a data error.

Department is a real GL dimension, not a reporting overlay. **Department ≠ channel** — see §6.7.

Every GL account carries a cost behaviour classification: **fixed**, **step-fixed**, **directly
budgeted**, or **variable**. Operating leverage emerges from this structure rather than being
asserted.

---

## 5. Fact tables

Seven operational facts plus the ledger and payroll. Each declares its grain; each grain gets a
uniqueness test.

### 5.1 `fact_dtc_order_line`

**Grain: one row per line of a DTC order.** Key `(order_id, line_number)`.

Fields: `order_id`, `line_number`, `order_timestamp`, `customer_key`, `sku_key`, `quantity`,
`gross_merchandise_value`, `promotional_discount`, `net_merchandise_value`,
`shipping_revenue_allocated`, `tax`, `promotion_key`, `campaign_key`, `acquisition_channel`,
`is_first_order`.

Order-line grain is required because daily SKU aggregates destroy the link between acquisition,
repeat behaviour, basket economics and returns.

**FY2025 calibration:** ~83,400 orders; $78 AOV net of discounts; 1.7 units per order; ~142,000
units before returns; ~$2.43 blended shipping revenue per order.

### 5.2 `fact_wholesale_invoice_line`

**Grain: one row per line of a wholesale invoice/shipment.** Key `(invoice_id, line_number)`.

Fields: `invoice_id`, `line_number`, `account_key`, `invoice_date`, `shipment_date`, `sku_key`,
`units`, `gross_invoice_amount`, `contractual_discount`, `co_op_allowance`, `markdown_allowance`,
`chargeback`, `other_deduction`, `net_revenue`, `payment_terms`, `due_date`, `collection_date`,
`po_reference`, `programme_key`.

**Both gross billings and net revenue are stored**, with each deduction type as its own
contra-revenue field. Deductions are a named driver of wholesale margin variance and cannot be
netted at source.

**FY2025 calibration:** gross billings ~$4.552M; ~173,000 units; ~$25.10 net per unit.

### 5.3 `fact_return_line`

**Grain: one row per returned line, linked to its originating sale line.**

Fields: originating sale reference (`order_id`/`invoice_id` + `line_number`), `customer_key` or
`account_key`, `sku_key`, `return_initiation_date`, `return_receipt_date`, `refund_date`,
`refund_amount`, `recoverable_quantity`, `non_sellable_quantity`, `return_reason`.

The return **must preserve the originating sale period** so return lag and reserve adequacy are
testable.

| | DTC | Wholesale |
|---|---|---|
| Rate | 7% of net merchandise sales | 1.5% of net wholesale sales |
| Lag | Mostly within 30 days; ~18 day mean | 45–90 days |
| Recoverable to sellable inventory | 80% | 50% |

The non-recoverable remainder is written off through shrink / obsolescence.

### 5.4 `fact_inventory_daily`

**Grain: SKU × location × day.**

Movements: opening, purchases/receipts, DTC shipments, wholesale shipments, customer returns,
transfers, write-offs, adjustments, closing. Cost-layer / receipt-date granularity is required so
ageing and reserves compute from actual age.

**Daily balances are mandatory.** Stockouts last one to three weeks, so a month-end balance cannot
detect them. This is the most demanding grain in the contract and it sizes the dataset.

Monthly snapshots are derived for management reporting; inventory must never exist only as a
month-end GL balance.

**FY2025 calibration:** turns 3.3x on landed COGS; average inventory ~$1.39M; ~111 days on hand.

### 5.5 `fact_purchase_order_line`

**Grain: PO line × SKU.** Key `(po_id, line_number)`.

Fields: `po_id`, `line_number`, `supplier_key`, `sku_key`, `order_date`, `quantity`, `unit_cost`,
`currency` (USD only — see ADR 0009), `deposit_pct`, `deposit_date`, `expected_shipment_date`,
`actual_shipment_date`, `expected_receipt_date`, `actual_receipt_date`, `outstanding_quantity`,
`remaining_commitment`, `commitment_status`, `shipment_mode` (ocean / air).

**A PO carries a state machine:** raised → confirmed → past cancellation point → in transit →
received. Only pre-cancellation states are flexible in a reforecast. Once past the commitment
point, units are treated as committed inventory even if the sales forecast declines.

Purchasing is **constrained and lumpy**, never a frictionless balancing figure:

- Standard lead time **90 days** PO to available for sale (production 45–60, inspection/export
  5–10, ocean transit 25–35); 120–150 days for a first production run.
- MOQ by family: drinkware 1,000–1,500 per SKU/colour; food storage 800–1,200; accessories
  500–1,000; custom seasonal 1,500–2,500.
- Order rounding to MOQ, seasonal ordering cut-offs, and existing committed POs all bind.

Seasonal PO timing: holiday/BFCM inventory committed May–July; spring launches October–December of
the prior year; fall launches April–June.

Air freight is an approved exception, tracked as a management variance, never blended into the
standard freight assumption.

### 5.6 `fact_po_payment`

**Grain: one row per scheduled or actual supplier payment on a PO.** Key
`(po_id, payment_sequence)`.

Supplier terms by relationship type:

| Type | Deposit | Balance |
|---|---|---|
| Established strategic supplier | 20% at PO | 80% 30 days after shipment |
| Core replenishment | 30% at PO | 70% 30 days after shipment |
| New launch / custom seasonal | 50% at PO | 50% before shipment |

**Effective DPO is negative — approximately 30 days before goods are received** on core terms.
Northlake funds its suppliers rather than being funded by them. Accounts payable therefore cannot
be forecast as a percentage of COGS; it is built from these events.

Deposits are carried as **supplier advances / prepaid inventory**, a distinct balance sheet line,
until goods are received. On receipt the deposit becomes part of inventory cost and any unpaid
balance moves to accounts payable.

**Open PO commitments are a required disclosure.** Reported AP materially understates committed
cash.

### 5.7 `fact_marketing_spend`

**Grain: date × campaign × acquisition channel.**

Fields: `spend`, `impressions`, `clicks`, `conversions`, `new_customers`, `attributed_orders`,
`attributed_revenue`, `campaign_key`, `channel`, `promotion_key`,
`acquisition_or_retention_class`.

**The model must not rely on platform-reported ROAS.** Attributed revenue is derived by combining
spend with actual order and customer data.

**FY2025 calibration:** $1.45M total (13.7% of net revenue, 23% of DTC net revenue); 68% paid /
performance, 32% owned, retention and brand.

### 5.8 `fact_gl`

**Grain: GL account × department × posting date**, extended to **× version × scenario** for
planning.

~135 active accounts. The gross-to-net and gross-margin bridges must be constructible **from
ledger accounts alone**, without manual management adjustments — this is a testable assertion, not
a presentation preference.

Required contra-revenue accounts: DTC returns, wholesale returns, promotional discounts, co-op
marketing deductions, markdown allowances, chargebacks / compliance deductions. DTC shipping
revenue is its own account.

Required COGS accounts: product cost, inbound freight, duty and customs, outbound parcel freight,
wholesale outbound freight, DTC pick-and-pack, wholesale fulfilment, packaging, inventory
write-downs, shrink / damage.

Budget and forecast are **append-only and never overwritten by actuals**.

### 5.9 `fact_headcount`

**Grain: employee × month.**

Fields: `employee_key`, `hire_date`, `departure_date`, `department_key`, `role`, `salary`,
`benefits_payroll_burden`, `bonus_eligibility`, `planned_hire_status`.

Payroll is **never a percentage of revenue**. Existing employees are fixed unless an explicit
departure or restructuring is modelled; planned hires activate when an operating threshold is
crossed.

**FY2025 roster — 28 FTE, $2.981M fully loaded:**

| Cost centre | FTE | $k |
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

Finance contains Controller / Head of Finance, Senior Accountant, FP&A Manager.

**Hiring triggers are operational, not financial**, which makes the operating metrics below
first-class model outputs rather than reporting views:

| Function | Trigger |
|---|---|
| Customer Experience | DTC orders sustainably above 100,000–110,000 |
| Wholesale Sales | Another major national account; accounts above ~50; or >10–12 managed relationships per manager |
| Supply Chain | Active SKUs above 100–110; revenue above $13–14M; or PO/inbound volume above capacity |
| Finance | Revenue $14–16M, or deduction and inventory accounting complexity above capacity |
| Product | Beyond ~110 active SKUs, a new category, or an expanded launch calendar |
| Marketing | DTC revenue above $7.5–8.0M |
| People / HR | Total headcount 40–45 |

Temporary labour, agencies and contractors are modelled separately from permanent FTE, so November
and December absorb peak CX demand without permanent staffing.

---

## 6. Financial conventions

Each of these is a decision with a rejected alternative, recorded as an ADR.

### 6.1 Revenue recognition and returns — ADR 0002

Revenue is recognised **net of expected returns**, on an ASC 606 basis. A **refund liability** and
a **right-of-return asset** (recoverable inventory at cost) are carried and unwind as returns
arrive.

Without this, an 18-day mean DTC return lag would flatter November after Black Friday and push the
correction into December.

Refunds reduce revenue; they are never an operating expense.

### 6.2 Gross-to-net ladders

**DTC:**

```
Gross merchandise value
  less promotional discount
= Net merchandise revenue          ($78.00 per order, FY2025)
  plus shipping revenue            (~$2.43 per order blended)
  less returns                     (7% of net merchandise sales)
= Reported DTC net revenue
```

**Wholesale** — each component has its own declared base, so the two do not compound ambiguously:

```
Gross billings                                   $4.552M
  less deductions        (3.0% of gross)        ($0.137M)
  less returns           (1.5% of net)          ($0.065M)
= Net wholesale revenue                          $4.350M
```

Shipping revenue is **gross, never netted against outbound freight**, so a free-shipping promotion
is visible on both sides.

### 6.3 COGS boundary — ADR 0004

**In COGS:** landed product cost (product, inbound freight, duty); outbound shipping (DTC parcel;
wholesale freight where Northlake bears it); variable fulfilment (pick-and-pack, per-order
handling, packaging, variable warehouse handling).

**In operating expense:** payment processing (a variable selling expense within Sales &
Marketing); fixed 3PL storage, retainers and account management.

The split turns on **variability with order volume, not on department** — the same 3PL invoice
splits across COGS and opex.

**Three margin tiers:**

```
Revenue − landed cost − outbound shipping − variable fulfilment  = Gross Profit
  − payment processing − variable marketing − channel-variable selling = Contribution Profit
  − fixed operating expense                                       = EBITDA
```

Classification is **frozen across historical and forecast periods**. Management does not
reclassify between COGS and opex to achieve a presentation.

### 6.4 Landed and standard cost — ADR 0003

Landed cost composition: **78% product, 12% inbound freight, 10% duty and customs**. FY2025
portfolio average **$15.00 per unit**.

Inventory is carried at **standard landed cost**, with **purchase price, freight and duty
variances captured separately**. This is what allows the April 2025 supplier increase (product
cost only) to be separated from freight volatility in the margin bridge.

Landed cost is **effective-dated** at SKU or product-family level. It is not a static constant.

### 6.5 Inventory reserve and shrink

Ageing buckets and indicative reserve rates:

| Age | Bucket | Reserve |
|---|---|---|
| 0–180 days | Current | 0% |
| 181–270 days | Watch list | 10% |
| 271–365 days | Aged | 25% |
| >365 days | Potential obsolescence | 50–100% by recoverability |

Inventory is written down when net realisable value falls below landed cost. Shrink, damage and
obsolescence run at **~1% of average inventory cost** normally; **~2.5% in FY2025**.

### 6.6 Stockouts

Stockouts are modelled as a **suppression layer over underlying demand**, not as weak demand.

FY2025: ~4% of potential DTC demand on hero SKUs affected; most stockouts last one to three weeks;
**50% of affected demand is assumed lost**, 50% substituted or deferred.

The generator must therefore carry **both underlying demand and realised revenue**, so poor
availability is never misread as a demand problem. Hero SKUs stock out at peak while the long tail
ages simultaneously — a single company-wide weeks-of-supply target cannot reproduce both.

### 6.7 Channel allocation — ADR 0010

**Contribution only; corporate unallocated.**

Directly attributable costs are allocated to channel: marketing to DTC, account management to
wholesale, fulfilment and freight by actual activity. Supply Chain, Finance, Executive, People and
Technology remain in a **single unallocated corporate block** below channel contribution.

Cost centre ≠ channel. Marketing supports primarily DTC but incurs brand spend benefiting both;
Supply Chain serves both; Wholesale Sales is a department while Wholesale is a channel.

### 6.8 CAC definitions — ADR 0006

| Measure | FY2025 | Definition |
|---|---|---|
| Paid media CAC | $34 | Performance media spend ÷ paid-acquired new customers |
| Blended media CAC | $24 | Total media spend ÷ all new customers |
| Fully loaded acquisition CAC | $32–$34 target | Adds acquisition-attributable payroll, agencies, creative and tools |

**Not all marketing payroll and not all brand/retention spend is allocated to acquisition.**

FY2025 new customers: ~29,000 paid-acquired, ~12,400 organic / referral / owned, **~41,400 total**.

### 6.9 Marketing as a driver — ADR 0005

Marketing splits into two behaviours that cannot share a driver:

- **Variable performance marketing** (paid social, paid search, affiliate, creator, retargeting) —
  solved from a new-customer target against a **CAC response curve**, subject to a spending ceiling
  and an efficiency threshold. Marginal efficiency deteriorates as spend rises; a fixed-ROAS
  formula is prohibited.
- **Semi-fixed programme marketing** (creative production, CRM tools, PR, brand partnerships,
  content, baseline agency) — budgeted directly, stepping periodically.

**If required spend exceeds the approved CAC threshold, the model reduces assumed new-customer
acquisition rather than silently improving efficiency.** This is what prevents marketing becoming
a balancing plug.

### 6.10 Interest and financing — ADR 0001, ADR 0008

Interest accrues on the **beginning-of-period** debt balance, so the model is acyclic and
iterative calculation stays off (ADR 0001).

**$2.0M committed ABL revolver.**

Borrowing base:

- 85% of eligible wholesale AR
- 50% of eligible finished-goods inventory, with a **$1.0M inventory advance sublimit**
- less lender reserves

AR eligibility: over 90 days past due ineligible; **25% single-account concentration cap**;
disputed amounts and known credits ineligible; **~2% general dilution reserve**, able to increase
if trailing dilution deteriorates.

Inventory eligibility excludes or reserves against obsolete, damaged, aged and
weak-liquidation-value stock.

Pricing: **SOFR + 3.50%**, 0.50% unused-line fee. **SOFR is an explicit monthly model input**, not
an embedded all-in rate.

Liquidity: internal minimum cash **$500k**; **springing FCCR test** when excess availability falls
below **$300k**; FCCR minimum **1.10x** trailing twelve months.

**Five separately reported lines:** facility commitment; borrowing base; revolver drawn; excess
availability; minimum availability / covenant status.

FY2025 opening drawn balance ~**$650k**, subject to reconciliation against the generated borrowing
base.

**Debt is never an unlimited balancing plug.** Where borrowing-base capacity is exhausted, the
model surfaces the **first funding-gap month and the additional capital required**.

The borrowing base is deliberately built from the same AR and inventory the central tension
degrades: ageing inventory becomes ineligible, stretched receivables and the concentration cap
reduce availability, and the dilution reserve rises with deductions. The largest account at 24% of
wholesale sits immediately below the 25% cap, so growth there consumes availability rather than
creating it.

### 6.11 Bad debt

Wholesale bad debt ~**0.4% of wholesale net revenue**, concentrated in the long tail. **Forecast
separately from DSO**, never embedded in the collection lag. No material DTC bad debt.

AR ageing buckets: current 0–30; 31–60 past due (monitor); 61–90 past due (elevated); >90 past due
(specific reserve review).

### 6.12 Cash timing

| Flow | Timing |
|---|---|
| DTC receipts | 2 business days settlement; **3 calendar days** planning equivalent. Processor receivable is a distinct balance sheet line |
| Wholesale receipts | FY2025 actual DSO **52 days**; base forward 50; downside 58–60; upside 45–47. Terms plus a behavioural delay caused by deduction disputes and short-pays |
| Supplier payments | Per §5.6. Effective DPO ~−30 days |

Deductions appear **twice**: as contra-revenue (§6.2) and as a cause of collection delay here. A
short-paid invoice stays open until reconciled.

---

## 7. FY2025 calibration targets

The generator must reproduce these within tolerance. They are mutually consistent and were
reconciled during the interview.

### 7.1 Unit economics

| Per DTC order | | Per wholesale unit | |
|---|---|---|---|
| Merchandise revenue | $78.00 | Net revenue | $25.10 |
| Shipping revenue | $2.43 | | |
| **Total revenue** | **$80.43** | **Total revenue** | **$25.10** |
| Landed cost (1.7 × $15) | $25.50 | Landed cost | $15.00 |
| Outbound parcel | $7.25 | Outbound freight (1.8%) | $0.45 |
| Variable fulfilment | $3.25 | Variable fulfilment | $0.45 |
| **Gross profit** | **$44.43** | **Gross profit** | **$9.20** |
| **Gross margin** | **55.2%** | **Gross margin** | **36.7%** |

Channel gross margin gap **18.5 points**. Blended gross margin **47.6%**.

Cost rates: DTC parcel $7.25/order base ($7.60–7.90 peak, $7.00 long-term target); DTC fulfilment
$3.25/order (pick-pack $2.20, packaging $0.70, handling $0.35); wholesale fulfilment $4.25/carton
(~12 units) plus ~$18/pallet; payment processing 2.9% of gross customer payments (2.7% upside,
3.1% downside).

DTC shipping: ~35% of orders pay, ~$6.95 each; free-shipping threshold ~$75; the paying share
falls materially during BFCM and holiday.

### 7.2 P&L bridge

| FY2025 | $M |
|---|---|
| Net revenue | 10.60 |
| Gross profit @ 47.6% | 5.05 |
| Payment processing | (0.19) |
| Marketing | (1.45) |
| Payroll | (2.98) |
| Fixed cost base | (1.16) |
| Bad debt | (0.02) |
| **EBITDA** | **(0.75)** |
| **EBITDA margin** | **(7.1%)** |

Fixed cost base: 3PL fixed $228k ($19k/month); office $150k; software $280k ($225k fixed, $55k
usage-based); professional fees $210k; insurance $95k; other corporate ~$200k.

### 7.3 Working capital

| | FY2025 |
|---|---|
| Inventory (average, at landed cost) | ~$1.39M |
| Wholesale receivables | ~$620k |
| Processor receivable | ~$51k |
| Supplier advances | ~$370k |
| Accounts payable | ~$290k |
| **Net working capital** | **~$2.1M (20% of revenue)** |

The channel mix shift absorbed roughly **$720k** of incremental working capital in FY2025 —
~$400k into inventory and ~$320k into receivables.

### 7.4 Seasonality

Promotional periods: spring March–April; summer June; back-to-school / fall August–September;
**Black Friday / Cyber Monday November**; holiday gifting December.

~27% of annual DTC gross revenue moves on promotion at ~16% average realised discount. BFCM alone
is ~12% of annual DTC revenue.

**November and December must move revenue up and gross margin down simultaneously.** Promotions
move four things at once and in conflicting directions: order volume up, merchandise ASP down,
shipping revenue down, outbound freight up.

Promotion targeting is driven by inventory state — weeks of supply, colour variant age — which
links the promotional calendar to the inventory module rather than leaving it exogenous.

---

## 8. Forecast structure

36 months, January 2026 to December 2028, with precision declining by horizon.

| Band | Granularity |
|---|---|
| Months 1–6 | Detailed monthly operational forecast; known wholesale POs; open purchase orders; named hires; promotional calendar; SKU-level inventory planning |
| Months 7–18 | Monthly driver-based; account and category assumptions; planned hiring thresholds; expected working capital |
| Months 19–36 | Strategic monthly; category and channel growth; margin progression; headcount capacity steps; capital and liquidity outlook |

Outer years exist for strategic capacity and cash planning, not false precision. The model must
support different driver granularity by band rather than one uniform calculation across 36 months.

Planning input is owned at **GL account × department × month × version × scenario**. Operational
schedules reconcile *into* the GL rather than replacing it.

---

## 9. Validation suite

The generator is not done until these pass. They run in CI.

**Structural**

1. Grain uniqueness on every fact table
2. Referential integrity — zero orphan keys on every fact-to-dimension join
3. Date spine contiguous, no gaps, covering every fact date
4. No PII field present in any customer record

**Accounting**

5. Trial balance sums to zero by period
6. Subledger totals tie to the corresponding control account (AR, AP, inventory, refund liability)
7. Gross-to-net ladders reconstructable from ledger accounts alone, both channels
8. Inventory roll-forward ties: opening + receipts − shipments + returns − write-offs = closing,
   every SKU, every day

**Calibration**

9. FY2023/24/25 net revenue within tolerance of $8.10M / $9.30M / $10.60M
10. Channel mix within tolerance of 72/28, 66/34, 59/41
11. Blended gross margin 47.6% ±0.5pt for FY2025; channel gap 18.5pt ±1pt
12. FY2025 EBITDA −7.1% ±0.5pt; FY2023 positive; FY2024 within ±1pt of zero
13. Inventory turns 4.1x FY2024, 3.3x FY2025, each ±0.2x
14. Wholesale DSO 52 days ±3
15. SKU concentration: top 5 ≈ 38%, top 10 ≈ 55% of revenue, each ±2pt
16. Account concentration: largest 24%, top 5 62% of wholesale revenue, each ±2pt

**Behavioural**

17. Returns arrive **after** their originating sale in every case, with the stated lag
    distributions by channel
18. Every PO deposit precedes its receipt date; effective DPO is negative
19. November and December show revenue above trend and gross margin below trend, every year
20. Underlying demand exceeds realised revenue in stockout periods on hero SKUs
21. April 2025 onward shows an ~8% product-cost step, isolated from freight and duty
22. The February 2025 launch cohort shows sell-through materially below the core range, and
    inventory ageing into the H2 2025 buckets

**Sign and range**

23. Value ranges and sign conventions plausible per column, not merely non-null
24. Favourable variance is positive regardless of whether the line is revenue or cost

---

## 10. Out of scope

Confirmed excluded, consistent with `docs/charter.md`:

- Multi-entity, multi-currency and consolidation logic
- FX rate dimensions and payables revaluation (ADR 0009)
- Personally identifiable customer data
- Live databases, hosted services, or anything requiring credentials to reproduce
- Cost-centre granularity per wholesale customer, marketing campaign, product family or SKU —
  these are analytical dimensions, not cost centres

---

## 11. Decision record

| ADR | Decision |
|---|---|
| 0001 | Interest accrues on the beginning-of-period debt balance |
| 0002 | Returns on an ASC 606 basis: refund liability and right-of-return asset |
| 0003 | Standard landed cost with PPV / freight / duty variances |
| 0004 | COGS boundary: outbound shipping and variable fulfilment in COGS, payment processing in opex |
| 0005 | Marketing as a constrained driver with a CAC response curve |
| 0006 | Three explicit CAC definitions |
| 0007 | Version and Scenario as two separate dimensions |
| 0008 | ABL revolver with a borrowing base, treated as a binding constraint |
| 0009 | Supplier contracts in USD; FX out of scope |
| 0010 | Channel contribution reporting with corporate costs unallocated |
