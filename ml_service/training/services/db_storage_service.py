"""
Database Storage Service for ML Model Predictions.

This service saves ML model outputs to the database for:
- Audit trails
- Historical analysis
- Dashboard queries
- Compliance
"""

from typing import Any, Dict, Optional
from decimal import Decimal
import time

from django.db import transaction
from django.utils import timezone

from ml_service.training.models import (
    TradeRiskPrediction,
    MarketManipulationScore,
    PlatformHealthMetric,
    ModelPredictionAudit,
)
from backend_api.api.trades.models import Trade
from backend_api.api.users.models import User
from backend_api.api.markets.models import Market


def save_trade_risk_prediction(
    user_id: Optional[int],
    trade_id: Optional[int],
    market_id: Optional[int],
    score: float,
    label: int,
    risk_level: str,
    features: Optional[Dict[str, Any]] = None,
    model_version: str = 'v1.0',
) -> TradeRiskPrediction:
    """
    Save Model 1 (Trade Risk) prediction to database.
    
    Args:
        user_id: User ID (optional)
        trade_id: Trade ID (optional)
        market_id: Market ID (optional)
        score: Anomaly score
        label: Prediction label (1 or -1)
        risk_level: Risk level string
        features: Optional feature values for audit
        model_version: Model version string
        
    Returns:
        TradeRiskPrediction instance
    """
    with transaction.atomic():
        prediction = TradeRiskPrediction.objects.create(
            user_id=user_id,
            trade_id=trade_id,
            market_id=market_id,
            score=score,
            label=label,
            risk_level=risk_level,
            amount_staked=Decimal(str(features.get('amount_staked'))) if features and 'amount_staked' in features else None,
            time_since_last_trade=features.get('time_since_last_trade') if features else None,
            hour_of_day=features.get('hour_of_day') if features else None,
            user_total_trades=features.get('user_total_trades') if features else None,
            user_avg_stake=Decimal(str(features.get('user_avg_stake'))) if features and 'user_avg_stake' in features else None,
            model_version=model_version,
        )
        
        # Also log to audit table
        ModelPredictionAudit.objects.create(
            model_name='model1',
            input_data=features or {},
            output_data={
                'score': score,
                'label': label,
                'risk_level': risk_level,
            },
            created_at=timezone.now(),
        )
        
        return prediction


def save_manipulation_score(
    market_id: int,
    user_id: Optional[int],
    manipulation_score: float,
    is_manipulation_suspected: bool,
    risk_level: str,
    pump_dump_score: float = 0.0,
    wash_trading_score: float = 0.0,
    clique_id: Optional[int] = None,
    time_window_minutes: int = 60,
    model_version: str = 'v1.0',
) -> MarketManipulationScore:
    """
    Save Model 4 (Market Manipulation) score to database.
    
    Args:
        market_id: Market ID
        user_id: User ID (optional)
        manipulation_score: Overall manipulation score (0-1)
        is_manipulation_suspected: Boolean flag
        risk_level: Risk level string
        pump_dump_score: Pump & dump score
        wash_trading_score: Wash trading score
        clique_id: Detected clique ID
        time_window_minutes: Time window used
        model_version: Model version string
        
    Returns:
        MarketManipulationScore instance
    """
    with transaction.atomic():
        score = MarketManipulationScore.objects.create(
            market_id=market_id,
            user_id=user_id,
            manipulation_score=manipulation_score,
            is_manipulation_suspected=is_manipulation_suspected,
            risk_level=risk_level,
            pump_dump_score=pump_dump_score,
            wash_trading_score=wash_trading_score,
            clique_id=clique_id,
            time_window_minutes=time_window_minutes,
            model_version=model_version,
        )
        
        # Log to audit table
        ModelPredictionAudit.objects.create(
            model_name='model4',
            input_data={
                'market_id': market_id,
                'user_id': user_id,
                'time_window_minutes': time_window_minutes,
            },
            output_data={
                'manipulation_score': manipulation_score,
                'is_manipulation_suspected': is_manipulation_suspected,
                'risk_level': risk_level,
                'pump_dump_score': pump_dump_score,
                'wash_trading_score': wash_trading_score,
            },
            created_at=timezone.now(),
        )
        
        return score


def save_platform_health_metric(
    platform_stress_level: float,
    systemic_risk_index: float,
    health_status: str,
    alert_level: str,
    model1_stress_score: float = 0.0,
    model2_stress_score: float = 0.0,
    model3_stress_score: float = 0.0,
    model4_stress_score: float = 0.0,
    model1_anomaly_rate: Optional[float] = None,
    model2_avg_hhi: Optional[float] = None,
    model3_avg_volatility: Optional[float] = None,
    model4_manipulation_rate: Optional[float] = None,
    alert_messages: str = '',
    aggregation_window_hours: int = 24,
    model_version: str = 'v1.0',
) -> PlatformHealthMetric:
    """
    Save Model 5 (Platform Health) metric to database.
    
    Args:
        platform_stress_level: Platform stress level (0-1)
        systemic_risk_index: Systemic risk index (0-1)
        health_status: Health status string
        alert_level: Alert level string
        model1_stress_score: Model 1 contribution
        model2_stress_score: Model 2 contribution
        model3_stress_score: Model 3 contribution
        model4_stress_score: Model 4 contribution
        model1_anomaly_rate: Model 1 anomaly rate
        model2_avg_hhi: Model 2 average HHI
        model3_avg_volatility: Model 3 average volatility
        model4_manipulation_rate: Model 4 manipulation rate
        alert_messages: Alert messages
        aggregation_window_hours: Aggregation window
        model_version: Model version string
        
    Returns:
        PlatformHealthMetric instance
    """
    with transaction.atomic():
        metric = PlatformHealthMetric.objects.create(
            platform_stress_level=platform_stress_level,
            systemic_risk_index=systemic_risk_index,
            health_status=health_status,
            alert_level=alert_level,
            model1_stress_score=model1_stress_score,
            model2_stress_score=model2_stress_score,
            model3_stress_score=model3_stress_score,
            model4_stress_score=model4_stress_score,
            model1_anomaly_rate=model1_anomaly_rate,
            model2_avg_hhi=model2_avg_hhi,
            model3_avg_volatility=model3_avg_volatility,
            model4_manipulation_rate=model4_manipulation_rate,
            alert_messages=alert_messages,
            aggregation_window_hours=aggregation_window_hours,
            model_version=model_version,
        )
        
        # Log to audit table
        ModelPredictionAudit.objects.create(
            model_name='model5',
            input_data={
                'aggregation_window_hours': aggregation_window_hours,
            },
            output_data={
                'platform_stress_level': platform_stress_level,
                'systemic_risk_index': systemic_risk_index,
                'health_status': health_status,
                'alert_level': alert_level,
            },
            created_at=timezone.now(),
        )
        
        return metric


def get_recent_predictions(
    model_name: Optional[str] = None,
    limit: int = 10,
) -> list:
    """
    Get recent model predictions from database.
    
    Args:
        model_name: Filter by model name (optional)
        limit: Number of records to return
        
    Returns:
        List of prediction records
    """
    queryset = ModelPredictionAudit.objects.all()
    
    if model_name:
        queryset = queryset.filter(model_name=model_name)
    
    return list(queryset.order_by('-created_at')[:limit].values())


def get_prediction_statistics(
    model_name: Optional[str] = None,
    days: int = 7,
) -> Dict[str, Any]:
    """
    Get prediction statistics for a model.
    
    Args:
        model_name: Filter by model name (optional)
        days: Number of days to look back
        
    Returns:
        Dictionary with statistics
    """
    from django.utils import timezone
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=days)
    
    queryset = ModelPredictionAudit.objects.filter(created_at__gte=cutoff_date)
    
    if model_name:
        queryset = queryset.filter(model_name=model_name)
    
    total = queryset.count()
    errors = queryset.exclude(error_message__isnull=True).exclude(error_message='').count()
    
    return {
        'total_predictions': total,
        'successful_predictions': total - errors,
        'failed_predictions': errors,
        'success_rate': (total - errors) / total if total > 0 else 0.0,
        'days': days,
    }

