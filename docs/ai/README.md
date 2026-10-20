# AI-assisted write-up

**Rules find the problems. Python does the math. AI only writes. A person reviews.**

`src/05_build_ai_brief.py` turns the verified exception register into structured briefs. Each brief gives Claude a role, a task, the verified figures and guardrails (use only the numbers given, never invent figures, mark anything missing as `[PLACEHOLDER]`).

| Brief | Draft | Produces |
|---|---|---|
| [brief_cfo_commentary.md](brief_cfo_commentary.md) | [cfo_commentary.md](drafts/cfo_commentary.md) | 200-word month-end commentary for the CFO |
| [brief_dispute_bestbuy.md](brief_dispute_bestbuy.md) | [dispute_bestbuy.md](drafts/dispute_bestbuy.md) | Dispute email for the two short-shipment deductions |
| [brief_rebill_amazon.md](brief_rebill_amazon.md) | [rebill_amazon.md](drafts/rebill_amazon.md) | Rebill request for the three underbilled invoices |

## Workflow

1. `python src/05_build_ai_brief.py`
2. Paste a brief into Claude and save the draft in `docs/ai/drafts/` under the brief's name (without `brief_`).
3. `python src/07_check_ai_drafts.py` checks that every number in each draft appears in its brief.
4. A person reviews tone and facts, fills in the placeholders and signs off the checklist at the bottom of each draft.

## Why it's built this way

- **Auditable:** every dollar amount, count and ratio in a brief is computed from the database, so each figure in a draft can be traced back to the exception register. The root causes in each brief's context (for example, the discount applied twice) are analyst findings from `sql/01_analysis.sql`.
- **No AI math:** the model never calculates, and an automated check rejects any draft containing a number that isn't in its brief.
- **Human in the loop:** nothing is sent to a retailer or executive without review.
- **Easy to automate:** replacing the manual paste with one API call per brief is the only change needed to make this step fully automatic.
