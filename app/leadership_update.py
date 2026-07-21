"""
Generates a founder/leadership-ready summary combining both boards.

Interpretation of "help prepare data for leadership updates" (documented
further in the Decision Log): a one-click, structured briefing - revenue
pipeline health, sector breakdown, operational/delivery status, and a
flagged data-quality/risk section - written in plain prose a founder could
paste into a board update or Slack digest, backed entirely by the same
deterministic analytics.py functions used elsewhere (no separate, drifting
source of numbers).
"""
from __future__ import annotations

from datetime import datetime

from openai import OpenAI

from . import analytics, config


def _build_raw_snapshot(deals_df, wo_df) -> dict:
    sectors = analytics.list_sectors(deals_df, wo_df)
    overall_pipeline = analytics.pipeline_summary(deals_df)
    overall_wo = analytics.work_order_summary(wo_df)
    per_sector = {s: analytics.combined_sector_view(deals_df, wo_df, sector=s) for s in sectors}
    return {
        "generated_at": datetime.now().isoformat(),
        "overall_pipeline": overall_pipeline,
        "overall_work_orders": overall_wo,
        "per_sector": per_sector,
    }


def generate_leadership_update(deals_df, wo_df, deals_quality, wo_quality) -> str:
    """Returns a markdown-formatted leadership update string."""
    snapshot = _build_raw_snapshot(deals_df, wo_df)

    # Configure client for xAI / Grok endpoint
    client = OpenAI(
        api_key=getattr(config, "XAI_API_KEY", getattr(config, "OPENAI_API_KEY", None)),
        base_url="https://api.xai.com/v1",
    )

    # Use Grok model from config with fallback
    model_name = getattr(config, "GROK_MODEL", getattr(config, "OPENAI_MODEL", "grok-2-latest"))

    prompt = f"""You are drafting a leadership/board update for a founder based on the JSON \
data below (sales pipeline + project delivery, already aggregated - do not invent numbers \
beyond what's here). 

Structure it in markdown with these sections:
1. **Headline** - one or two sentence top-line summary
2. **Pipeline Health** - open/weighted pipeline value, win/loss, notable sector concentration
3. **Delivery Status** - work order status mix, value, any overdue/at-risk items
4. **Sector Breakdown** - short bullets per sector combining pipeline + delivery
5. **Data Quality & Risks** - be direct about any gaps (missing values, missing dates, \
overdue work) a founder should know before trusting these numbers for a real decision

Keep it tight and skimmable - this goes in front of a founder who has 90 seconds, not a \
detailed report. Use real numbers from the data, formatted with $ and commas.

DATA:
{snapshot}
"""
    resp = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content