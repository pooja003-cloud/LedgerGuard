"""
LedgerGuard: Generate the synthetic dataset
===========================================

Creates three tables that mimic how a PC hardware vendor sells through
big-box retailers (Best Buy, Amazon, Costco):

    data/raw/contract_terms.csv     -> the "rulebook" agreed with each retailer
    data/raw/shipments.csv          -> ~1,000 invoices, Sep 2025 to Oct 2026
    data/answer_key/answer_key.csv  -> invoices with planted problems (used only for validation)

All data is SIMULATED. Northwind Devices is a fictional company; prices,
products and contract terms are illustrative.

Run:  python src/01_generate_data.py
"""

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# Fixed seed: every run produces identical data, so results are reproducible.
rng = np.random.default_rng(42)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
KEY_DIR = PROJECT_ROOT / "data" / "answer_key"

N_INVOICES = 1000
START_DATE = date(2025, 9, 1)
END_DATE = date(2026, 10, 15)

RETAILERS = ["BestBuy_US", "Amazon_US", "Costco_Wholesale"]
RETAILER_SHARE = [0.40, 0.40, 0.20]          # share of invoices per retailer
PRODUCTS = ["AI_Laptop_14", "Gaming_Desktop_X", "Chromebook_Edu"]

CHARGEBACK_REASONS = ["Late_Delivery", "Damaged_Packaging", "Labeling_Error", "ASN_Mismatch"]


# ---------------------------------------------------------------------------
# 1. CONTRACT TERMS (the rulebook)
# ---------------------------------------------------------------------------
# Each retailer negotiates its own price and limits for each product.
# Costco pays less (volume buyer) and has tighter promo budgets.
def build_contract_terms() -> pd.DataFrame:
    prices = {
        "BestBuy_US":       {"AI_Laptop_14": 850, "Gaming_Desktop_X": 1300, "Chromebook_Edu": 240},
        "Amazon_US":        {"AI_Laptop_14": 845, "Gaming_Desktop_X": 1290, "Chromebook_Edu": 235},
        "Costco_Wholesale": {"AI_Laptop_14": 820, "Gaming_Desktop_X": 1250, "Chromebook_Edu": 230},
    }
    max_markdown_pct = {"BestBuy_US": 0.08, "Amazon_US": 0.10, "Costco_Wholesale": 0.05}
    max_chargeback_pct = {"BestBuy_US": 0.03, "Amazon_US": 0.03, "Costco_Wholesale": 0.02}
    base_return_rate = {"AI_Laptop_14": 0.020, "Gaming_Desktop_X": 0.015, "Chromebook_Edu": 0.030}

    rows = []
    for r in RETAILERS:
        for p in PRODUCTS:
            # Costco's generous return policy means slightly more returns
            ret_rate = base_return_rate[p] + (0.005 if r == "Costco_Wholesale" else 0)
            rows.append({
                "Retailer": r,
                "Product": p,
                "Contract_Unit_Price": prices[r][p],
                "Max_Markdown_Pct": max_markdown_pct[r],
                "Max_Chargeback_Pct": max_chargeback_pct[r],
                "Expected_Return_Rate": round(ret_rate, 3),
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 2. SEASONALITY (when do invoices happen?)
# ---------------------------------------------------------------------------
# Consumer electronics follow the retail calendar. We give each day a weight
# and sample invoice dates in proportion to it.
def season_of(d: date) -> str:
    if date(2025, 11, 24) <= d <= date(2025, 12, 31):
        return "holiday"
    if date(2026, 7, 15) <= d <= date(2026, 9, 10):
        return "back_to_school"
    if date(2026, 1, 1) <= d <= date(2026, 2, 28):
        return "post_holiday_lull"
    if date(2026, 10, 1) <= d <= date(2026, 10, 15):
        return "holiday_ramp"
    return "normal"


SEASON_WEIGHT = {"holiday": 2.2, "back_to_school": 1.8, "post_holiday_lull": 0.7,
                 "holiday_ramp": 1.3, "normal": 1.0}

# During back-to-school, students buy Chromebooks and laptops, not gaming desktops.
SEASON_PRODUCT_MIX = {
    "back_to_school": [0.40, 0.10, 0.50],
    "holiday":        [0.40, 0.30, 0.30],
}
DEFAULT_PRODUCT_MIX = [0.40, 0.20, 0.40]


def sample_invoice_dates(n: int) -> list:
    all_days = [START_DATE + timedelta(days=i) for i in range((END_DATE - START_DATE).days + 1)]
    weights = np.array([SEASON_WEIGHT[season_of(d)] for d in all_days])
    picks = rng.choice(len(all_days), size=n, p=weights / weights.sum())
    return sorted(all_days[i] for i in picks)


# ---------------------------------------------------------------------------
# 3. BUILD ONE NORMAL INVOICE
# ---------------------------------------------------------------------------
def build_invoice(d: date, terms: pd.DataFrame, retailer=None, product=None, units=None) -> dict:
    season = season_of(d)
    peak = season in ("holiday", "back_to_school")

    retailer = retailer or rng.choice(RETAILERS, p=RETAILER_SHARE)
    product = product or rng.choice(PRODUCTS, p=SEASON_PRODUCT_MIX.get(season, DEFAULT_PRODUCT_MIX))
    t = terms[(terms.Retailer == retailer) & (terms.Product == product)].iloc[0]

    # Units: most shipments are a few hundred units, a few are very large.
    # A lognormal distribution produces that "long right tail" naturally.
    if units is None:
        units = rng.lognormal(mean=5.5, sigma=0.6) * (1.3 if peak else 1.0)
        units = int(np.clip(units, 50, 2000))

    contract_price = float(t.Contract_Unit_Price)
    billed_price = contract_price                    # normally billed exactly at contract
    gross = units * billed_price

    # Markdown allowance: promo money, normally well under the contract cap.
    # In peak season ~15% of invoices run a big (but legitimate) promo close to the cap.
    # These are "benign outliers": large, but NOT a problem.
    cap = float(t.Max_Markdown_Pct)
    if peak and rng.random() < 0.15:
        markdown_pct = rng.uniform(0.85, 1.0) * cap
    else:
        markdown_pct = rng.uniform(0.2, 0.75) * cap
    markdown = gross * markdown_pct

    # Chargebacks: ~40% of invoices have none; the rest are small fees.
    if rng.random() < 0.40:
        chargeback, reason = 0.0, "No_Chargeback"
    else:
        chargeback = gross * rng.uniform(0.001, 0.6 * float(t.Max_Chargeback_Pct))
        reason = rng.choice(CHARGEBACK_REASONS)

    # Returns: each unit has a small chance of coming back defective.
    returned = int(rng.binomial(units, float(t.Expected_Return_Rate)))

    return {
        "Invoice_Date": d.isoformat(),
        "Retailer": retailer,
        "Product": product,
        "Units_Shipped": units,
        "Contract_Unit_Price": contract_price,
        "Billed_Unit_Price": round(billed_price, 2),
        "Gross_Invoice": round(gross, 2),
        "Markdown_Allowance": round(markdown, 2),
        "Chargeback": round(chargeback, 2),
        "Chargeback_Reason": reason,
        "Units_Returned": returned,
    }


# ---------------------------------------------------------------------------
# 4. PLANT THE THREE PROBLEMS
# ---------------------------------------------------------------------------
def plant_anomalies(df: pd.DataFrame, terms: pd.DataFrame) -> pd.DataFrame:
    key_rows = []
    dates = pd.to_datetime(df.Invoice_Date)

    # --- Scenario A: Black Friday double-discount glitch (Amazon, Nov 24-30, 2025)
    # A 15% promo code was applied twice: price billed = contract x 0.85 x 0.85 = 72.25%
    window = df.index[(dates >= "2025-11-24") & (dates <= "2025-11-30")]
    for idx in rng.choice(window, size=3, replace=False):
        units = int(rng.integers(800, 1200))
        row = build_invoice(dates[idx].date(), terms, "Amazon_US", "AI_Laptop_14", units)
        row["Billed_Unit_Price"] = round(row["Contract_Unit_Price"] * 0.85 * 0.85, 2)
        row["Gross_Invoice"] = round(units * row["Billed_Unit_Price"], 2)
        # Keep the promo money proportional to the (lower) invoice, so the ONLY problem is price
        row["Markdown_Allowance"] = round(row["Markdown_Allowance"] * 0.85 * 0.85, 2)
        df.loc[idx, list(row)] = list(row.values())
        leakage = (row["Contract_Unit_Price"] - row["Billed_Unit_Price"]) * units
        key_rows.append((idx, "A_Double_Discount",
                         "15% promo applied twice; billed at 72.25% of contract price",
                         round(leakage, 2)))

    # --- Scenario B: Phantom short-shipment (Best Buy, August 2026)
    # Retailer claims half the container never arrived and deducts ~50% of the invoice.
    window = df.index[(dates >= "2026-08-01") & (dates <= "2026-08-31")]
    for idx in rng.choice(window, size=2, replace=False):
        units = int(rng.integers(1400, 1600))
        row = build_invoice(dates[idx].date(), terms, "BestBuy_US", "Chromebook_Edu", units)
        row["Chargeback"] = round(row["Gross_Invoice"] * rng.uniform(0.48, 0.55), 2)
        row["Chargeback_Reason"] = "Short_Shipment"
        df.loc[idx, list(row)] = list(row.values())
        key_rows.append((idx, "B_Phantom_Short_Shipment",
                         "Short-shipment deduction of ~50% of invoice; fully disputable",
                         row["Chargeback"]))

    # --- Scenario C: Defective AI laptop batch (March 2026, all retailers)
    # Return rate jumps from ~2% to ~9% for every AI laptop invoice dated in March.
    mask = (dates.dt.strftime("%Y-%m") == "2026-03") & (df.Product == "AI_Laptop_14")
    for idx in df.index[mask]:
        units = int(df.loc[idx, "Units_Shipped"])
        df.loc[idx, "Units_Returned"] = int(rng.binomial(units, 0.09))
        t = terms[(terms.Retailer == df.loc[idx, "Retailer"]) & (terms.Product == "AI_Laptop_14")].iloc[0]
        excess_units = df.loc[idx, "Units_Returned"] - units * t.Expected_Return_Rate
        key_rows.append((idx, "C_Defective_Batch",
                         "AI laptop return rate ~9% vs ~2% expected",
                         round(max(excess_units, 0) * t.Contract_Unit_Price, 2)))

    key = pd.DataFrame(key_rows, columns=["row_idx", "Scenario", "Description", "Expected_Leakage_USD"])
    return df, key


# ---------------------------------------------------------------------------
# 5. RUN EVERYTHING
# ---------------------------------------------------------------------------
def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    KEY_DIR.mkdir(parents=True, exist_ok=True)

    terms = build_contract_terms()
    shipments = pd.DataFrame([build_invoice(d, terms) for d in sample_invoice_dates(N_INVOICES)])
    shipments, key = plant_anomalies(shipments, terms)

    # Invoice IDs are assigned after sorting by date, like a real billing system.
    shipments.insert(0, "Invoice_ID", [f"INV-{100001 + i}" for i in range(len(shipments))])
    key.insert(0, "Invoice_ID", shipments.loc[key.row_idx, "Invoice_ID"].values)
    key = key.drop(columns="row_idx")

    terms.to_csv(RAW_DIR / "contract_terms.csv", index=False)
    shipments.to_csv(RAW_DIR / "shipments.csv", index=False)
    key.to_csv(KEY_DIR / "answer_key.csv", index=False)

    print(f"shipments.csv      {len(shipments):>5} rows  "
          f"({shipments.Invoice_Date.min()} to {shipments.Invoice_Date.max()})")
    print(f"contract_terms.csv {len(terms):>5} rows")
    print(f"answer_key.csv     {len(key):>5} planted rows (for validation only)")
    print(f"Gross invoiced:    ${shipments.Gross_Invoice.sum():,.0f}")


if __name__ == "__main__":
    main()
