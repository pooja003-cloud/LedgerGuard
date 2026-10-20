"""
LedgerGuard: Draw the gross-to-net waterfall chart
==================================================

Builds the revenue bridge from data/ledgerguard.db and saves
docs/gross_to_net_bridge.png. Same figures as the Gross_to_Net sheet.

Run:  python src/06_make_charts.py
"""

import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt   # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "ledgerguard.db"
VIEWS_SQL = PROJECT_ROOT / "sql" / "02_exceptions.sql"
OUT_PATH = PROJECT_ROOT / "docs" / "gross_to_net_bridge.png"

TOTAL_COLOR = "#3D6CB3"     # blue: totals and subtotals
DEDUCT_COLOR = "#B23A3A"    # red: deductions
LEAK_COLOR = DEDUCT_COLOR   # same red as other deductions, to match the dashboard chart
INK, MUTED, GRID = "#1A1A1A", "#595959", "#E0E0E0"
AXIS_FLOOR = 200e6          # bridge charts start above zero so deductions are visible


def bridge():
    src = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn = sqlite3.connect(":memory:")
    src.backup(conn)
    src.close()
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='v_exceptions'").fetchone():
        conn.executescript(VIEWS_SQL.read_text())
    t = conn.execute("""
        SELECT SUM(units_shipped * contract_unit_price), SUM(gross_invoice),
               SUM(markdown_allowance), SUM(chargeback),
               SUM(units_returned * billed_unit_price)
        FROM shipments""").fetchone()
    disputed = conn.execute(
        "SELECT SUM(impact_usd) FROM v_exceptions WHERE exception_type='CHARGEBACK_OVER_CAP'"
    ).fetchone()[0]
    conn.close()
    contract, billed, markdowns, chargebacks, returns = t
    # (label, value, kind) - kind: total | deduct | leak
    return [
        ("Gross at\ncontract", contract, "total"),
        ("Pricing\nerrors", billed - contract, "leak"),
        ("Gross as\nbilled", billed, "total"),
        ("Markdowns", -markdowns, "deduct"),
        ("Routine\nchargebacks", -(chargebacks - disputed), "deduct"),
        ("Disputed\nchargebacks", -disputed, "leak"),
        ("Returns\ncredits", -returns, "deduct"),
        ("Net\nrevenue", billed - markdowns - chargebacks - returns, "total"),
    ]


def money(v):
    s = f"${abs(v) / 1e6:,.1f}M"
    return f"({s})" if v < 0 else s


def main():
    steps = bridge()
    plt.rcParams["font.family"] = "DejaVu Sans"
    fig, ax = plt.subplots(figsize=(10, 5.6), dpi=200)

    running = 0.0
    tops = []
    for i, (label, value, kind) in enumerate(steps):
        if kind == "total":
            bottom, height, running = AXIS_FLOOR, value - AXIS_FLOOR, value
            color = TOTAL_COLOR
        else:
            bottom, height = running + value, -value
            running += value
            color = LEAK_COLOR if kind == "leak" else DEDUCT_COLOR
        ax.bar(i, height, bottom=bottom, width=0.62, color=color, zorder=3)
        top = bottom + height
        tops.append(running)
        ax.text(i, top + 0.35e6, money(value), ha="center", va="bottom",
                fontsize=9.5, color=INK)

    # dashed connectors between bars
    for i in range(len(steps) - 1):
        ax.plot([i + 0.31, i + 0.69], [tops[i], tops[i]], color=MUTED, lw=0.8, ls=(0, (2, 2)), zorder=2)

    ax.set_xticks(range(len(steps)), [s[0] for s in steps], fontsize=9.5, color=INK)
    ax.set_ylim(AXIS_FLOOR, 230e6)
    ax.yaxis.set_major_formatter(lambda v, _: f"${v / 1e6:,.0f}M")
    ax.tick_params(axis="y", labelsize=9, colors=MUTED, length=0)
    ax.tick_params(axis="x", length=0)
    ax.grid(axis="y", color=GRID, lw=0.8, zorder=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(MUTED)

    fig.suptitle("Gross-to-Net Revenue Bridge, Sep 2025 - Oct 2026", x=0.065, ha="left",
                 fontsize=14, fontweight="bold", color=INK, y=0.97)
    ax.set_title("Northwind Devices (fictional, simulated data). Axis starts at $200M so deductions are visible.",
                 loc="left", fontsize=9, color=MUTED, pad=12)
    fig.tight_layout()
    fig.savefig(OUT_PATH, facecolor="white")
    print(f"Saved {OUT_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
