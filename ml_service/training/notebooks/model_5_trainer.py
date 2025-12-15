"""
Model 5 Trainer: Train ML models for Market Health Early Warning System

This module provides training functionality for Model 5, converting
heuristic-based aggregation into trained ML regressors/classifiers.
"""

import pickle
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    mean_squared_error, mean_absolute_error, r2_score,
    classification_report, confusion_matrix, roc_auc_score
)

warnings.filterwarnings('ignore')


def extract_health_features(
    df_model1: Optional[pd.DataFrame] = None,
    df_model2: Optional[pd.DataFrame] = None,
    df_model3: Optional[pd.DataFrame] = None,
    df_model4: Optional[pd.DataFrame] = None,
    aggregation_window_hours: int = 24,
) -> Dict[str, float]:
    """
    Extract features for health prediction from model outputs.
    
    Args:
        df_model1: Model 1 output (Suspicious Trades)
        df_model2: Model 2 output (Position Exposure)
        df_model3: Model 3 output (Token Forecasting)
        df_model4: Model 4 output (Market Manipulation)
        aggregation_window_hours: Time window for aggregation
        
    Returns:
        Dictionary of feature values
    """
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


def prepare_health_training_data(
    historical_data: List[Dict],
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Prepare training data from historical health data.
    
    Args:
        historical_data: List of dictionaries with:
            - model1_df, model2_df, model3_df, model4_df (optional)
            - platform_stress_level (target)
            - systemic_risk_index (target)
            - health_status (target for classification)
            
    Returns:
        Tuple of (features_df, targets_df) where targets_df has columns:
            - platform_stress_level
            - systemic_risk_index
            - health_status
    """
    feature_list = []
    target_list = []
    
    for data_point in historical_data:
        features = extract_health_features(
            df_model1=data_point.get('model1_df'),
            df_model2=data_point.get('model2_df'),
            df_model3=data_point.get('model3_df'),
            df_model4=data_point.get('model4_df'),
        )
        
        feature_list.append(features)
        target_list.append({
            'platform_stress_level': data_point.get('platform_stress_level', 0.0),
            'systemic_risk_index': data_point.get('systemic_risk_index', 0.0),
            'health_status': data_point.get('health_status', 'STABLE'),
        })
    
    features_df = pd.DataFrame(feature_list)
    targets_df = pd.DataFrame(target_list)
    
    return features_df, targets_df


def train_health_predictor(
    historical_data: List[Dict],
    task_type: str = 'regression',
    target: str = 'platform_stress_level',
    model_type: str = 'random_forest',
    test_size: float = 0.2,
    random_state: int = 42,
    save_path: Optional[Path] = None,
) -> Dict:
    """
    Train a health prediction model.
    
    Args:
        historical_data: Historical data points
        task_type: 'regression' or 'classification'
        target: 'platform_stress_level', 'systemic_risk_index', or 'health_status'
        model_type: 'random_forest' or 'gradient_boosting'
        test_size: Test set size
        random_state: Random seed
        save_path: Path to save trained model
        
    Returns:
        Dictionary with model, scaler, metrics, and feature importance
    """
    print("Preparing training data...")
    X, y_df = prepare_health_training_data(historical_data)
    
    if len(X) == 0:
        raise ValueError("No features extracted. Check input data.")
    
    # Select target
    if target == 'health_status':
        y = y_df['health_status']
        task_type = 'classification'
    elif target == 'platform_stress_level':
        y = y_df['platform_stress_level']
        task_type = 'regression'
    elif target == 'systemic_risk_index':
        y = y_df['systemic_risk_index']
        task_type = 'regression'
    else:
        raise ValueError(f"Unknown target: {target}")
    
    print(f"✅ Extracted {len(X)} samples with {len(X.columns)} features")
    if task_type == 'classification':
        print(f"📊 Class distribution:\n{y.value_counts()}")
    else:
        print(f"📊 Target statistics: mean={y.mean():.4f}, std={y.std():.4f}, min={y.min():.4f}, max={y.max():.4f}")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state,
        stratify=y if task_type == 'classification' else None
    )
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train model
    print(f"\nTraining {model_type} {task_type} model...")
    if task_type == 'regression':
        if model_type == 'random_forest':
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=random_state,
                n_jobs=-1
            )
        elif model_type == 'gradient_boosting':
            model = GradientBoostingRegressor(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=random_state
            )
        else:
            raise ValueError(f"Unknown model_type: {model_type}")
    else:  # classification
        if model_type == 'random_forest':
            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=random_state,
                n_jobs=-1,
                class_weight='balanced'
            )
        elif model_type == 'gradient_boosting':
            model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=random_state
            )
        else:
            raise ValueError(f"Unknown model_type: {model_type}")
    
    model.fit(X_train_scaled, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test_scaled)
    
    print("\n📊 Model Performance:")
    if task_type == 'regression':
        mse = mean_squared_error(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        print(f"MSE: {mse:.4f}")
        print(f"MAE: {mae:.4f}")
        print(f"R² Score: {r2:.4f}")
        metrics = {'mse': mse, 'mae': mae, 'r2': r2}
    else:
        print(classification_report(y_test, y_pred))
        metrics = {
            'classification_report': classification_report(y_test, y_pred, output_dict=True),
            'confusion_matrix': confusion_matrix(y_test, y_pred).tolist(),
        }
        if hasattr(model, 'predict_proba'):
            y_pred_proba = model.predict_proba(X_test_scaled)
            # For multi-class, use macro average
            try:
                roc_auc = roc_auc_score(y_test, y_pred_proba, multi_class='ovr', average='macro')
                metrics['roc_auc'] = roc_auc
                print(f"ROC-AUC Score: {roc_auc:.4f}")
            except:
                pass
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': X.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("\n🔝 Top 10 Most Important Features:")
    print(feature_importance.head(10))
    
    # Cross-validation
    scoring = 'r2' if task_type == 'regression' else 'roc_auc_ovr'
    cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring=scoring)
    print(f"\n📊 Cross-Validation {scoring.upper()}: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")
    metrics['cv_score_mean'] = cv_scores.mean()
    metrics['cv_score_std'] = cv_scores.std()
    
    # Save model
    if save_path is None:
        save_path = Path(__file__).parent.parent / 'models' / f'model5_health_{target}.pkl'
    
    save_path.parent.mkdir(parents=True, exist_ok=True)
    
    model_data = {
        'model': model,
        'scaler': scaler,
        'feature_names': list(X.columns),
        'model_type': model_type,
        'task_type': task_type,
        'target': target,
        'trained_at': datetime.now().isoformat(),
    }
    
    with open(save_path, 'wb') as f:
        pickle.dump(model_data, f)
    
    print(f"\n✅ Model saved to: {save_path}")
    
    return {
        'model': model,
        'scaler': scaler,
        'feature_names': list(X.columns),
        'metrics': metrics,
        'feature_importance': feature_importance,
    }


def load_health_model(target: str = 'platform_stress_level', model_path: Optional[Path] = None) -> Dict:
    """
    Load trained health prediction model.
    
    Args:
        target: Target variable name
        model_path: Path to model file
        
    Returns:
        Dictionary with model, scaler, and metadata
    """
    if model_path is None:
        model_path = Path(__file__).parent.parent / 'models' / f'model5_health_{target}.pkl'
    
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found at: {model_path}")
    
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)
    
    return model_data


def predict_health_ml(
    df_model1: Optional[pd.DataFrame] = None,
    df_model2: Optional[pd.DataFrame] = None,
    df_model3: Optional[pd.DataFrame] = None,
    df_model4: Optional[pd.DataFrame] = None,
    target: str = 'platform_stress_level',
    model_path: Optional[Path] = None,
) -> Dict[str, float]:
    """
    Predict health metrics using trained ML model.
    
    Args:
        df_model1: Model 1 output
        df_model2: Model 2 output
        df_model3: Model 3 output
        df_model4: Model 4 output
        target: Target to predict
        model_path: Path to trained model
        
    Returns:
        Dictionary with prediction
    """
    model_data = load_health_model(target, model_path)
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
    
    # Reorder columns
    features_df = features_df[model_data['feature_names']]
    
    # Scale and predict
    X_scaled = scaler.transform(features_df.values)
    prediction = model.predict(X_scaled)[0]
    
    result = {target: float(prediction)}
    
    # If classification, also get probabilities
    if model_data['task_type'] == 'classification' and hasattr(model, 'predict_proba'):
        probabilities = model.predict_proba(X_scaled)[0]
        classes = model.classes_
        for cls, prob in zip(classes, probabilities):
            result[f'prob_{cls}'] = float(prob)
    
    return result

