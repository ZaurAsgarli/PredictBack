"""
Model 5: Market Health Early Warning System (MHEWS)

This is a meta-model that aggregates signals from Models 1-4 to assess overall platform health.

Key Features:
- Aggregates outputs from Models 1-4 (Suspicious Trades, Position Exposure, Token Forecasting, Manipulation)
- Calculates composite metrics: Platform_Stress_Level, Systemic_Risk_Index
- Provides alerting thresholds and dashboard-ready outputs
- Real-time health monitoring

Author: Prediction Hub ML Team
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import warnings

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

warnings.filterwarnings('ignore')


# ============================================================================
# MODEL OUTPUT INTERFACES (Expected formats from Models 1-4)
# ============================================================================

"""
Model 1 Output Format (Suspicious Trades):
    - user_id
    - score: Anomaly score
    - label: 1 (normal) or -1 (anomaly)
    - risk_level: 'LOW', 'MEDIUM', 'HIGH'

Model 2 Output Format (Position Exposure):
    - user_id (optional)
    - market_id
    - open_interest
    - num_traders
    - top1_share
    - top5_share
    - hhi: Herfindahl-Hirschman Index

Model 3 Output Format (Token Behavior Forecasting):
    - market_id
    - forecasted_price
    - forecasted_volatility
    - price_change_pct
    - volatility_risk_level: 'LOW', 'MEDIUM', 'HIGH'

Model 4 Output Format (Market Manipulation):
    - market_id
    - user_id (optional)
    - manipulation_score: 0-1
    - is_manipulation_suspected: Boolean
    - risk_level: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
"""


# ============================================================================
# RISK LEVEL MAPPING
# ============================================================================

RISK_LEVEL_MAP = {
    'LOW': 0.2,
    'MEDIUM': 0.5,
    'HIGH': 0.8,
    'CRITICAL': 1.0,
}


def risk_level_to_numeric(risk_level: str) -> float:
    """Convert risk level string to numeric value."""
    return RISK_LEVEL_MAP.get(risk_level.upper(), 0.0)


# ============================================================================
# MODEL 1 AGGREGATION (Suspicious Trades)
# ============================================================================

def aggregate_model1_signals(
    df_model1: pd.DataFrame,
    aggregation_window_hours: int = 24,
) -> Dict[str, float]:
    """
    Aggregate Model 1 (Suspicious Trades) signals.
    
    Args:
        df_model1: DataFrame with columns: user_id, score, label, risk_level, created_at
        aggregation_window_hours: Time window for aggregation
        
    Returns:
        Dictionary with aggregated metrics
    """
    if df_model1.empty:
        return {
            'model1_anomaly_rate': 0.0,
            'model1_avg_score': 0.0,
            'model1_high_risk_count': 0,
            'model1_stress_score': 0.0,
        }
    
    df = df_model1.copy()
    
    # Filter by time window if created_at exists
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'])
        cutoff_time = datetime.now() - timedelta(hours=aggregation_window_hours)
        df = df[df['created_at'] >= cutoff_time].copy()
    
    # Calculate metrics
    total_trades = len(df)
    anomaly_count = (df['label'] == -1).sum() if 'label' in df.columns else 0
    anomaly_rate = anomaly_count / total_trades if total_trades > 0 else 0.0
    
    avg_score = df['score'].mean() if 'score' in df.columns else 0.0
    
    # Count high risk cases
    if 'risk_level' in df.columns:
        high_risk_count = df['risk_level'].isin(['HIGH', 'CRITICAL']).sum()
    else:
        high_risk_count = 0
    
    # Stress score (0-1): Higher anomaly rate and scores = higher stress
    stress_score = min(anomaly_rate * 0.6 + abs(avg_score) * 0.4, 1.0)
    
    return {
        'model1_anomaly_rate': anomaly_rate,
        'model1_avg_score': avg_score,
        'model1_high_risk_count': high_risk_count,
        'model1_stress_score': stress_score,
    }


# ============================================================================
# MODEL 2 AGGREGATION (Position Exposure)
# ============================================================================

def aggregate_model2_signals(
    df_model2: pd.DataFrame,
) -> Dict[str, float]:
    """
    Aggregate Model 2 (Position Exposure) signals.
    
    Args:
        df_model2: DataFrame with market risk KPIs from Model 2
        
    Returns:
        Dictionary with aggregated metrics
    """
    if df_model2.empty:
        return {
            'model2_avg_hhi': 0.0,
            'model2_max_concentration': 0.0,
            'model2_stress_score': 0.0,
        }
    
    df = df_model2.copy()
    
    # Calculate metrics
    avg_hhi = df['hhi'].mean() if 'hhi' in df.columns else 0.0
    max_concentration = df['top1_share'].max() if 'top1_share' in df.columns else 0.0
    
    # Stress score: Higher HHI and concentration = higher stress
    # HHI ranges from 0 (perfect competition) to 1 (monopoly)
    hhi_stress = min(avg_hhi, 1.0)
    concentration_stress = min(max_concentration, 1.0)
    stress_score = (hhi_stress * 0.5 + concentration_stress * 0.5)
    
    return {
        'model2_avg_hhi': avg_hhi,
        'model2_max_concentration': max_concentration,
        'model2_stress_score': stress_score,
    }


# ============================================================================
# MODEL 3 AGGREGATION (Token Behavior Forecasting)
# ============================================================================

def aggregate_model3_signals(
    df_model3: pd.DataFrame,
) -> Dict[str, float]:
    """
    Aggregate Model 3 (Token Behavior Forecasting) signals.
    
    Args:
        df_model3: DataFrame with forecasting outputs from Model 3
        
    Returns:
        Dictionary with aggregated metrics
    """
    if df_model3.empty:
        return {
            'model3_avg_volatility': 0.0,
            'model3_high_volatility_count': 0,
            'model3_price_instability': 0.0,
            'model3_stress_score': 0.0,
        }
    
    df = df_model3.copy()
    
    # Calculate metrics
    avg_volatility = df['forecasted_volatility'].mean() if 'forecasted_volatility' in df.columns else 0.0
    
    # Count high volatility markets
    if 'volatility_risk_level' in df.columns:
        high_volatility_count = df['volatility_risk_level'].isin(['HIGH', 'CRITICAL']).sum()
    else:
        high_volatility_count = 0
    
    # Price instability (standard deviation of price changes)
    if 'price_change_pct' in df.columns:
        price_instability = df['price_change_pct'].std() if len(df) > 1 else 0.0
    else:
        price_instability = 0.0
    
    # Stress score: Higher volatility and instability = higher stress
    volatility_stress = min(avg_volatility, 1.0)
    instability_stress = min(abs(price_instability) / 0.5, 1.0)  # Normalize
    stress_score = (volatility_stress * 0.6 + instability_stress * 0.4)
    
    return {
        'model3_avg_volatility': avg_volatility,
        'model3_high_volatility_count': high_volatility_count,
        'model3_price_instability': price_instability,
        'model3_stress_score': stress_score,
    }


# ============================================================================
# MODEL 4 AGGREGATION (Market Manipulation)
# ============================================================================

def aggregate_model4_signals(
    df_model4: pd.DataFrame,
) -> Dict[str, float]:
    """
    Aggregate Model 4 (Market Manipulation) signals.
    
    Args:
        df_model4: DataFrame with manipulation detection outputs from Model 4
        
    Returns:
        Dictionary with aggregated metrics
    """
    if df_model4.empty:
        return {
            'model4_manipulation_rate': 0.0,
            'model4_avg_manipulation_score': 0.0,
            'model4_critical_markets': 0,
            'model4_stress_score': 0.0,
        }
    
    df = df_model4.copy()
    
    # Calculate metrics
    total_cases = len(df)
    manipulation_count = df['is_manipulation_suspected'].sum() if 'is_manipulation_suspected' in df.columns else 0
    manipulation_rate = manipulation_count / total_cases if total_cases > 0 else 0.0
    
    avg_manipulation_score = df['manipulation_score'].mean() if 'manipulation_score' in df.columns else 0.0
    
    # Count critical markets
    if 'risk_level' in df.columns:
        critical_markets = df[df['risk_level'] == 'CRITICAL']['market_id'].nunique()
    else:
        critical_markets = 0
    
    # Stress score: Higher manipulation rate and scores = higher stress
    stress_score = min(manipulation_rate * 0.5 + avg_manipulation_score * 0.5, 1.0)
    
    return {
        'model4_manipulation_rate': manipulation_rate,
        'model4_avg_manipulation_score': avg_manipulation_score,
        'model4_critical_markets': critical_markets,
        'model4_stress_score': stress_score,
    }


# ============================================================================
# COMPOSITE METRICS CALCULATION
# ============================================================================

def calculate_platform_stress_level(
    model1_signals: Dict[str, float],
    model2_signals: Dict[str, float],
    model3_signals: Dict[str, float],
    model4_signals: Dict[str, float],
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """
    Calculate Platform Stress Level (0-1).
    
    Higher values indicate higher platform stress.
    
    Args:
        model1_signals: Aggregated Model 1 signals
        model2_signals: Aggregated Model 2 signals
        model3_signals: Aggregated Model 3 signals
        model4_signals: Aggregated Model 4 signals
        weights: Optional weights for each model (default: equal weights)
        
    Returns:
        Platform Stress Level (0-1)
    """
    if weights is None:
        weights = {
            'model1': 0.25,
            'model2': 0.25,
            'model3': 0.25,
            'model4': 0.25,
        }
    
    stress_scores = [
        model1_signals.get('model1_stress_score', 0.0) * weights['model1'],
        model2_signals.get('model2_stress_score', 0.0) * weights['model2'],
        model3_signals.get('model3_stress_score', 0.0) * weights['model3'],
        model4_signals.get('model4_stress_score', 0.0) * weights['model4'],
    ]
    
    platform_stress_level = sum(stress_scores)
    return min(platform_stress_level, 1.0)


def calculate_systemic_risk_index(
    model1_signals: Dict[str, float],
    model2_signals: Dict[str, float],
    model3_signals: Dict[str, float],
    model4_signals: Dict[str, float],
) -> float:
    """
    Calculate Systemic Risk Index (0-1).
    
    Measures the risk of cascading failures across the platform.
    Higher values indicate higher systemic risk.
    
    Args:
        model1_signals: Aggregated Model 1 signals
        model2_signals: Aggregated Model 2 signals
        model3_signals: Aggregated Model 3 signals
        model4_signals: Aggregated Model 4 signals
        
    Returns:
        Systemic Risk Index (0-1)
    """
    # Factors that contribute to systemic risk:
    # 1. High concentration (Model 2)
    concentration_risk = model2_signals.get('model2_max_concentration', 0.0)
    
    # 2. Widespread manipulation (Model 4)
    manipulation_risk = model4_signals.get('model4_manipulation_rate', 0.0)
    
    # 3. High volatility across markets (Model 3)
    volatility_risk = min(model3_signals.get('model3_avg_volatility', 0.0), 1.0)
    
    # 4. High anomaly rate (Model 1)
    anomaly_risk = model1_signals.get('model1_anomaly_rate', 0.0)
    
    # Weighted combination (manipulation and concentration are most critical)
    systemic_risk = (
        0.35 * manipulation_risk +
        0.30 * concentration_risk +
        0.20 * volatility_risk +
        0.15 * anomaly_risk
    )
    
    return min(systemic_risk, 1.0)


# ============================================================================
# ALERTING SYSTEM
# ============================================================================

ALERT_THRESHOLDS = {
    'LOW': 0.3,
    'MEDIUM': 0.5,
    'HIGH': 0.7,
    'CRITICAL': 0.85,
}


def determine_alert_level(
    platform_stress_level: float,
    systemic_risk_index: float,
) -> Tuple[str, List[str]]:
    """
    Determine alert level and generate alert messages.
    
    Args:
        platform_stress_level: Platform Stress Level (0-1)
        systemic_risk_index: Systemic Risk Index (0-1)
        
    Returns:
        Tuple of (alert_level, alert_messages)
    """
    alert_level = 'LOW'
    alert_messages = []
    
    # Determine alert level based on thresholds
    if platform_stress_level >= ALERT_THRESHOLDS['CRITICAL'] or systemic_risk_index >= ALERT_THRESHOLDS['CRITICAL']:
        alert_level = 'CRITICAL'
    elif platform_stress_level >= ALERT_THRESHOLDS['HIGH'] or systemic_risk_index >= ALERT_THRESHOLDS['HIGH']:
        alert_level = 'HIGH'
    elif platform_stress_level >= ALERT_THRESHOLDS['MEDIUM'] or systemic_risk_index >= ALERT_THRESHOLDS['MEDIUM']:
        alert_level = 'MEDIUM'
    
    # Generate specific alert messages
    if platform_stress_level >= ALERT_THRESHOLDS['HIGH']:
        alert_messages.append(f"Platform Stress Level is CRITICAL: {platform_stress_level:.2%}")
    
    if systemic_risk_index >= ALERT_THRESHOLDS['HIGH']:
        alert_messages.append(f"Systemic Risk Index is CRITICAL: {systemic_risk_index:.2%}")
    
    if platform_stress_level >= ALERT_THRESHOLDS['MEDIUM'] and platform_stress_level < ALERT_THRESHOLDS['HIGH']:
        alert_messages.append(f"Platform Stress Level is ELEVATED: {platform_stress_level:.2%}")
    
    if systemic_risk_index >= ALERT_THRESHOLDS['MEDIUM'] and systemic_risk_index < ALERT_THRESHOLDS['HIGH']:
        alert_messages.append(f"Systemic Risk Index is ELEVATED: {systemic_risk_index:.2%}")
    
    if not alert_messages:
        alert_messages.append("Platform operating within normal parameters")
    
    return alert_level, alert_messages


# ============================================================================
# MAIN MHEWS FUNCTION
# ============================================================================

def calculate_market_health(
    df_model1: Optional[pd.DataFrame] = None,
    df_model2: Optional[pd.DataFrame] = None,
    df_model3: Optional[pd.DataFrame] = None,
    df_model4: Optional[pd.DataFrame] = None,
    aggregation_window_hours: int = 24,
    model_weights: Optional[Dict[str, float]] = None,
) -> pd.DataFrame:
    """
    Main function to calculate Market Health Early Warning System metrics.
    
    Aggregates signals from Models 1-4 and produces dashboard-ready output.
    
    Args:
        df_model1: Model 1 output DataFrame (Suspicious Trades)
        df_model2: Model 2 output DataFrame (Position Exposure)
        df_model3: Model 3 output DataFrame (Token Forecasting)
        df_model4: Model 4 output DataFrame (Market Manipulation)
        aggregation_window_hours: Time window for aggregating signals
        model_weights: Optional weights for each model in stress calculation
        
    Returns:
        DataFrame with health metrics:
            - timestamp: Calculation timestamp
            - platform_stress_level: 0-1
            - systemic_risk_index: 0-1
            - alert_level: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
            - alert_messages: List of alert messages
            - model1_stress_score: Model 1 contribution
            - model2_stress_score: Model 2 contribution
            - model3_stress_score: Model 3 contribution
            - model4_stress_score: Model 4 contribution
            - health_status: Overall health status
    """
    timestamp = datetime.now()
    
    # Aggregate signals from each model
    model1_signals = aggregate_model1_signals(
        df_model1 if df_model1 is not None else pd.DataFrame(),
        aggregation_window_hours=aggregation_window_hours,
    )
    
    model2_signals = aggregate_model2_signals(
        df_model2 if df_model2 is not None else pd.DataFrame(),
    )
    
    model3_signals = aggregate_model3_signals(
        df_model3 if df_model3 is not None else pd.DataFrame(),
    )
    
    model4_signals = aggregate_model4_signals(
        df_model4 if df_model4 is not None else pd.DataFrame(),
    )
    
    # Calculate composite metrics
    platform_stress_level = calculate_platform_stress_level(
        model1_signals,
        model2_signals,
        model3_signals,
        model4_signals,
        weights=model_weights,
    )
    
    systemic_risk_index = calculate_systemic_risk_index(
        model1_signals,
        model2_signals,
        model3_signals,
        model4_signals,
    )
    
    # Determine alert level
    alert_level, alert_messages = determine_alert_level(
        platform_stress_level,
        systemic_risk_index,
    )
    
    # Determine overall health status
    if platform_stress_level < 0.3 and systemic_risk_index < 0.3:
        health_status = 'HEALTHY'
    elif platform_stress_level < 0.5 and systemic_risk_index < 0.5:
        health_status = 'STABLE'
    elif platform_stress_level < 0.7 and systemic_risk_index < 0.7:
        health_status = 'ELEVATED'
    elif platform_stress_level < 0.85 and systemic_risk_index < 0.85:
        health_status = 'WARNING'
    else:
        health_status = 'CRITICAL'
    
    # Compile results
    result = {
        'timestamp': timestamp,
        'platform_stress_level': platform_stress_level,
        'systemic_risk_index': systemic_risk_index,
        'alert_level': alert_level,
        'alert_messages': ' | '.join(alert_messages),
        'model1_stress_score': model1_signals.get('model1_stress_score', 0.0),
        'model2_stress_score': model2_signals.get('model2_stress_score', 0.0),
        'model3_stress_score': model3_signals.get('model3_stress_score', 0.0),
        'model4_stress_score': model4_signals.get('model4_stress_score', 0.0),
        'health_status': health_status,
        # Additional detailed metrics
        'model1_anomaly_rate': model1_signals.get('model1_anomaly_rate', 0.0),
        'model2_avg_hhi': model2_signals.get('model2_avg_hhi', 0.0),
        'model3_avg_volatility': model3_signals.get('model3_avg_volatility', 0.0),
        'model4_manipulation_rate': model4_signals.get('model4_manipulation_rate', 0.0),
    }
    
    return pd.DataFrame([result])


# ============================================================================
# SYNTHETIC DATA GENERATOR (for testing)
# ============================================================================

def generate_synthetic_model_outputs(
    n_users: int = 100,
    n_markets: int = 10,
    seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Generate synthetic outputs from Models 1-4 for testing.
    
    Args:
        n_users: Number of users
        n_markets: Number of markets
        seed: Random seed
        
    Returns:
        Tuple of (df_model1, df_model2, df_model3, df_model4)
    """
    np.random.seed(seed)
    base_time = datetime.now() - timedelta(hours=24)
    
    # Model 1: Suspicious Trades
    model1_data = []
    for i in range(50):
        model1_data.append({
            'user_id': np.random.randint(1, n_users + 1),
            'score': np.random.uniform(-0.5, 0.3),
            'label': np.random.choice([1, -1], p=[0.8, 0.2]),
            'risk_level': np.random.choice(['LOW', 'MEDIUM', 'HIGH'], p=[0.6, 0.3, 0.1]),
            'created_at': base_time + timedelta(hours=np.random.randint(0, 24)),
        })
    df_model1 = pd.DataFrame(model1_data)
    
    # Model 2: Position Exposure
    model2_data = []
    for market_id in range(1, n_markets + 1):
        model2_data.append({
            'market_id': market_id,
            'open_interest': np.random.uniform(1000, 10000),
            'num_traders': np.random.randint(10, 100),
            'top1_share': np.random.uniform(0.1, 0.8),
            'top5_share': np.random.uniform(0.3, 0.9),
            'hhi': np.random.uniform(0.1, 0.7),
        })
    df_model2 = pd.DataFrame(model2_data)
    
    # Model 3: Token Forecasting
    model3_data = []
    for market_id in range(1, n_markets + 1):
        model3_data.append({
            'market_id': market_id,
            'forecasted_price': np.random.uniform(0.3, 0.7),
            'forecasted_volatility': np.random.uniform(0.05, 0.3),
            'price_change_pct': np.random.uniform(-0.2, 0.2),
            'volatility_risk_level': np.random.choice(['LOW', 'MEDIUM', 'HIGH'], p=[0.5, 0.3, 0.2]),
        })
    df_model3 = pd.DataFrame(model3_data)
    
    # Model 4: Market Manipulation
    model4_data = []
    for market_id in range(1, n_markets + 1):
        for user_id in np.random.choice(range(1, n_users + 1), size=5, replace=False):
            model4_data.append({
                'market_id': market_id,
                'user_id': user_id,
                'manipulation_score': np.random.uniform(0.0, 0.6),
                'is_manipulation_suspected': np.random.choice([True, False], p=[0.2, 0.8]),
                'risk_level': np.random.choice(['LOW', 'MEDIUM', 'HIGH'], p=[0.7, 0.2, 0.1]),
            })
    df_model4 = pd.DataFrame(model4_data)
    
    return df_model1, df_model2, df_model3, df_model4


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("Generating synthetic model outputs...")
    df_m1, df_m2, df_m3, df_m4 = generate_synthetic_model_outputs()
    
    print("\nCalculating Market Health Early Warning System metrics...")
    health_df = calculate_market_health(
        df_model1=df_m1,
        df_model2=df_m2,
        df_model3=df_m3,
        df_model4=df_m4,
    )
    
    print("\n" + "="*60)
    print("MARKET HEALTH EARLY WARNING SYSTEM REPORT")
    print("="*60)
    print(f"\nTimestamp: {health_df['timestamp'].iloc[0]}")
    print(f"Platform Stress Level: {health_df['platform_stress_level'].iloc[0]:.2%}")
    print(f"Systemic Risk Index: {health_df['systemic_risk_index'].iloc[0]:.2%}")
    print(f"Alert Level: {health_df['alert_level'].iloc[0]}")
    print(f"Health Status: {health_df['health_status'].iloc[0]}")
    print(f"\nAlert Messages:\n{health_df['alert_messages'].iloc[0]}")
    print("\nModel Contributions:")
    print(f"  Model 1 (Suspicious Trades): {health_df['model1_stress_score'].iloc[0]:.2%}")
    print(f"  Model 2 (Position Exposure): {health_df['model2_stress_score'].iloc[0]:.2%}")
    print(f"  Model 3 (Token Forecasting): {health_df['model3_stress_score'].iloc[0]:.2%}")
    print(f"  Model 4 (Market Manipulation): {health_df['model4_stress_score'].iloc[0]:.2%}")
    print("\n" + "="*60)

