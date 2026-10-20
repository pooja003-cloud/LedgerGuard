# AI-assisted write-up

**Rules find the problems. Python does the math. AI only writes. A person reviews.**

`src/05_build_ai_brief.py` turns the verified exception register into structured briefs. Each brief gives Claude a role, a task, the verified figures and guardrails (use only the numbers given, never invent figures, mark anything missing as `[PLACEHOLDER]`).

| Brief | Produces |
|---|---|
| [brief_cfo_commentary.md](brief_cfo_commentary.md) | 200-word month-end commentary for the CFO |
| [brief_dispute_bestbuy.md](brief_dispute_bestbuy.md) | Dispute email for the two short-shipment deductions |
| [brief_rebill_amazon.md](brief_rebill_amazon.md) | Rebill request for the three underbilled invoices |

## Workflow

1. `python src/05_build_ai_brief.py`
2. Paste a brief into Claude.
3. Review the draft: check every number against the brief, fill in the placeholders, edit the tone.
4. Save the reviewed version in `docs/ai/drafts/` (created when the first reviewed draft is saved).

## Why it's built this way

- **Auditable:** every dollar amount, count and ratio in a brief is computed from the database, so each figure in a draft can be traced back to the exception register. The root causes in each brief's context (for example, the discount applied twice) are analyst findings from `sql/01_analysis.sql`.
- **No AI math:** the model never calculates, so it can't introduce numerical errors.
- **Human in the loop:** nothing is sent to a retailer or executive without review.
- **Easy to automate:** replacing the manual paste with one API call per brief is the only change needed to make this step fully automatic.
