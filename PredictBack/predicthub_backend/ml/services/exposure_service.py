"""
Exposure Service Layer.

Provides Django ORM integration for the Position/Exposure Risk Model.
Fetches data from database, converts to DataFrames, and calls ml.exposure functions.
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from positions.models import Position
from markets.models import Market
from ml.exposure import (
    compute_user_market_exposure,
    compute_market_risk_kpis,
    compute_user_risk_profile,
)


def _positions_queryset_to_df(qs) -> pd.DataFrame:
    """
    Convert Position queryset into a DataFrame suitable for Model 2.

    Args:
        qs: Django QuerySet of Position objects

    Returns:
        DataFrame with columns: user_id, market_id, yes_tokens,
        no_tokens, total_staked, created_at, updated_at
    """
    return pd.DataFrame.from_records(
        qs.values(
            "user_id",
            "market_id",
            "yes_tokens",
            "no_tokens",
            "total_staked",
            "created_at",
            "updated_at",
        )
    )


def _markets_queryset_to_df(qs) -> pd.DataFrame:
    """
    Convert Market queryset into a DataFrame for metadata.

    Args:
        qs: Django QuerySet of Market objects

    Returns:
        DataFrame with columns: id, title, status, liquidity_pool, fee_percentage
    """
    return pd.DataFrame.from_records(
        qs.values(
            "id",
            "title",
            "status",
            "liquidity_pool",
            "fee_percentage",
        )
    )


def get_user_exposure(user_id: int) -> Optional[List[Dict[str, Any]]]:
    """
    Get exposure data for a specific user across all markets.

    Args:
        user_id: User ID to fetch exposure for

    Returns:
        List of dicts with exposure data per market, or None if no positions found
    """
    qs = Position.objects.filter(user_id=user_id, total_staked__gt=0)

    if not qs.exists():
        return None

    df = _positions_queryset_to_df(qs)
    df_exposure = compute_user_market_exposure(df)

    return df_exposure.to_dict(orient="records")


def get_market_risk(market_id: int) -> Optional[Dict[str, Any]]:
    """
    Get risk KPIs for a specific market.

    Args:
        market_id: Market ID to fetch risk data for

    Returns:
        Dict with market risk KPIs, or None if no positions found
    """
    qs = Position.objects.filter(market_id=market_id, total_staked__gt=0)

    if not qs.exists():
        return None

    df_pos = _positions_queryset_to_df(qs)

    # Fetch market metadata
    market_qs = Market.objects.filter(id=market_id)
    df_markets = _markets_queryset_to_df(market_qs)

    df_kpis = compute_market_risk_kpis(df_pos, df_markets)

    if df_kpis.empty:
        return None

    # Convert to dict and handle numpy/decimal types
    result = df_kpis.iloc[0].to_dict()
    for key, value in result.items():
        if hasattr(value, "item"):
            result[key] = value.item()
        elif pd.isna(value):
            result[key] = None

    return result


def get_all_market_risks() -> List[Dict[str, Any]]:
    """
    Get risk KPIs for all markets with active positions.

    Returns:
        List of dicts with market risk KPIs
    """
    qs = Position.objects.filter(total_staked__gt=0)

    if not qs.exists():
        return []

    df_pos = _positions_queryset_to_df(qs)

    # Fetch all relevant market metadata
    market_ids = df_pos["market_id"].unique().tolist()
    market_qs = Market.objects.filter(id__in=market_ids)
    df_markets = _markets_queryset_to_df(market_qs)

    df_kpis = compute_market_risk_kpis(df_pos, df_markets)

    return df_kpis.to_dict(orient="records")


def get_user_risk_profile(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Get risk profile for a specific user.

    Args:
        user_id: User ID to fetch profile for

    Returns:
        Dict with user risk profile, or None if no positions found
    """
    qs = Position.objects.filter(user_id=user_id, total_staked__gt=0)

    if not qs.exists():
        return None

    df = _positions_queryset_to_df(qs)
    df_profile = compute_user_risk_profile(df)

    if df_profile.empty:
        return None

    result = df_profile[df_profile["user_id"] == user_id].iloc[0].to_dict()
    for key, value in result.items():
        if hasattr(value, "item"):
            result[key] = value.item()
        elif pd.isna(value):
            result[key] = None

    return result


def get_user_risk_profile_all() -> List[Dict[str, Any]]:
    """
    Get risk profiles for all users with active positions.

    Returns:
        List of dicts with user risk profiles
    """
    qs = Position.objects.filter(total_staked__gt=0)

    if not qs.exists():
        return []

    df = _positions_queryset_to_df(qs)
    df_profile = compute_user_risk_profile(df)

    return df_profile.to_dict(orient="records")

