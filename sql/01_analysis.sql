-- =====================================================================
-- LedgerGuard: Exploratory analysis
-- =====================================================================
-- Queries run against data/ledgerguard.db (SQLite), each followed by
-- the findings it produced. These findings shaped the exception rules
-- in sql/02_exceptions.sql.
--
--   Q1  Overall totals                Q6  Return rate by product
--   Q2  Revenue by retailer           Q7  Chargebacks by reason (+ drill-downs)
--   Q3  Revenue vs volume by product  Q8  Actual vs expected returns (JOIN)
--   Q4  Monthly trend                 Q9  AI laptop returns by month
--   Q5  Gross-to-net by retailer
-- =====================================================================


-- Q1. Overall totals ---------------------------------------------------
SELECT COUNT(*)                     AS invoices,
       SUM(units_shipped)           AS units,
       ROUND(SUM(gross_invoice), 0) AS gross_usd
FROM shipments;
-- Findings: 1,000 invoices, 329,590 units, $225.0M gross invoiced.


-- Q2. Gross invoiced by retailer, with share of total ------------------
SELECT retailer,
       COUNT(*)                                                 AS invoices,
       ROUND(SUM(gross_invoice), 0)                             AS gross_usd,
       ROUND(100.0 * SUM(gross_invoice)
             / SUM(SUM(gross_invoice)) OVER (), 2)              AS pct_of_total
FROM shipments
GROUP BY retailer
ORDER BY gross_usd DESC;
-- Findings: Amazon 41.8%, Best Buy 41.0%, Costco 17.2%.
-- Best Buy has more invoices than Amazon (414 vs 397) but less revenue.


-- Q3. Revenue vs volume by product -------------------------------------
SELECT product,
       SUM(units_shipped)                               AS units_shipped,
       ROUND(SUM(gross_invoice), 0)                     AS gross_usd,
       RANK() OVER (ORDER BY SUM(gross_invoice) DESC)   AS revenue_rank,
       RANK() OVER (ORDER BY SUM(units_shipped) DESC)   AS units_rank
FROM shipments
GROUP BY product
ORDER BY gross_usd DESC;
-- Findings:
-- Chromebooks ship almost as many units as AI laptops but earn about a
--   quarter of the revenue (low unit price).
-- The gaming desktop is #2 in revenue despite the lowest volume (high unit price).
-- So an error on an AI laptop or gaming desktop invoice costs far more per unit.


-- Q4. Monthly trend ----------------------------------------------------
SELECT strftime('%Y-%m', invoice_date) AS month,
       COUNT(*)                        AS invoices,
       ROUND(SUM(gross_invoice), 0)    AS gross_usd
FROM shipments
GROUP BY month
ORDER BY month;
-- Findings:
-- Holiday peak: Dec 2025 is the biggest month (133 invoices, $41.6M),
--   with Nov ($22.1M) as the ramp-up.
-- Back-to-school peak: Aug 2026 (126 invoices, $28.5M), Jul ($20.0M) ramp-up.
-- Post-holiday lull: Jan-Feb 2026 are lowest ($5.9M, $7.0M).
-- Dec is ~7x Jan, so forecasts must be seasonal (compare with the same
--   month last year), not a flat monthly average.
-- Oct 2026 ($7.3M) is a partial month (data ends Oct 15).


-- Q5. Gross-to-net by retailer (before returns) ------------------------
SELECT retailer,
       ROUND(SUM(gross_invoice), 0)                                     AS gross_usd,
       ROUND(SUM(markdown_allowance), 0)                                AS markdowns_usd,
       ROUND(SUM(chargeback), 0)                                        AS chargebacks_usd,
       ROUND(SUM(gross_invoice - markdown_allowance - chargeback), 0)   AS net_usd,
       ROUND(100.0 * SUM(markdown_allowance) / SUM(gross_invoice), 2)   AS markdown_pct,
       ROUND(100.0 * SUM(chargeback)         / SUM(gross_invoice), 2)   AS chargeback_pct,
       ROUND(100.0 * SUM(markdown_allowance + chargeback)
                   / SUM(gross_invoice), 2)                             AS total_deduction_pct
FROM shipments
GROUP BY retailer
ORDER BY gross_usd DESC;
-- Findings:
-- $225.0M gross -> $213.7M after ~$11.3M of markdowns and chargebacks
--   (returns credits of $5.1M come off later, in the full bridge).
-- Amazon has the highest markdown rate (5.08%), consistent with its 10% cap.
-- Costco has the lowest deductions (2.71%), consistent with its tighter terms.
-- Best Buy's chargeback rate (1.04%) is ~1.7x Amazon's (0.62%) under the same
--   3% cap -> investigate which chargeback reasons drive it (Q7).


-- Q6. Return rate by product -------------------------------------------
SELECT product,
       SUM(units_shipped)                                          AS units_shipped,
       SUM(units_returned)                                         AS units_returned,
       ROUND(100.0 * SUM(units_returned) / SUM(units_shipped), 2)  AS return_rate_pct
FROM shipments
GROUP BY product
ORDER BY return_rate_pct DESC;
-- Findings:
-- Chromebook (3.06%) and gaming desktop (1.59%) are in line with expected rates.
-- AI laptop returns are 2.55% vs ~2.0% expected: ~25% above plan for the full year.
-- A full-year average can hide a short spike -> break AI laptops down by month (Q9).


-- Q7. Chargebacks by reason --------------------------------------------
SELECT chargeback_reason,
       COUNT(*)                   AS chargebacks,
       ROUND(SUM(chargeback), 2)  AS total_usd,
       ROUND(AVG(chargeback), 2)  AS avg_usd,
       ROUND(MAX(chargeback), 2)  AS max_usd
FROM shipments
WHERE chargeback_reason <> 'No_Chargeback'
GROUP BY chargeback_reason
ORDER BY total_usd DESC;

-- Q7b. Drill-down: short-shipment invoices
SELECT *
FROM shipments
WHERE chargeback_reason = 'Short_Shipment';

-- Q7c. Drill-down: invoices billed below contract price
SELECT invoice_id, invoice_date, retailer, product, units_shipped,
       contract_unit_price, billed_unit_price,
       ROUND((contract_unit_price - billed_unit_price) * units_shipped, 2) AS underbilled_usd
FROM shipments
WHERE billed_unit_price < contract_unit_price;
-- Findings:
-- Short_Shipment: only 2 chargebacks, but they average ~$200K vs ~$2K for every
--   other reason (~100x). Total ~$401K, which explains Best Buy's rate in Q5.
-- Pricing: 3 Amazon AI laptop invoices in Black Friday week billed at $610.51 vs
--   $845 contract (72.25% = 15% discount applied twice). Underbilled: $752,478.


-- Q8. Actual vs expected return rate by retailer and product -----------
SELECT s.retailer,
       s.product,
       SUM(s.units_shipped)                                          AS units_shipped,
       SUM(s.units_returned)                                         AS units_returned,
       ROUND(1.0 * SUM(s.units_returned) / SUM(s.units_shipped), 4)  AS actual_return_rate,
       c.expected_return_rate,
       ROUND(1.0 * SUM(s.units_returned) / SUM(s.units_shipped)
             - c.expected_return_rate, 4)                            AS variance,
       ROUND(100.0 * (1.0 * SUM(s.units_returned) / SUM(s.units_shipped)
                      - c.expected_return_rate)
             / c.expected_return_rate, 1)                            AS pct_over_expected,
       CASE
         WHEN c.expected_return_rate IS NULL THEN 'No contract terms'
         WHEN 1.0 * SUM(s.units_returned) / SUM(s.units_shipped)
              > c.expected_return_rate * 1.10 THEN 'Investigate (>10% over)'
         WHEN 1.0 * SUM(s.units_returned) / SUM(s.units_shipped)
              > c.expected_return_rate THEN 'Slightly above'
         ELSE 'Within expected'
       END                                                           AS status
FROM shipments s
LEFT JOIN contract_terms c
       ON c.retailer = s.retailer
      AND c.product  = s.product
GROUP BY s.retailer, s.product, c.expected_return_rate
ORDER BY pct_over_expected DESC;
-- Findings:
-- AI laptop returns are 21-25% above expected at all three retailers -> likely a
--   product issue, not a retailer process issue.
-- Gaming desktop and Chromebook are within +/-5% of expected, except the
--   Costco gaming desktop, which runs 12% better than expected.
-- A 10% tolerance band keeps normal variation from being flagged.


-- Q9. AI laptop return rate by month vs weighted expected rate -------------
SELECT strftime('%Y-%m', s.invoice_date)                              AS month,
       SUM(s.units_shipped)                                           AS units_shipped,
       SUM(s.units_returned)                                          AS units_returned,
       ROUND(100.0 * SUM(s.units_returned) / SUM(s.units_shipped), 2) AS return_rate_pct,
       ROUND(100.0 * SUM(c.expected_return_rate * s.units_shipped)
                   / SUM(s.units_shipped), 2)                         AS expected_rate_pct
FROM shipments s
JOIN contract_terms c
  ON c.retailer = s.retailer
 AND c.product  = s.product
WHERE s.product = 'AI_Laptop_14'
GROUP BY month
ORDER BY month;
-- Findings:
-- March 2026: 8.71% returned vs 2.12% expected (4.1x). Every other month
--   is 1.8-2.5% against an expected 2.0-2.2%.
-- Returns were back to normal in April -> one faulty batch, not an ongoing issue.
-- Excluding March, AI laptops run ~2.1% (on plan): the full-year 2.55% in Q6 was
--   driven almost entirely by this one month.
-- ~601 excess units returned (795 actual vs ~194 expected) = ~$506K at
--   contract price (an upper bound: returned units keep some recovery value).
