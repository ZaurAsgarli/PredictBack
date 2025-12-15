"""
Manipulation Service Layer.

Provides Django ORM integration for Model 4 (Market Manipulation Detection).
Fetches data from database, converts to DataFrames, and calls ml.model_4_manipulation functions.
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from backend_api.api.trades.models import Trade
from ml_service.training.notebooks.model_4_manipulation import detect_market_manipulation
from ml_service.training.services.db_storage_service import save_manipulation_score


def _trades_queryset_to_df(qs) -> pd.DataFrame:
    """
    Convert Trade queryset into a DataFrame suitable for Model 4.

    Args:
        qs: Django QuerySet of Trade objects

    Returns:
        DataFrame with columns: user_id, market_id, created_at, amount_staked,
        trade_type, outcome_type
    """
    return pd.DataFrame.from_records(
        qs.values(
            "user_id",
            "market_id",
            "created_at",
            "amount_staked",
            "trade_type",
            "outcome_type",
        )
    )


def get_market_manipulation_analysis(
    market_id: int,
    time_window_minutes: int = 60,
) -> Optional[Dict[str, Any]]:
    """
    Get manipulation analysis for a specific market.

    Args:
        market_id: Market ID to analyze
        time_window_minutes: Time window for coordination detection

    Returns:
        Dict with manipulation analysis results, or None if no trades found
    """
    qs = Trade.objects.filter(market_id=market_id)

    if not qs.exists():
        return None

    df_trades = _trades_queryset_to_df(qs)
    results = detect_market_manipulation(
        df_trades,
        market_id=market_id,
        time_window_minutes=time_window_minutes,
    )

    if results.empty:
        return None

    # Aggregate results for the market
    market_result = {
        'market_id': market_id,
        'manipulation_score': float(results['manipulation_score'].mean()),
        'is_manipulation_suspected': bool(results['is_manipulation_suspected'].any()),
        'suspected_users_count': int(results['is_manipulation_suspected'].sum()),
        'total_users_analyzed': len(results),
        'pump_dump_score': float(results['pump_dump_score'].iloc[0]) if len(results) > 0 else 0.0,
        'wash_trading_score': float(results['wash_trading_score'].iloc[0]) if len(results) > 0 else 0.0,
        'risk_level': results['risk_level'].iloc[0] if len(results) > 0 else 'LOW',
        'suspected_users': results[results['is_manipulation_suspected']]['user_id'].tolist(),
    }
    
    # Save to database for each user in the market
    try:
        for _, row in results.iterrows():
            save_manipulation_score(
                market_id=market_id,
                user_id=int(row['user_id']) if pd.notna(row['user_id']) else None,
                manipulation_score=float(row['manipulation_score']),
                is_manipulation_suspected=bool(row['is_manipulation_suspected']),
                risk_level=str(row['risk_level']),
                pump_dump_score=float(row['pump_dump_score']),
                wash_trading_score=float(row['wash_trading_score']),
                clique_id=int(row['clique_id']) if pd.notna(row['clique_id']) else None,
                time_window_minutes=time_window_minutes,
            )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to save manipulation scores to DB: {e}")

    return market_result


def get_all_markets_manipulation_analysis(
    time_window_minutes: int = 60,
) -> List[Dict[str, Any]]:
    """
    Get manipulation analysis for all markets with trades.

    Args:
        time_window_minutes: Time window for coordination detection

    Returns:
        List of dicts with manipulation analysis per market
    """
    qs = Trade.objects.all()

    if not qs.exists():
        return []

    df_trades = _trades_queryset_to_df(qs)
    results = detect_market_manipulation(
        df_trades,
        market_id=None,  # Analyze all markets
        time_window_minutes=time_window_minutes,
    )

    if results.empty:
        return []

    # Aggregate by market
    market_analysis = []
    for market_id in results['market_id'].unique():
        market_results = results[results['market_id'] == market_id]
        
        market_analysis.append({
            'market_id': int(market_id),
            'manipulation_score': float(market_results['manipulation_score'].mean()),
            'is_manipulation_suspected': bool(market_results['is_manipulation_suspected'].any()),
            'suspected_users_count': int(market_results['is_manipulation_suspected'].sum()),
            'total_users_analyzed': len(market_results),
            'pump_dump_score': float(market_results['pump_dump_score'].iloc[0]) if len(market_results) > 0 else 0.0,
            'wash_trading_score': float(market_results['wash_trading_score'].iloc[0]) if len(market_results) > 0 else 0.0,
            'risk_level': market_results['risk_level'].iloc[0] if len(market_results) > 0 else 'LOW',
        })

    return market_analysis


def get_user_manipulation_risk(
    user_id: int,
    time_window_minutes: int = 60,
) -> Optional[Dict[str, Any]]:
    """
    Get manipulation risk profile for a specific user.

    Args:
        user_id: User ID to analyze
        time_window_minutes: Time window for coordination detection

    Returns:
        Dict with user manipulation risk profile, or None if no trades found
    """
    qs = Trade.objects.filter(user_id=user_id)

    if not qs.exists():
        return None

    df_trades = _trades_queryset_to_df(qs)
    results = detect_market_manipulation(
        df_trades,
        market_id=None,
        time_window_minutes=time_window_minutes,
    )

    if results.empty:
        return None

    # Filter for this user
    user_results = results[results['user_id'] == user_id]

    if user_results.empty:
        return None

    # Aggregate across all markets for this user
    user_result = {
        'user_id': user_id,
        'manipulation_score': float(user_results['manipulation_score'].mean()),
        'is_manipulation_suspected': bool(user_results['is_manipulation_suspected'].any()),
        'markets_involved': int(user_results['market_id'].nunique()),
        'clique_id': int(user_results['clique_id'].iloc[0]) if user_results['clique_id'].notna().any() else None,
        'max_risk_level': user_results['risk_level'].max() if len(user_results) > 0 else 'LOW',
        'suspected_markets': user_results[user_results['is_manipulation_suspected']]['market_id'].tolist(),
    }

    return user_result

