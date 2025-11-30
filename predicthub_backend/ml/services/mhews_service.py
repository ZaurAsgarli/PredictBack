"""
MHEWS Service Layer.

Provides Django ORM integration for Model 5 (Market Health Early Warning System).
Aggregates signals from Models 1-4 and provides platform health metrics.
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from ml.notebooks.model_5_mhews import (
    calculate_market_health,
    aggregate_model1_signals,
    aggregate_model2_signals,
    aggregate_model3_signals,
    aggregate_model4_signals,
)
from ml.services.exposure_service import get_all_market_risks
from ml.services.manipulation_service import get_all_markets_manipulation_analysis
from ml.services.db_storage_service import save_platform_health_metric
from ml.model_loader import predict_trade_risk
from ml.features import build_features


def get_platform_health_status(
    aggregation_window_hours: int = 24,
) -> Dict[str, Any]:
    """
    Get current platform health status by aggregating all model signals.

    Args:
        aggregation_window_hours: Time window for aggregating signals

    Returns:
        Dict with platform health metrics and alerts
    """
    # Note: This is a simplified version. In production, you would:
    # 1. Fetch Model 1 outputs from database/cache
    # 2. Fetch Model 2 outputs (already available via exposure_service)
    # 3. Fetch Model 3 outputs from database/cache (if implemented)
    # 4. Fetch Model 4 outputs (already available via manipulation_service)

    # For now, we'll generate synthetic data or use available services
    # Model 2: Position Exposure (available)
    model2_data = get_all_market_risks()
    df_model2 = pd.DataFrame(model2_data) if model2_data else pd.DataFrame()

    # Model 4: Market Manipulation (available)
    model4_data = get_all_markets_manipulation_analysis()
    df_model4 = pd.DataFrame(model4_data) if model4_data else pd.DataFrame()

    # Model 1 & 3: Would need to be fetched from database/cache
    # For now, create empty DataFrames (will result in zero contribution)
    df_model1 = pd.DataFrame()  # Would fetch from Trade risk predictions
    df_model3 = pd.DataFrame()  # Would fetch from Token forecasting

    # Calculate health metrics
    health_df = calculate_market_health(
        df_model1=df_model1,
        df_model2=df_model2,
        df_model3=df_model3,
        df_model4=df_model4,
        aggregation_window_hours=aggregation_window_hours,
    )

    if health_df.empty:
        return {
            'error': 'Insufficient data for health calculation',
        }

    # Convert to dict
    result = health_df.iloc[0].to_dict()

    # Convert timestamp to string for JSON serialization
    if 'timestamp' in result:
        result['timestamp'] = result['timestamp'].isoformat()
    
    # Save to database
    try:
        save_platform_health_metric(
            platform_stress_level=result.get('platform_stress_level', 0.0),
            systemic_risk_index=result.get('systemic_risk_index', 0.0),
            health_status=result.get('health_status', 'HEALTHY'),
            alert_level=result.get('alert_level', 'LOW'),
            model1_stress_score=result.get('model1_stress_score', 0.0),
            model2_stress_score=result.get('model2_stress_score', 0.0),
            model3_stress_score=result.get('model3_stress_score', 0.0),
            model4_stress_score=result.get('model4_stress_score', 0.0),
            model1_anomaly_rate=result.get('model1_anomaly_rate'),
            model2_avg_hhi=result.get('model2_avg_hhi'),
            model3_avg_volatility=result.get('model3_avg_volatility'),
            model4_manipulation_rate=result.get('model4_manipulation_rate'),
            alert_messages=result.get('alert_messages', ''),
            aggregation_window_hours=aggregation_window_hours,
        )
    except Exception as e:
        # Don't fail the request if DB save fails
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to save health metric to DB: {e}")

    return result


def get_health_dashboard_data() -> Dict[str, Any]:
    """
    Get comprehensive dashboard data for health monitoring.

    Returns:
        Dict with dashboard-ready data including:
            - Current health status
            - Historical trends (if available)
            - Model contributions
            - Alert information
    """
    health_status = get_platform_health_status()

    # Get detailed breakdowns
    model2_data = get_all_market_risks()
    model4_data = get_all_markets_manipulation_analysis()

    dashboard_data = {
        'health_status': health_status,
        'model_breakdown': {
            'model2_markets_analyzed': len(model2_data),
            'model4_markets_analyzed': len(model4_data),
            'model2_high_risk_markets': len([m for m in model2_data if m.get('hhi', 0) > 0.5]),
            'model4_suspected_markets': len([m for m in model4_data if m.get('is_manipulation_suspected', False)]),
        },
        'recommendations': _generate_recommendations(health_status),
    }

    return dashboard_data


def _generate_recommendations(health_status: Dict[str, Any]) -> List[str]:
    """
    Generate recommendations based on health status.

    Args:
        health_status: Health status dictionary

    Returns:
        List of recommendation strings
    """
    recommendations = []

    platform_stress = health_status.get('platform_stress_level', 0.0)
    systemic_risk = health_status.get('systemic_risk_index', 0.0)
    alert_level = health_status.get('alert_level', 'LOW')

    if alert_level == 'CRITICAL':
        recommendations.append("IMMEDIATE ACTION REQUIRED: Platform health is critical")
        recommendations.append("Review all high-risk markets and consider temporary restrictions")
        recommendations.append("Investigate manipulation patterns and coordinate with security team")
    elif alert_level == 'HIGH':
        recommendations.append("Platform stress is elevated - monitor closely")
        recommendations.append("Review markets with high concentration or manipulation scores")
        recommendations.append("Consider increasing monitoring frequency")
    elif alert_level == 'MEDIUM':
        recommendations.append("Platform operating with elevated risk levels")
        recommendations.append("Continue monitoring and review risk metrics regularly")
    else:
        recommendations.append("Platform operating within normal parameters")
        recommendations.append("Continue standard monitoring procedures")

    # Model-specific recommendations
    if health_status.get('model4_stress_score', 0.0) > 0.6:
        recommendations.append("High manipulation risk detected - investigate coordinated trading patterns")

    if health_status.get('model2_stress_score', 0.0) > 0.6:
        recommendations.append("High concentration risk - consider diversification incentives")

    return recommendations

