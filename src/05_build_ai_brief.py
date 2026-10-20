"""
LedgerGuard - AI brief builder
==============================

Design rule: the SQL rules FIND the problems and Python does ALL the math.
The AI only WRITES (commentary, letters) from numbers it is given, and a
person reviews every draft before it is used.

This script turns the verified exception register into structured prompts
("briefs") that can be pasted into Claude:

    docs/ai/brief_cfo_commentary.md   month-end commentary for the CFO
    docs/ai/brief_dispute_bestbuy.md  dispute email for invalid deductions
    docs/ai/brief_rebill_amazon.md    rebill request for underbilled invoices

Paste a brief into Claude, review and edit the draft, then save the final
version in docs/ai/drafts/. To automate later, replace the manual paste with
one API call per brief; nothing else in the pipeline changes.

Run:  python src/05_build_ai_brief.py
"""

import sqlite3
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "ledgerguard.db"
VIEWS_SQL = PROJECT_ROOT / "sql" / "02_exceptions.sql"
OUT_DIR = PROJECT_ROOT / "docs" / "ai"

# Guardrails included in every brief
RULES = """## Rules
- Use ONLY the numbers and facts in this brief. Do not calculate, estimate or invent new figures.
- If something you need is missing (a name, a date, a document), write [PLACEHOLDER: what is needed] instead of guessing.
- Plain business English. No jargon, no technical terms, no SQL.
- This is a DRAFT for human review. Do not include any claim you are not sure of.
- The data is simulated; company and retailer names are illustrative."""


def usd(x: float) -> str:
    return f"${x:,.0f}"


def load():
    src = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn = sqlite3.connect(":memory:")
    src.backup(conn)
    src.close()
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='v_exceptions'").fetchone():
        conn.executescript(VIEWS_SQL.read_text())
    exc = pd.read_sql("""
        SELECT e.*, s.units_shipped, s.contract_unit_price, s.billed_unit_price,
               s.gross_invoice, s.chargeback_reason, s.units_returned,
               c.max_chargeback_pct, c.expected_return_rate
        FROM v_exceptions e
        JOIN shipments s USING (invoice_id)
        JOIN contract_terms c ON c.retailer = s.retailer AND c.product = s.product
        ORDER BY e.impact_usd DESC""", conn)
    totals = pd.read_sql("""
        SELECT SUM(units_shipped * contract_unit_price)          AS gross_contract,
               SUM(gross_invoice)                                 AS gross_billed,
               SUM(markdown_allowance)                            AS markdowns,
               SUM(chargeback)                                    AS chargebacks,
               SUM(units_returned * billed_unit_price)            AS returns_credit,
               MIN(invoice_date) AS start_date, MAX(invoice_date) AS end_date
        FROM shipments""", conn).iloc[0]
    # Average chargeback within the contract cap: the "typical" deduction
    totals["typical_chargeback"] = conn.execute("""
        SELECT AVG(s.chargeback)
        FROM shipments s
        JOIN contract_terms c ON c.retailer = s.retailer AND c.product = s.product
        WHERE s.chargeback > 0 AND s.chargeback <= c.max_chargeback_pct * s.gross_invoice
        """).fetchone()[0]
    conn.close()
    return exc, totals


def months_between(start: str, end: str) -> int:
    return round((pd.Timestamp(end) - pd.Timestamp(start)).days / 30.44)


def table(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False)


def brief_cfo(exc, t) -> str:
    by_type = (exc.groupby("exception_type")
                  .agg(invoices=("invoice_id", "count"), impact=("impact_usd", "sum"))
                  .reset_index().sort_values("impact", ascending=False))
    by_type["impact"] = by_type["impact"].map(usd)
    by_ret = (exc.pivot_table(index="retailer", columns="exception_type",
                              values="impact_usd", aggfunc="sum", fill_value=0))
    by_ret["TOTAL"] = by_ret.sum(axis=1)
    by_ret = by_ret.map(usd).reset_index()

    total = exc.impact_usd.sum()
    recoverable = exc.loc[exc.exception_type != "RETURN_SPIKE", "impact_usd"].sum()
    net = t.gross_billed - t.markdowns - t.chargebacks - t.returns_credit
    pr = exc[exc.exception_type == "PRICE_BELOW_CONTRACT"]
    cb = exc[exc.exception_type == "CHARGEBACK_OVER_CAP"]
    rs = exc[exc.exception_type == "RETURN_SPIKE"]
    pr_age = months_between(pr.invoice_date.min(), t.end_date)
    cb_multiple = cb.impact_usd.mean() / t.typical_chargeback
    spike_month = pd.to_datetime(rs.invoice_date.min()).strftime("%B %Y")
    spike_multiple = rs.units_returned.sum() / (rs.expected_return_rate * rs.units_shipped).sum()

    return f"""# Brief: CFO month-end commentary

## Your role
You are an FP&A analyst writing commentary for the CFO of Northwind Devices, a fictional PC hardware company that sells to Best Buy, Amazon and Costco.

## Task
Write a short commentary (maximum 200 words) on revenue leakage for the period {t.start_date} to {t.end_date}:
1. One-sentence headline with the total and the amount that may be recoverable (say "up to").
2. The three issues, one sentence each, biggest first.
3. Three recommended next steps, each with an owner (Billing, Deductions team, FP&A, Quality).

## Verified figures (calculated by the pipeline; do not change)
- Gross invoiced at contract price: {usd(t.gross_contract)}
- Gross invoiced as billed: {usd(t.gross_billed)}
- Net revenue after markdowns, chargebacks and returns: {usd(net)}
- Total leakage flagged: {usd(total)} ({total / t.gross_billed:.2%} of gross billed)
- Recoverable, up to (pricing errors + disputed chargebacks): {usd(recoverable)}
  - Pricing errors: our own billing error, invoices ~{pr_age} months old; Amazon may not accept the full rebill.
  - Disputed chargebacks: recovered only if the disputes are won.
- Not recoverable (excess returns from a faulty batch): {usd(total - recoverable)}
  - Already included in returns credits, so already reflected in net revenue. No additional charge; it is a revenue reduction, not a cost.
  - Valued at full contract price, so it is an upper bound (returned units keep some recovery value).
  - Returns were back to plan in April: no change to the ongoing returns reserve rate.

### By issue type
{table(by_type)}

### By retailer
{table(by_ret)}

### Context (counts and ratios computed; root causes from sql/01_analysis.sql)
- PRICE_BELOW_CONTRACT: Black Friday week 2025, a 15% discount was applied twice on {len(pr)} Amazon AI laptop invoices.
- CHARGEBACK_OVER_CAP: {len(cb)} Best Buy "short shipment" deductions, about {cb_multiple:,.0f}x a typical deduction ({usd(t.typical_chargeback)}).
- RETURN_SPIKE: AI laptops shipped in {spike_month} ({rs.invoice_id.nunique()} invoices) were returned at about {spike_multiple:.1f}x the expected rate at all retailers; returns were normal again the following month.

{RULES}
"""


def brief_dispute(exc, t) -> str:
    cb = exc[exc.exception_type == "CHARGEBACK_OVER_CAP"].copy()
    cap = cb.max_chargeback_pct.max()
    share = (cb.impact_usd / cb.gross_invoice)
    rows = pd.DataFrame({
        "Invoice": cb.invoice_id,
        "Invoice date": cb.invoice_date,
        "Product": cb["product"],
        "Units invoiced": cb.units_shipped.map("{:,}".format),
        "Invoice amount": cb.gross_invoice.map(usd),
        "Deduction taken": cb.impact_usd.map(usd),
        "Reason given": cb.chargeback_reason,
        "Deduction % of invoice": share.map("{:.1%}".format),
    })
    return f"""# Brief: Dispute email to Best Buy

## Your role
You are a deductions analyst at Northwind Devices, a fictional PC hardware company, writing to the Best Buy accounts payable / vendor deductions team.

## Task
Draft a polite, firm email (maximum 180 words) disputing the deductions below and requesting repayment of {usd(cb.impact_usd.sum())} in total.
- Reference each invoice number and deduction amount.
- State that proof of delivery is attached as [PLACEHOLDER: proof of delivery documents]. Only say the full quantity was shipped if this is confirmed: [PLACEHOLDER: confirm the warehouse shipping log shows the full quantity shipped]. This pipeline has no shipping records.
- Ask them to provide their receiving records if they believe the shipment was short.
- Ask for a response by [PLACEHOLDER: response date].
- Include a clear subject line.

## Verified invoice data
{table(rows)}

## Context
- Our contract allows chargebacks up to {cap:.0%} of the invoice; these are about {share.mean():.0%}.
- A typical deduction on our account (within the contract cap) is about {usd(t.typical_chargeback)}.

{RULES}
"""


def brief_rebill(exc) -> str:
    pr = exc[exc.exception_type == "PRICE_BELOW_CONTRACT"].copy()
    rows = pd.DataFrame({
        "Invoice": pr.invoice_id,
        "Invoice date": pr.invoice_date,
        "Product": pr["product"],
        "Units": pr.units_shipped.map("{:,}".format),
        "Contract price": pr.contract_unit_price.map("${:,.2f}".format),
        "Price billed": pr.billed_unit_price.map("${:,.2f}".format),
        "Amount underbilled": pr.impact_usd.map("${:,.2f}".format),
    })
    return f"""# Brief: Rebill request to Amazon

## Your role
You are a billing analyst at Northwind Devices, a fictional PC hardware company, writing to the Amazon vendor accounts payable team.

## Task
Draft a short, professional email (maximum 150 words) explaining that {len(pr)} invoices were billed below the agreed contract price because a promotional discount was applied twice in our billing system, and requesting that Amazon accept corrected invoices for the difference of {usd(pr.impact_usd.sum())}, attached as [PLACEHOLDER: corrected invoice numbers].
- Take responsibility for the error; the tone should be cooperative, not accusatory.
- Acknowledge the invoices are from {pd.to_datetime(pr.invoice_date.min()).strftime("%B %Y")} and offer to discuss timing of payment.
- List each invoice and the amount underbilled.
- Include a clear subject line.

## Verified invoice data
{table(rows)}

{RULES}
"""


def main():
    exc, totals = load()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    briefs = {
        "brief_cfo_commentary.md": brief_cfo(exc, totals),
        "brief_dispute_bestbuy.md": brief_dispute(exc, totals),
        "brief_rebill_amazon.md": brief_rebill(exc),
    }
    for name, text in briefs.items():
        (OUT_DIR / name).write_text(text)
        print(f"Saved docs/ai/{name}")


if __name__ == "__main__":
    main()
