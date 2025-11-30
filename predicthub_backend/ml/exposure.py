"""
Position / Exposure Risk Model.

This module provides heuristic, deterministic risk computations
for user-level and market-level KPIs from the Position table.

No machine learning is used - this is a rule-based risk engine.
"""

from typing import Optional

import numpy as np
import pandas as pd


def compute_user_market_exposure(df_pos: pd.DataFrame) -> pd.DataFrame:
    """
    Compute user-market exposure metrics from position data.

    Args:
        df_pos: DataFrame with columns:
            - user_id
            - market_id
            - yes_tokens
            - no_tokens
            - total_staked

    Returns:
        DataFrame with additional columns:
            - net_tokens: yes_tokens - no_tokens
            - direction: 1 (long YES), -1 (long NO), 0 (balanced)

    Raises:
        ValueError: If required columns are missing.
    """
    required_cols = ["user_id", "market_id", "yes_tokens", "no_tokens", "total_staked"]
    missing = [col for col in required_cols if col not in df_pos.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df_pos.copy()

    # Fill NaN values with 0
    for col in ["yes_tokens", "no_tokens", "total_staked"]:
        df[col] = df[col].fillna(0.0)

    # Net exposure: YES - NO
    df["net_tokens"] = df["yes_tokens"] - df["no_tokens"]

    # Direction flag
    df["direction"] = 0
    df.loc[df["net_tokens"] > 0, "direction"] = 1
    df.loc[df["net_tokens"] < 0, "direction"] = -1

    return df


def _compute_market_user_exposure(df_exposure: pd.DataFrame) -> pd.DataFrame:
    """
    Compute each user's share of total staked within each market.

    Args:
        df_exposure: DataFrame from compute_user_market_exposure with columns:
            - market_id
            - user_id
            - total_staked

    Returns:
        DataFrame with columns:
            - market_id
            - user_id
            - total_staked
            - market_total
            - share
    """
    market_user_exposure = df_exposure[["market_id", "user_id", "total_staked"]].copy()

    # Total staked per market
    total_by_market = (
        market_user_exposure
        .groupby("market_id", as_index=False)
        .agg(market_total=("total_staked", "sum"))
    )

    # Merge market totals
    market_user_exposure = market_user_exposure.merge(
        total_by_market,
        on="market_id",
        how="left",
    )

    # Compute share (handle division by zero)
    market_user_exposure["share"] = np.where(
        market_user_exposure["market_total"] > 0,
        market_user_exposure["total_staked"] / market_user_exposure["market_total"],
        0.0
    )

    return market_user_exposure


def _concentration_stats(group: pd.DataFrame, top_k: int = 5) -> pd.Series:
    """
    Compute concentration statistics for a single market.

    Args:
        group: DataFrame group for a single market with 'share' column
        top_k: Number of top users to include in topK_share calculation

    Returns:
        Series with:
            - top1_share: Largest single user share
            - top5_share: Sum of top K user shares
            - hhi: Herfindahl-Hirschman Index (sum of squared shares)
    """
    shares = group["share"].sort_values(ascending=False).values

    if len(shares) == 0:
        return pd.Series({
            "top1_share": 0.0,
            "top5_share": 0.0,
            "hhi": 0.0,
        })

    top1 = shares[0]
    topk = shares[:top_k].sum()
    hhi = np.sum(shares ** 2)

    return pd.Series({
        "top1_share": top1,
        "top5_share": topk,
        "hhi": hhi,
    })


def compute_market_risk_kpis(
    df_pos: pd.DataFrame,
    df_markets: Optional[pd.DataFrame] = None,
    top_k: int = 5,
) -> pd.DataFrame:
    """
    Compute market-level risk KPIs.

    Args:
        df_pos: Position DataFrame with user_id, market_id, yes_tokens,
            no_tokens, total_staked
        df_markets: Optional market metadata DataFrame with id, title, status
        top_k: Number of top users for concentration calculation

    Returns:
        DataFrame with columns:
            - market_id
            - open_interest: Total staked in market
            - num_traders: Unique user count
            - top1_share: Largest user share
            - top5_share: Sum of top K user shares
            - hhi: Herfindahl-Hirschman Index
            - title, status (if df_markets provided)
    """
    # Step 1: Compute user-market exposure
    df_exposure = compute_user_market_exposure(df_pos)

    # Step 2: Compute open interest and trader count per market
    market_base_kpis = (
        df_exposure
        .groupby("market_id", as_index=False)
        .agg(
            open_interest=("total_staked", "sum"),
            num_traders=("user_id", "nunique"),
        )
    )

    # Step 3: Compute market-user exposure (shares)
    market_user_exposure = _compute_market_user_exposure(df_exposure)

    # Step 4: Compute concentration stats per market
    market_concentration = (
        market_user_exposure
        .groupby("market_id")
        .apply(_concentration_stats, top_k=top_k, include_groups=False)
        .reset_index()
    )

    # Step 5: Merge base KPIs with concentration stats
    market_risk_kpis = market_base_kpis.merge(
        market_concentration,
        on="market_id",
        how="left",
    )

    # Step 6: Merge market metadata if provided
    if df_markets is not None:
        market_meta = df_markets.copy()
        if "id" in market_meta.columns and "market_id" not in market_meta.columns:
            market_meta = market_meta.rename(columns={"id": "market_id"})

        meta_cols = ["market_id"]
        for col in ["title", "status", "description"]:
            if col in market_meta.columns:
                meta_cols.append(col)

        market_risk_kpis = market_risk_kpis.merge(
            market_meta[meta_cols],
            on="market_id",
            how="left",
        )

    return market_risk_kpis


def compute_user_risk_profile(df_pos: pd.DataFrame) -> pd.DataFrame:
    """
    Compute user-level risk profile metrics.

    Args:
        df_pos: Position DataFrame with user_id, market_id, yes_tokens,
            no_tokens, total_staked

    Returns:
        DataFrame with columns:
            - user_id
            - total_stake_all_markets: Sum of total_staked across all markets
            - num_markets: Number of unique markets user participates in
            - max_market_share: User's maximum share in any single market
    """
    # Compute user-market exposure
    df_exposure = compute_user_market_exposure(df_pos)

    # Compute user totals
    user_total_stake = (
        df_exposure
        .groupby("user_id", as_index=False)
        .agg(
            total_stake_all_markets=("total_staked", "sum"),
            num_markets=("market_id", "nunique"),
        )
    )

    # Compute market-user exposure for share calculation
    market_user_exposure = _compute_market_user_exposure(df_exposure)

    # Compute max market share per user
    user_max_share = (
        market_user_exposure
        .groupby("user_id", as_index=False)
        .agg(max_market_share=("share", "max"))
    )

    # Merge user metrics
    user_risk_profile = user_total_stake.merge(
        user_max_share,
        on="user_id",
        how="left",
    )

    return user_risk_profile

