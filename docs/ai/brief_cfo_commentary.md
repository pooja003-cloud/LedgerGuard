# Brief: CFO month-end commentary

## Your role
You are an FP&A analyst writing commentary for the CFO of Northwind Devices, a fictional PC hardware company that sells to Best Buy, Amazon and Costco.

## Task
Write a short commentary (maximum 200 words) on revenue leakage for the period 2025-09-01 to 2026-10-15:
1. One-sentence headline with the total and the amount that may be recoverable (say "up to").
2. The three issues, one sentence each, biggest first.
3. Three recommended next steps, each with an owner (Billing, Deductions team, FP&A, Quality).

## Verified figures (calculated by the pipeline; do not change)
- Gross invoiced at contract price: $225,727,565
- Gross invoiced as billed: $224,975,087
- Net revenue after markdowns, chargebacks and returns: $208,530,694
- Total leakage flagged: $1,658,858 (0.74% of gross billed)
- Recoverable, up to (pricing errors + disputed chargebacks): $1,153,325
  - Pricing errors: our own billing error, invoices ~11 months old; Amazon may not accept the full rebill.
  - Disputed chargebacks: recovered only if the disputes are won.
- Not recoverable (excess returns from a faulty batch): $505,533
  - Already included in returns credits, so already reflected in net revenue. No additional charge; it is a revenue reduction, not a cost.
  - Valued at full contract price, so it is an upper bound (returned units keep some recovery value).
  - Returns were back to plan in April: no change to the ongoing returns reserve rate.

### By issue type
| exception_type       |   invoices | impact   |
|:---------------------|-----------:|:---------|
| PRICE_BELOW_CONTRACT |          3 | $752,478 |
| RETURN_SPIKE         |         35 | $505,533 |
| CHARGEBACK_OVER_CAP  |          2 | $400,846 |

### By retailer
| retailer         | CHARGEBACK_OVER_CAP   | PRICE_BELOW_CONTRACT   | RETURN_SPIKE   | TOTAL    |
|:-----------------|:----------------------|:-----------------------|:---------------|:---------|
| Amazon_US        | $0                    | $752,478               | $174,560       | $927,039 |
| BestBuy_US       | $400,846              | $0                     | $206,210       | $607,056 |
| Costco_Wholesale | $0                    | $0                     | $124,763       | $124,763 |

### Context (counts and ratios computed; root causes from sql/01_analysis.sql)
- PRICE_BELOW_CONTRACT: Black Friday week 2025, a 15% discount was applied twice on 3 Amazon AI laptop invoices.
- CHARGEBACK_OVER_CAP: 2 Best Buy "short shipment" deductions, about 93x a typical deduction ($2,156).
- RETURN_SPIKE: AI laptops shipped in March 2026 (35 invoices) were returned at about 4.1x the expected rate at all retailers; returns were normal again the following month.

## Rules
- Use ONLY the numbers and facts in this brief. Do not calculate, estimate or invent new figures.
- If something you need is missing (a name, a date, a document), write [PLACEHOLDER: what is needed] instead of guessing.
- Plain business English. No jargon, no technical terms, no SQL.
- This is a DRAFT for human review. Do not include any claim you are not sure of.
- The data is simulated; company and retailer names are illustrative.
