"""
Deterministic aggregation functions over cleaned Deals / Work Orders
DataFrames. All numeric results the agent reports to the founder come from
here (pandas), never from LLM free-generation, to avoid hallucinated
figures. The LLM's job is choosing which of these to call and narrating
the result.
"""
from __future__ import annotations

import pandas as pd

from . import config


def _quarter_bounds(year: int, quarter: int) -> tuple[pd.Timestamp, pd.Timestamp]:
    start_month = (quarter - 1) * 3 + 1
    start = pd.Timestamp(year=year, month=start_month, day=1)
    end = start + pd.DateOffset(months=3) - pd.DateOffset(days=1)
    return start, end


def _current_quarter(today: pd.Timestamp | None = None) -> tuple[int, int]:
    today = today or pd.Timestamp.today()
    return today.year, (today.month - 1) // 3 + 1


def filter_by_quarter(df: pd.DataFrame, date_col: str, year: int | None, quarter: int | None) -> pd.DataFrame:
    if year is None or quarter is None:
        return df
    start, end = _quarter_bounds(year, quarter)
    mask = df[date_col].between(start, end)
    return df[mask]


def pipeline_summary(
    deals_df: pd.DataFrame,
    sector: str | None = None,
    year: int | None = None,
    quarter: int | None = None,
    stage: str | None = None,
) -> dict:
    """
    Summarize sales pipeline: total open pipeline value, weighted value,
    won/lost, deal counts, by-stage and by-sector breakdowns.
    """
    df = deals_df.copy()
    filters_applied = {}

    if sector:
        df = df[df["sector"].str.lower() == sector.lower()]
        filters_applied["sector"] = sector
    if stage:
        df = df[df["stage"].str.lower() == stage.lower()]
        filters_applied["stage"] = stage
    if year and quarter:
        df = filter_by_quarter(df, "expected_close_date", year, quarter)
        filters_applied["period"] = f"Q{quarter} {year}"

    stage_lower = df["stage"].str.lower()
    open_df = df[stage_lower.isin(config.OPEN_STAGES)]
    won_df = df[stage_lower.isin(config.WON_STAGES)]
    lost_df = df[stage_lower.isin(config.LOST_STAGES)]

    open_value = open_df["value"].sum(skipna=True)
    weighted_value = (open_df["value"].fillna(0) * open_df["probability"].fillna(0) / 100).sum()
    won_value = won_df["value"].sum(skipna=True)
    lost_value = lost_df["value"].sum(skipna=True)

    by_stage = (
        df.groupby("stage", dropna=False)
        .agg(deal_count=("deal_id", "count"), total_value=("value", "sum"))
        .reset_index()
        .to_dict(orient="records")
    )
    by_sector = (
        df.groupby("sector", dropna=False)
        .agg(deal_count=("deal_id", "count"), total_value=("value", "sum"))
        .reset_index()
        .to_dict(orient="records")
    )

    missing_value_count = int(df["value"].isna().sum())
    missing_close_date_count = int(df["expected_close_date"].isna().sum())

    return {
        "filters_applied": filters_applied,
        "total_deals": int(len(df)),
        "open_deal_count": int(len(open_df)),
        "open_pipeline_value": None if pd.isna(open_value) else round(float(open_value), 2),
        "probability_weighted_pipeline_value": round(float(weighted_value), 2),
        "won_deal_count": int(len(won_df)),
        "won_value": None if pd.isna(won_value) else round(float(won_value), 2),
        "lost_deal_count": int(len(lost_df)),
        "lost_value": None if pd.isna(lost_value) else round(float(lost_value), 2),
        "by_stage": by_stage,
        "by_sector": by_sector,
        "data_quality_notes": {
            "deals_missing_value": missing_value_count,
            "deals_missing_expected_close_date": missing_close_date_count,
        },
    }


def work_order_summary(
    wo_df: pd.DataFrame,
    sector: str | None = None,
    status: str | None = None,
    year: int | None = None,
    quarter: int | None = None,
) -> dict:
    df = wo_df.copy()
    filters_applied = {}

    if sector:
        df = df[df["sector"].str.lower() == sector.lower()]
        filters_applied["sector"] = sector
    if status:
        df = df[df["status"].str.lower() == status.lower()]
        filters_applied["status"] = status
    if year and quarter:
        df = filter_by_quarter(df, "due_date", year, quarter)
        filters_applied["period"] = f"Q{quarter} {year}"

    by_status = (
        df.groupby("status", dropna=False)
        .agg(order_count=("wo_id", "count"), total_value=("value", "sum"), avg_pct_complete=("pct_complete", "mean"))
        .reset_index()
        .to_dict(orient="records")
    )
    by_sector = (
        df.groupby("sector", dropna=False)
        .agg(order_count=("wo_id", "count"), total_value=("value", "sum"))
        .reset_index()
        .to_dict(orient="records")
    )

    total_value = df["value"].sum(skipna=True)
    at_risk = df[
        (df["status"].str.lower() == "in progress")
        & (df["due_date"].notna())
        & (df["due_date"] < pd.Timestamp.today())
    ]

    return {
        "filters_applied": filters_applied,
        "total_work_orders": int(len(df)),
        "total_value": None if pd.isna(total_value) else round(float(total_value), 2),
        "by_status": by_status,
        "by_sector": by_sector,
        "overdue_in_progress_count": int(len(at_risk)),
        "overdue_in_progress_orders": at_risk[["wo_name", "client", "due_date"]].astype(str).to_dict(orient="records"),
        "data_quality_notes": {
            "orders_missing_value": int(df["value"].isna().sum()),
            "orders_missing_due_date": int(df["due_date"].isna().sum()),
        },
    }


def combined_sector_view(deals_df: pd.DataFrame, wo_df: pd.DataFrame, sector: str | None = None) -> dict:
    """
    Cross-board view: for a given sector (or all), show pipeline alongside
    active delivery work, so a founder can see sales + execution together.
    """
    pipeline = pipeline_summary(deals_df, sector=sector)
    delivery = work_order_summary(wo_df, sector=sector)

    return {
        "sector": sector or "All Sectors",
        "pipeline": {
            "open_pipeline_value": pipeline["open_pipeline_value"],
            "weighted_pipeline_value": pipeline["probability_weighted_pipeline_value"],
            "won_value": pipeline["won_value"],
            "open_deal_count": pipeline["open_deal_count"],
        },
        "delivery": {
            "total_work_order_value": delivery["total_value"],
            "total_work_orders": delivery["total_work_orders"],
            "overdue_in_progress_count": delivery["overdue_in_progress_count"],
        },
        "data_quality_notes": {
            **pipeline["data_quality_notes"],
            **delivery["data_quality_notes"],
        },
    }


def list_sectors(deals_df: pd.DataFrame, wo_df: pd.DataFrame) -> list[str]:
    sectors = set(deals_df["sector"].dropna().unique()) | set(wo_df["sector"].dropna().unique())
    return sorted(s for s in sectors if s != "Unspecified")
