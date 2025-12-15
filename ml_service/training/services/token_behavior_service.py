"""
Token Behavior Service Layer.

Provides Django ORM integration for Model 3 (Token Behavior Forecasting).
Fetches market data, builds features, and calls the model to predict price movements.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd

from ml_service.training.model_loader import predict_token_behavior, TokenBehaviorModelError
from backend_api.api.markets.models import Market
from backend_api.api.trades.models import Trade


def _trades_queryset_to_df(qs) -> pd.DataFrame:
    """
    Convert Trade queryset into a DataFrame suitable for Model 3 feature engineering.
    
    Args:
        qs: Django QuerySet of Trade objects
        
    Returns:
        DataFrame with columns: market_id, created_at, user_id, outcome, amount, yes_price_at_trade
    """
    return pd.DataFrame.from_records(
        qs.values(
            "market_id",
            "created_at",
            "user_id",
            "outcome",
            "amount_staked",
        )
    )


def _build_model3_features(
    trades_df: pd.DataFrame,
    price_history_df: Optional[pd.DataFrame] = None,
    liquidity_events_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Build features for Model 3 from trades, price history, and liquidity events.
    
    This function should replicate the feature engineering from the training notebook.
    For now, this is a placeholder that needs to be implemented based on the actual
    feature engineering logic from model3_token_behaviour_forcasting.ipynb.
    
    Args:
        trades_df: DataFrame with trade data
        price_history_df: Optional DataFrame with price history
        liquidity_events_df: Optional DataFrame with liquidity events
        
    Returns:
        DataFrame with feature columns matching model3_token_xgb_features.pkl
    """
    # TODO: Implement actual feature engineering from the notebook
    # This should include:
    # - Price features (yes_price, ret_1h, ret_3h, ret_6h, vol_6h, vol_24h)
    # - Trade features (trade_count, volume_total, volume_yes, volume_no, trade_imbalance, etc.)
    # - Liquidity features (liq_add, liq_remove, liq_add_6h, liq_remove_6h, net_liq_6h)
    # - Rolling window aggregations
    
    # Placeholder: Return empty DataFrame with correct structure
    # In production, this should be fully implemented based on the notebook
    raise NotImplementedError(
        "Feature engineering for Model 3 needs to be implemented based on "
        "the training notebook (model3_token_behaviour_forcasting.ipynb)"
    )


def forecast_token_behavior_for_market(
    market_id: int,
    window_hours: int = 24,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Build features for Model 3, call the model, and return predictions and KPIs.
    
    Args:
        market_id: Market ID to analyze
        window_hours: Time window in hours for feature aggregation (default: 24)
        start_time: Optional start time for analysis window
        end_time: Optional end time for analysis window
        
    Returns:
        Dict containing:
        {
            "market_id": int,
            "window_hours": int,
            "predictions": [
                {
                    "timestamp": str (ISO format),
                    "predicted_label": "UP" | "FLAT" | "DOWN",
                    "proba": {"DOWN": float, "FLAT": float, "UP": float},
                    "risk_score": float
                },
                ...
            ],
            "kpis": {
                "total_predictions": int,
                "up_count": int,
                "flat_count": int,
                "down_count": int,
                "avg_risk_score": float,
                "max_risk_score": float,
                "up_probability_avg": float,
                "down_probability_avg": float,
            },
            "timestamp": str (ISO format of when analysis was run)
        }
        
    Raises:
        TokenBehaviorModelError: If model cannot be loaded or features mismatch
        ValueError: If market_id is invalid or no data available
    """
    # Validate market exists
    try:
        market = Market.objects.get(id=market_id)
    except Market.DoesNotExist:
        raise ValueError(f"Market with id={market_id} does not exist")
    
    # Set time window
    if end_time is None:
        end_time = datetime.now()
    if start_time is None:
        start_time = end_time - timedelta(hours=window_hours)
    
    # Fetch trades for this market in the time window
    trades_qs = Trade.objects.filter(
        market_id=market_id,
        created_at__gte=start_time,
        created_at__lte=end_time,
    ).order_by("created_at")
    
    if not trades_qs.exists():
        raise ValueError(
            f"No trades found for market_id={market_id} "
            f"in time window [{start_time}, {end_time}]"
        )
    
    trades_df = _trades_queryset_to_df(trades_qs)
    
    # TODO: Fetch price history and liquidity events if available
    # For now, we'll work with trades only
    price_history_df = None
    liquidity_events_df = None
    
    # Build features
    try:
        features_df = _build_model3_features(
            trades_df=trades_df,
            price_history_df=price_history_df,
            liquidity_events_df=liquidity_events_df,
        )
    except NotImplementedError:
        # If feature engineering is not implemented, return a helpful error
        return {
            "market_id": market_id,
            "window_hours": window_hours,
            "error": "Feature engineering not yet implemented. "
                     "Please implement _build_model3_features() based on the training notebook.",
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    if features_df.empty:
        raise ValueError(
            f"No features could be extracted for market_id={market_id} "
            f"in time window [{start_time}, {end_time}]"
        )
    
    # Get predictions from model
    try:
        predictions = predict_token_behavior(features_df)
    except TokenBehaviorModelError as e:
        raise TokenBehaviorModelError(f"Model prediction failed: {str(e)}")
    
    # Calculate KPIs
    if not predictions:
        kpis = {
            "total_predictions": 0,
            "up_count": 0,
            "flat_count": 0,
            "down_count": 0,
            "avg_risk_score": 0.0,
            "max_risk_score": 0.0,
            "up_probability_avg": 0.0,
            "down_probability_avg": 0.0,
        }
    else:
        up_count = sum(1 for p in predictions if p["predicted_label"] == "UP")
        flat_count = sum(1 for p in predictions if p["predicted_label"] == "FLAT")
        down_count = sum(1 for p in predictions if p["predicted_label"] == "DOWN")
        
        risk_scores = [p["risk_score"] for p in predictions]
        up_probs = [p["proba"]["UP"] for p in predictions]
        down_probs = [p["proba"]["DOWN"] for p in predictions]
        
        kpis = {
            "total_predictions": len(predictions),
            "up_count": up_count,
            "flat_count": flat_count,
            "down_count": down_count,
            "avg_risk_score": float(sum(risk_scores) / len(risk_scores)) if risk_scores else 0.0,
            "max_risk_score": float(max(risk_scores)) if risk_scores else 0.0,
            "up_probability_avg": float(sum(up_probs) / len(up_probs)) if up_probs else 0.0,
            "down_probability_avg": float(sum(down_probs) / len(down_probs)) if down_probs else 0.0,
        }
    
    # Format predictions with timestamps if available
    formatted_predictions = []
    for i, pred in enumerate(predictions):
        # Try to get timestamp from features_df if it has an index
        # In practice, you'd want to preserve timestamps from feature engineering
        formatted_pred = {
            "predicted_label": pred["predicted_label"],
            "proba": pred["proba"],
            "risk_score": pred["risk_score"],
        }
        
        # If features_df has a timestamp column, use it
        if "timestamp" in features_df.columns:
            formatted_pred["timestamp"] = features_df.iloc[i]["timestamp"].isoformat() if hasattr(features_df.iloc[i]["timestamp"], "isoformat") else str(features_df.iloc[i]["timestamp"])
        else:
            # Use window end time as fallback
            formatted_pred["timestamp"] = end_time.isoformat()
        
        formatted_predictions.append(formatted_pred)
    
    return {
        "market_id": market_id,
        "window_hours": window_hours,
        "predictions": formatted_predictions,
        "kpis": kpis,
        "timestamp": datetime.utcnow().isoformat(),
    }

