# Memo: Revenue Leakage Review, Sep 2025 – Oct 2026

**To:** CFO, Northwind Devices (fictional)
**Prepared by:** Pooja Master
**Date:** October 19, 2026
**Re:** $1.66M of revenue leakage found; up to $1.15M may be recoverable

> Simulated data. Northwind Devices is a fictional company.

---

## Bottom line

We found $1.66M of revenue leakage over the past 13 months, about 0.7% of what we billed. Up to $1.15M may be recoverable, by asking Amazon to accept a rebill and by disputing two Best Buy deductions. The remaining $0.51M came from a faulty laptop batch; it is already reflected in net revenue and needs no further charge. I am asking for approval to start the rebill request and the disputes this month.

## What we found

**Amazon was undercharged.** During Black Friday week 2025, a 15% discount was applied twice on three AI laptop invoices, so Amazon paid $611 per unit instead of $845. Because the error was ours and the invoices are about 11 months old, Amazon may not accept the full rebill.

**Best Buy took two unusually large deductions.** In August 2026, Best Buy deducted about $200K twice for "short shipments." A typical deduction is around $2K, and both are far above our contract limit. We recover this only if the disputes succeed.

**One batch of AI laptops was faulty.** Laptops shipped in March 2026 were returned at four times the normal rate at all three retailers, so the cause was the product, not the retailer. Returns were back to normal in April, so this looks like a one-off.

| Issue | Retailer | When | Impact | Recoverable? |
|---|---|---|---|---|
| Discount applied twice | Amazon | Black Friday week 2025 | $752K | Possibly, if Amazon accepts the rebill |
| Short-shipment deductions | Best Buy | Aug 2026 | $401K | Only if the disputes are won |
| Faulty AI laptop batch | All | Mar 2026 | $506K | No; already in net revenue |
| **Total** | | | **$1.66M** | **Up to $1.15M** |

## Recommended actions

1. **Request a rebill from Amazon for $752K.** Owner: Billing. By October 31.
2. **Dispute the two Best Buy deductions ($401K)** using proof of delivery for both shipments, before the dispute window closes. Owner: Deductions team. By October 31.
3. **Treat the $506K faulty batch as a one-time revenue variance.** It is already included in returns credits, so no additional charge is needed, and the ongoing returns reserve rate can stay as it is because returns are back on plan. The $506K values the extra returns at full contract price, so the true loss is somewhat lower once returned units are refurbished or sent back to the supplier. Owner: FP&A and Accounting. By October month-end close.
4. **Prevent a repeat.** Stop any invoice priced below contract before it is sent, and ask Quality to confirm what caused the March defect. Owner: Billing and Quality. By November 30.

## Risk to watch

If the laptop defect returned during the holidays, extra returns could reduce revenue by up to $1.9M, based on the roughly 34,000 AI laptops we expect to ship in November and December. Nothing suggests this will happen, but the impact would be large, so I recommend tracking AI laptop returns weekly through December.

## How this was found

All 1,000 invoices were checked against each retailer's contract terms using four simple rules: price below contract, promotions over the limit, deductions over the limit, and returns well above normal. The rules were tested against known problem cases and caught all of them with no false alarms ([validation results](validation_results.md)). Every flagged item still needs review before action. Invoice-level detail is in the workbook ([LedgerGuard_Analysis_completed.xlsx](../excel/LedgerGuard_Analysis_completed.xlsx)).
