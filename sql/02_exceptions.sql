-- =====================================================================
-- LedgerGuard: Exception register
-- =====================================================================
-- Every invoice is checked against its contract terms with four rules.
-- Each rule returns the SAME columns, so UNION ALL can stack them into
-- one list: the exception register that feeds the Excel report.
--
--   Rule 1  PRICE_BELOW_CONTRACT  billed price < contract price
--   Rule 2  MARKDOWN_OVER_CAP     markdown % of gross > contract cap
--   Rule 3  CHARGEBACK_OVER_CAP   chargeback % of gross > contract cap
--   Rule 4  RETURN_SPIKE          product's return rate in a month is
--                                 > 1.5x expected (checked per product-month,
--                                 not per invoice, so one small invoice
--                                 can't trigger it by chance)
--
-- impact_usd is always POSITIVE = revenue lost or at risk.
-- =====================================================================

DROP VIEW IF EXISTS v_exceptions;

CREATE VIEW v_exceptions AS

-- Join every shipment to its contract once, and reuse it in each rule
WITH base AS (
    SELECT s.*,
           c.max_markdown_pct,
           c.max_chargeback_pct,
           c.expected_return_rate
    FROM shipments s
    JOIN contract_terms c
      ON c.retailer = s.retailer
     AND c.product  = s.product
),

-- Rule 4 needs a monthly view first: return rate per product per month
product_month AS (
    SELECT product,
           strftime('%Y-%m', invoice_date)                         AS month,
           1.0 * SUM(units_returned) / SUM(units_shipped)          AS actual_rate,
           SUM(expected_return_rate * units_shipped) / SUM(units_shipped) AS expected_rate
    FROM base
    GROUP BY product, month
),

spike_months AS (
    SELECT * FROM product_month
    WHERE actual_rate > expected_rate * 1.5
)

-- Rule 1: billed below contract price -----------------------------------
SELECT invoice_id, invoice_date, retailer, product,
       'PRICE_BELOW_CONTRACT'                                     AS exception_type,
       ROUND((contract_unit_price - billed_unit_price) * units_shipped, 2) AS impact_usd,
       'Rebill retailer for the price difference'                 AS recovery_action,
       printf('Billed $%.2f vs contract $%.2f (%.1f%% of contract) on %d units',
              billed_unit_price, contract_unit_price,
              100.0 * billed_unit_price / contract_unit_price, units_shipped) AS reason
FROM base
WHERE billed_unit_price < contract_unit_price

UNION ALL

-- Rule 2: markdown above contract cap -----------------------------------
SELECT invoice_id, invoice_date, retailer, product,
       'MARKDOWN_OVER_CAP',
       ROUND(markdown_allowance - max_markdown_pct * gross_invoice, 2),
       'Recover markdown in excess of contract cap',
       printf('Markdown %.1f%% of gross vs %.1f%% cap',
              100.0 * markdown_allowance / gross_invoice, 100.0 * max_markdown_pct)
FROM base
WHERE markdown_allowance > max_markdown_pct * gross_invoice

UNION ALL

-- Rule 3: chargeback above contract cap ---------------------------------
-- The whole deduction is disputed: a claim this size needs proof (e.g. the
-- warehouse shipping log / proof of delivery) before it is accepted.
SELECT invoice_id, invoice_date, retailer, product,
       'CHARGEBACK_OVER_CAP',
       ROUND(chargeback, 2),
       'Dispute deduction; request proof and check shipping log',
       printf('%s chargeback of $%.0f = %.1f%% of gross vs %.1f%% cap',
              chargeback_reason, chargeback,
              100.0 * chargeback / gross_invoice, 100.0 * max_chargeback_pct)
FROM base
WHERE chargeback > max_chargeback_pct * gross_invoice

UNION ALL

-- Rule 4: return spike (every invoice in a spike product-month) ----------
-- Impact = returns above the expected level, valued at contract price.
SELECT b.invoice_id, b.invoice_date, b.retailer, b.product,
       'RETURN_SPIKE',
       ROUND(MAX(b.units_returned - b.expected_return_rate * b.units_shipped, 0)
             * b.contract_unit_price, 2),
       'Raise with quality team; review returns reserve',
       printf('%s returns in %s ran %.1f%% vs %.1f%% expected',
              b.product, m.month, 100.0 * m.actual_rate, 100.0 * m.expected_rate)
FROM base b
JOIN spike_months m
  ON m.product = b.product
 AND m.month   = strftime('%Y-%m', b.invoice_date);


-- =====================================================================
-- Summary: how much is at stake, by exception type
-- =====================================================================
-- SELECT exception_type,
--        COUNT(*)                    AS invoices,
--        ROUND(SUM(impact_usd), 0)   AS impact_usd
-- FROM v_exceptions
-- GROUP BY exception_type
-- ORDER BY impact_usd DESC;
