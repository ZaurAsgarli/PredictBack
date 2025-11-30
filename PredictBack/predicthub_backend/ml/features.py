"""
Feature engineering module for trade anomaly detection.
"""

from typing import List

import pandas as pd


REQUIRED_COLUMNS: List[str] = ["user_id", "created_at", "amount_staked"]

FEATURE_COLUMNS: List[str] = [
    "amount_staked",
    "time_since_last_trade",
    "hour_of_day",
    "user_total_trades",
    "user_avg_stake",
]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build feature matrix from raw trade data.

    Args:
        df: DataFrame with columns: user_id, created_at, amount_staked

    Returns:
        DataFrame with feature columns in order:
            amount_staked, time_since_last_trade, hour_of_day,
            user_total_trades, user_avg_stake

    Raises:
        ValueError: If required columns are missing.
    """
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(
            f"Missing required columns: {missing_cols}. "
            f"Required columns are: {REQUIRED_COLUMNS}"
        )

    df_feat = df.copy()

    df_feat["created_at"] = pd.to_datetime(df_feat["created_at"])

    df_feat = df_feat.sort_values(["user_id", "created_at"]).reset_index(drop=True)

    df_feat["time_since_last_trade"] = (
        df_feat.groupby("user_id")["created_at"]
        .diff()
        .dt.total_seconds()
        .fillna(0.0)
    )

    df_feat["hour_of_day"] = df_feat["created_at"].dt.hour

    user_total_trades = (
        df_feat.groupby("user_id")["amount_staked"]
        .count()
        .rename("user_total_trades")
    )
    user_avg_stake = (
        df_feat.groupby("user_id")["amount_staked"]
        .mean()
        .rename("user_avg_stake")
    )

    df_feat = df_feat.merge(user_total_trades, on="user_id", how="left")
    df_feat = df_feat.merge(user_avg_stake, on="user_id", how="left")

    return df_feat[FEATURE_COLUMNS].copy()

