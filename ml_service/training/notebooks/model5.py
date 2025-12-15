"""
Model 5: Market Health Early Warning System (MHEWS) - Analysis and Testing

This script provides analysis and testing functionality for Model 5.
For training, use model_5_trainer.py
For the main model functions, use model_5_mhews.py
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).absolute().parent.parent))

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import pickle
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.ensemble import RandomForestRegressor

# Import Model 5 functions
from ml_service.training.notebooks.model_5_mhews import (
    generate_synthetic_model_outputs,
    calculate_market_health,
    aggregate_model1_signals,
    aggregate_model2_signals,
    aggregate_model3_signals,
    aggregate_model4_signals,
    calculate_platform_stress_level,
    calculate_systemic_risk_index
)

# Set plotting style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)


def extract_health_features(df_model1=None, df_model2=None, df_model3=None, df_model4=None, aggregation_window_hours=24):
    """Extract features for health prediction from model outputs."""
    features = {}
    
    # Model 1 features
    if df_model1 is not None and not df_model1.empty:
        df1 = df_model1.copy()
        if 'created_at' in df1.columns:
            df1['created_at'] = pd.to_datetime(df1['created_at'])
            cutoff = datetime.now() - timedelta(hours=aggregation_window_hours)
            df1 = df1[df1['created_at'] >= cutoff]
        
        features['model1_anomaly_rate'] = (df1['label'] == -1).sum() / max(len(df1), 1) if 'label' in df1.columns else 0.0
        features['model1_avg_score'] = df1['score'].mean() if 'score' in df1.columns else 0.0
        features['model1_high_risk_count'] = df1['risk_level'].isin(['HIGH', 'CRITICAL']).sum() if 'risk_level' in df1.columns else 0
        features['model1_total_trades'] = len(df1)
    else:
        features['model1_anomaly_rate'] = 0.0
        features['model1_avg_score'] = 0.0
        features['model1_high_risk_count'] = 0
        features['model1_total_trades'] = 0
    
    # Model 2 features
    if df_model2 is not None and not df_model2.empty:
        df2 = df_model2.copy()
        features['model2_avg_hhi'] = df2['hhi'].mean() if 'hhi' in df2.columns else 0.0
        features['model2_max_concentration'] = df2['top1_share'].max() if 'top1_share' in df2.columns else 0.0
        features['model2_avg_top5_share'] = df2['top5_share'].mean() if 'top5_share' in df2.columns else 0.0
        features['model2_total_markets'] = df2['market_id'].nunique() if 'market_id' in df2.columns else 0
        features['model2_avg_open_interest'] = df2['open_interest'].mean() if 'open_interest' in df2.columns else 0.0
    else:
        features['model2_avg_hhi'] = 0.0
        features['model2_max_concentration'] = 0.0
        features['model2_avg_top5_share'] = 0.0
        features['model2_total_markets'] = 0
        features['model2_avg_open_interest'] = 0.0
    
    # Model 3 features
    if df_model3 is not None and not df_model3.empty:
        df3 = df_model3.copy()
        features['model3_avg_volatility'] = df3['forecasted_volatility'].mean() if 'forecasted_volatility' in df3.columns else 0.0
        features['model3_max_volatility'] = df3['forecasted_volatility'].max() if 'forecasted_volatility' in df3.columns else 0.0
        features['model3_high_volatility_count'] = df3['volatility_risk_level'].isin(['HIGH', 'CRITICAL']).sum() if 'volatility_risk_level' in df3.columns else 0
        features['model3_price_instability'] = df3['price_change_pct'].std() if 'price_change_pct' in df3.columns else 0.0
        features['model3_avg_price_change'] = df3['price_change_pct'].mean() if 'price_change_pct' in df3.columns else 0.0
    else:
        features['model3_avg_volatility'] = 0.0
        features['model3_max_volatility'] = 0.0
        features['model3_high_volatility_count'] = 0
        features['model3_price_instability'] = 0.0
        features['model3_avg_price_change'] = 0.0
    
    # Model 4 features
    if df_model4 is not None and not df_model4.empty:
        df4 = df_model4.copy()
        features['model4_manipulation_rate'] = df4['is_manipulation_suspected'].sum() / max(len(df4), 1) if 'is_manipulation_suspected' in df4.columns else 0.0
        features['model4_avg_manipulation_score'] = df4['manipulation_score'].mean() if 'manipulation_score' in df4.columns else 0.0
        features['model4_critical_markets'] = df4[df4['risk_level'] == 'CRITICAL']['market_id'].nunique() if 'risk_level' in df4.columns else 0
        features['model4_high_risk_count'] = df4['risk_level'].isin(['HIGH', 'CRITICAL']).sum() if 'risk_level' in df4.columns else 0
    else:
        features['model4_manipulation_rate'] = 0.0
        features['model4_avg_manipulation_score'] = 0.0
        features['model4_critical_markets'] = 0
        features['model4_high_risk_count'] = 0
    
    # Derived features
    features['total_risk_indicators'] = (
        features['model1_high_risk_count'] +
        features['model3_high_volatility_count'] +
        features['model4_high_risk_count']
    )
    
    features['combined_stress_score'] = (
        features['model1_anomaly_rate'] * 0.25 +
        features['model2_max_concentration'] * 0.25 +
        features['model3_avg_volatility'] * 0.25 +
        features['model4_manipulation_rate'] * 0.25
    )
    
    return features


def test_trained_models(df_model1=None, df_model2=None, df_model3=None, df_model4=None):
    """Test trained ML models on current data."""
    print("=" * 60)
    print("TESTING TRAINED MODELS")
    print("=" * 60)
    
    # Define model paths
    stress_model_path = Path(__file__).absolute().parent.parent / 'models' / 'model5_health_platform_stress_level.pkl'
    risk_model_path = Path(__file__).absolute().parent.parent / 'models' / 'model5_health_systemic_risk_index.pkl'
    
    # Load models
    if not stress_model_path.exists() or not risk_model_path.exists():
        print("⚠️  Model files not found. Please train models first using model_5_trainer.py")
        return None, None
    
    with open(stress_model_path, 'rb') as f:
        loaded_stress_model = pickle.load(f)
    
    with open(risk_model_path, 'rb') as f:
        loaded_risk_model = pickle.load(f)
    
    print(f"✅ Models loaded successfully!")
    print(f"📅 Stress model trained at: {loaded_stress_model.get('trained_at', 'Unknown')}")
    print(f"📅 Risk model trained at: {loaded_risk_model.get('trained_at', 'Unknown')}")
    
    # Prediction function
    def predict_health_ml(df_model1=None, df_model2=None, df_model3=None, df_model4=None, target='platform_stress_level', model_path=None):
        """Predict health metrics using trained ML model."""
        if target == 'platform_stress_level':
            model_path = stress_model_path if model_path is None else model_path
        else:
            model_path = risk_model_path if model_path is None else model_path
        
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        model = model_data['model']
        scaler = model_data['scaler']
        
        # Extract features
        features = extract_health_features(df_model1, df_model2, df_model3, df_model4)
        
        # Convert to DataFrame with correct feature order
        features_df = pd.DataFrame([features])
        # Ensure all features are present
        for feat_name in model_data['feature_names']:
            if feat_name not in features_df.columns:
                features_df[feat_name] = 0.0
        
        # Reorder columns to match training
        features_df = features_df[model_data['feature_names']]
        
        # Scale and predict
        X_scaled = scaler.transform(features_df.values)
        prediction = model.predict(X_scaled)[0]
        
        return {target: float(prediction)}
    
    # Test prediction on current data
    print(f"\n🧪 Testing predictions on current model outputs...")
    
    ml_stress_pred = predict_health_ml(df_model1, df_model2, df_model3, df_model4, 'platform_stress_level')
    ml_risk_pred = predict_health_ml(df_model1, df_model2, df_model3, df_model4, 'systemic_risk_index')
    
    return ml_stress_pred, ml_risk_pred


def analyze_model5_health(df_model1=None, df_model2=None, df_model3=None, df_model4=None):
    """Run complete Model 5 health analysis."""
    print("=" * 60)
    print("MODEL 5: MARKET HEALTH EARLY WARNING SYSTEM ANALYSIS")
    print("=" * 60)
    
    # Generate synthetic data if not provided
    if df_model1 is None or df_model2 is None or df_model3 is None or df_model4 is None:
        print("\nGenerating synthetic model outputs...")
        df_model1, df_model2, df_model3, df_model4 = generate_synthetic_model_outputs(
            n_users=100,
            n_markets=10,
            seed=42
        )
        print(f"✅ Generated synthetic model outputs")
    
    # Calculate health metrics
    print("\n📊 Calculating platform health metrics...")
    health_df = calculate_market_health(
        df_model1=df_model1,
        df_model2=df_model2,
        df_model3=df_model3,
        df_model4=df_model4,
        aggregation_window_hours=24
    )
    
    print(f"\n🎯 Platform Health Assessment:")
    print(f"  Health Status: {health_df['health_status'].iloc[0]}")
    print(f"  Alert Level: {health_df['alert_level'].iloc[0]}")
    print(f"  Platform Stress Level: {health_df['platform_stress_level'].iloc[0]:.2%}")
    print(f"  Systemic Risk Index: {health_df['systemic_risk_index'].iloc[0]:.2%}")
    
    # Test ML models if available
    ml_stress_pred, ml_risk_pred = test_trained_models(df_model1, df_model2, df_model3, df_model4)
    
    if ml_stress_pred and ml_risk_pred:
        print(f"\n📊 ML Model Predictions:")
        print(f"  - Platform Stress Level: {ml_stress_pred['platform_stress_level']:.4f}")
        print(f"  - Systemic Risk Index: {ml_risk_pred['systemic_risk_index']:.4f}")
        
        # Compare with heuristic
        print(f"\n📊 Heuristic Results (for comparison):")
        print(f"  - Platform Stress Level: {health_df['platform_stress_level'].iloc[0]:.4f}")
        print(f"  - Systemic Risk Index: {health_df['systemic_risk_index'].iloc[0]:.4f}")
        
        print(f"\n📈 Differences:")
        print(f"  - Stress Level: {abs(ml_stress_pred['platform_stress_level'] - health_df['platform_stress_level'].iloc[0]):.4f}")
        print(f"  - Risk Index: {abs(ml_risk_pred['systemic_risk_index'] - health_df['systemic_risk_index'].iloc[0]):.4f}")
    
    return health_df, ml_stress_pred, ml_risk_pred


if __name__ == '__main__':
    """Run Model 5 analysis when executed directly."""
    health_df, ml_stress_pred, ml_risk_pred = analyze_model5_health()
    print("\n✅ Analysis complete!")

