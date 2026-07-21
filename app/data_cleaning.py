"""
Normalizes messy monday.com board data into clean pandas DataFrames, and
tracks data-quality issues so the agent can surface caveats instead of
silently guessing.
"""
from __future__ import annotations

import re
from datetime import datetime

import pandas as pd
from dateutil import parser as dateparser

from . import config

NULL_TOKENS = {"", "-", "n/a", "na", "tbd", "none", "null", "unknown", "?"}


def _clean_text(val: str | None) -> str | None:
    if val is None:
        return None
    v = val.strip()
    if v.lower() in NULL_TOKENS:
        return None
    return v


def clean_currency(val: str | None) -> float | None:
    """Parse messy currency strings like '$450,000', '310000.00', '-', '' -> float."""
    v = _clean_text(val)
    if v is None:
        return None
    v = re.sub(r"[^\d.\-]", "", v)
    if v in ("", "-", "."):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def clean_percent(val: str | None) -> float | None:
    """Parse '70%', '70', '' -> float 0-100."""
    v = _clean_text(val)
    if v is None:
        return None
    v = v.replace("%", "").strip()
    try:
        return float(v)
    except ValueError:
        return None


def clean_date(val: str | None) -> pd.Timestamp | None:
    """
    Parse a wide variety of date formats (MM/DD/YYYY, YYYY-MM-DD,
    'March 5, 2024', '03/2026' month-only, etc). Returns pandas Timestamp
    or None if unparseable/missing.
    """
    v = _clean_text(val)
    if v is None:
        return None

    # Month/Year only, e.g. "03/2026" or "August 2026" -> assume 1st of month
    month_year_slash = re.fullmatch(r"(\d{1,2})/(\d{4})", v)
    if month_year_slash:
        month, year = month_year_slash.groups()
        try:
            return pd.Timestamp(year=int(year), month=int(month), day=1)
        except ValueError:
            return None

    try:
        dt = dateparser.parse(v, fuzzy=True, default=datetime(1900, 1, 1))
        # Guard against dateutil silently parsing garbage into 1900
        if dt.year == 1900:
            return None
        return pd.Timestamp(dt)
    except (ValueError, OverflowError, TypeError):
        return None


def normalize_sector(val: str | None) -> str:
    """Map messy sector/industry free text to a canonical bucket."""
    v = _clean_text(val)
    if v is None:
        return "Unspecified"
    v_lower = v.lower().strip()
    for canonical, variants in config.SECTOR_CANONICAL_MAP.items():
        if v_lower in variants or v_lower == canonical.lower():
            return canonical
    # Fallback: title-case whatever they entered so at least it's consistent
    return v.strip().title()


def normalize_stage(val: str | None) -> str:
    v = _clean_text(val)
    if v is None:
        return "Unspecified"
    return v.strip().title()


def _resolve_columns(raw_column_titles: set[str], column_map: dict) -> dict:
    """
    Match logical field names to actual column titles found on the board
    (case-insensitive, whitespace-trimmed).
    """
    lower_lookup = {t.strip().lower(): t for t in raw_column_titles}
    resolved = {}
    for field, candidates in column_map.items():
        for cand in candidates:
            if cand in lower_lookup:
                resolved[field] = lower_lookup[cand]
                break
    return resolved


def clean_deals(raw_items: list[dict]) -> tuple[pd.DataFrame, dict]:
    """
    Convert raw monday.com Deals items into a clean DataFrame plus a
    data-quality report.
    """
    if not raw_items:
        return pd.DataFrame(), {"total_rows": 0, "missing_fields": {}, "unmatched_columns": []}

    all_titles = set()
    for it in raw_items:
        all_titles.update(it["columns"].keys())
    resolved = _resolve_columns(all_titles, config.DEALS_COLUMN_MAP)

    rows = []
    for it in raw_items:
        cols = it["columns"]

        def g(field):
            title = resolved.get(field)
            return cols.get(title) if title else None

        rows.append({
            "deal_id": it["id"],
            "deal_name": it["name"],
            "client": _clean_text(g("client")),
            "sector": normalize_sector(g("sector")),
            "value": clean_currency(g("value")),
            "stage": normalize_stage(g("stage")),
            "probability": clean_percent(g("probability")),
            "expected_close_date": clean_date(g("expected_close_date")),
            "owner": _clean_text(g("owner")),
            "created_date": clean_date(g("created_date")),
        })

    df = pd.DataFrame(rows)

    quality = {
        "total_rows": len(df),
        "missing_fields": {
            "client": int(df["client"].isna().sum()),
            "value": int(df["value"].isna().sum()),
            "expected_close_date": int(df["expected_close_date"].isna().sum()),
            "probability": int(df["probability"].isna().sum()),
        },
        "unmatched_columns": [f for f in config.DEALS_COLUMN_MAP if f not in resolved],
    }
    return df, quality


def clean_work_orders(raw_items: list[dict]) -> tuple[pd.DataFrame, dict]:
    if not raw_items:
        return pd.DataFrame(), {"total_rows": 0, "missing_fields": {}, "unmatched_columns": []}

    all_titles = set()
    for it in raw_items:
        all_titles.update(it["columns"].keys())
    resolved = _resolve_columns(all_titles, config.WORK_ORDERS_COLUMN_MAP)

    rows = []
    for it in raw_items:
        cols = it["columns"]

        def g(field):
            title = resolved.get(field)
            return cols.get(title) if title else None

        rows.append({
            "wo_id": it["id"],
            "wo_name": it["name"],
            "client": _clean_text(g("client")),
            "sector": normalize_sector(g("sector")),
            "value": clean_currency(g("value")),
            "status": normalize_stage(g("status")),
            "pct_complete": clean_percent(g("pct_complete")),
            "start_date": clean_date(g("start_date")),
            "due_date": clean_date(g("due_date")),
            "assigned_to": _clean_text(g("assigned_to")),
        })

    df = pd.DataFrame(rows)

    quality = {
        "total_rows": len(df),
        "missing_fields": {
            "client": int(df["client"].isna().sum()),
            "value": int(df["value"].isna().sum()),
            "due_date": int(df["due_date"].isna().sum()),
            "pct_complete": int(df["pct_complete"].isna().sum()),
        },
        "unmatched_columns": [f for f in config.WORK_ORDERS_COLUMN_MAP if f not in resolved],
    }
    return df, quality
