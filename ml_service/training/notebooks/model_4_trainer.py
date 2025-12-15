"""
Model 4 Trainer: Train ML models for Market Manipulation Detection

This module provides training functionality for Model 4, converting
heuristic-based detection into trained ML classifiers.
"""

import pickle
import joblib
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import warnings

import numpy as np
import pandas as pd
import networkx as nx
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    classification_report, confusion_matrix, 
    roc_auc_score, precision_recall_curve
)

warnings.filterwarnings('ignore')


def extract_features_for_ml(
    df_trades: pd.DataFrame,
    market_id: int,
    user_id: Optional[int] = None,
    time_window_minutes: int = 60,
) -> Dict[str, float]:
    """
    Extract ML features for manipulation detection.
    
    Args:
        df_trades: Trade DataFrame
        market_id: Market to analyze
        user_id: User to analyze (None = market-level features)
        time_window_minutes: Time window for analysis
        
    Returns:
        Dictionary of feature values
    """
    market_trades = df_trades[df_trades['market_id'] == market_id].copy()
    market_trades['created_at'] = pd.to_datetime(market_trades['created_at'])
    
    if len(market_trades) == 0:
        return {}
    
    features = {}
    
    # Filter by user if specified
    if user_id is not None:
        user_trades = market_trades[market_trades['user_id'] == user_id].copy()
        if len(user_trades) == 0:
            return {}
        market_trades = user_trades
    
    # 1. Volume features
    features['total_volume'] = float(market_trades['amount_staked'].sum())
    features['avg_volume'] = float(market_trades['amount_staked'].mean())
    features['volume_std'] = float(market_trades['amount_staked'].std()) if len(market_trades) > 1 else 0.0
    features['max_volume'] = float(market_trades['amount_staked'].max())
    features['min_volume'] = float(market_trades['amount_staked'].min())
    
    # 2. Trade count features
    features['total_trades'] = len(market_trades)
    features['buy_count'] = len(market_trades[market_trades['trade_type'] == 'buy'])
    features['sell_count'] = len(market_trades[market_trades['trade_type'] == 'sell'])
    features['buy_sell_ratio'] = features['buy_count'] / max(features['sell_count'], 1)
    
    # 3. Timing features
    market_trades = market_trades.sort_values('created_at')
    time_diffs = market_trades['created_at'].diff().dt.total_seconds().dropna()
    if len(time_diffs) > 0:
        features['avg_time_between_trades'] = float(time_diffs.mean())
        features['min_time_between_trades'] = float(time_diffs.min())
        features['time_std'] = float(time_diffs.std())
    else:
        features['avg_time_between_trades'] = 0.0
        features['min_time_between_trades'] = 0.0
        features['time_std'] = 0.0
    
    # 4. Graph-based features
    G = nx.Graph()
    for _, trade in market_trades.iterrows():
        G.add_node(trade['user_id'])
    
    # Build edges based on timing
    for i, trade1 in market_trades.iterrows():
        for j, trade2 in market_trades.iterrows():
            if i >= j:
                continue
            time_diff = (trade2['created_at'] - trade1['created_at']).total_seconds() / 60.0
            if time_diff <= time_window_minutes and trade1['user_id'] != trade2['user_id']:
                if not G.has_edge(trade1['user_id'], trade2['user_id']):
                    G.add_edge(trade1['user_id'], trade2['user_id'])
    
    features['num_users'] = G.number_of_nodes()
    features['num_edges'] = G.number_of_edges()
    features['avg_degree'] = sum(dict(G.degree()).values()) / max(G.number_of_nodes(), 1)
    features['density'] = nx.density(G) if G.number_of_nodes() > 1 else 0.0
    
    # Clique features
    try:
        cliques = list(nx.find_cliques(G))
        features['num_cliques'] = len(cliques)
        features['max_clique_size'] = max([len(c) for c in cliques]) if cliques else 0
    except:
        features['num_cliques'] = 0
        features['max_clique_size'] = 0
    
    # 5. Pump & dump features
    buy_trades = market_trades[market_trades['trade_type'] == 'buy'].copy()
    sell_trades = market_trades[market_trades['trade_type'] == 'sell'].copy()
    
    if len(buy_trades) > 0 and len(sell_trades) > 0:
        buy_volume = buy_trades['amount_staked'].sum()
        sell_volume = sell_trades['amount_staked'].sum()
        features['pump_dump_ratio'] = sell_volume / max(buy_volume, 1)
        
        # Time between first buy and first sell
        first_buy = buy_trades['created_at'].min()
        first_sell = sell_trades['created_at'].min()
        if first_sell > first_buy:
            features['pump_to_dump_time'] = (first_sell - first_buy).total_seconds() / 3600.0
        else:
            features['pump_to_dump_time'] = 0.0
    else:
        features['pump_dump_ratio'] = 0.0
        features['pump_to_dump_time'] = 0.0
    
    # 6. Wash trading features (circular patterns)
    G_directed = nx.DiGraph()
    for _, trade in market_trades.iterrows():
        G_directed.add_node(trade['user_id'])
        if trade['trade_type'] == 'buy':
            # Look for sells from other users
            window_end = trade['created_at'] + timedelta(hours=1)
            opposite_trades = market_trades[
                (market_trades['trade_type'] == 'sell') &
                (market_trades['user_id'] != trade['user_id']) &
                (market_trades['created_at'] >= trade['created_at']) &
                (market_trades['created_at'] <= window_end)
            ]
            for _, opp_trade in opposite_trades.iterrows():
                G_directed.add_edge(trade['user_id'], opp_trade['user_id'])
    
    try:
        cycles = list(nx.simple_cycles(G_directed))
        features['num_cycles'] = len(cycles)
        features['max_cycle_length'] = max([len(c) for c in cycles]) if cycles else 0
    except:
        features['num_cycles'] = 0
        features['max_cycle_length'] = 0
    
    # 7. Concentration features
    if user_id is not None:
        # User-specific concentration
        user_volume = market_trades['amount_staked'].sum()
        total_market_volume = df_trades[df_trades['market_id'] == market_id]['amount_staked'].sum()
        features['user_market_share'] = user_volume / max(total_market_volume, 1)
    else:
        # Market-level concentration
        user_volumes = market_trades.groupby('user_id')['amount_staked'].sum().sort_values(ascending=False)
        if len(user_volumes) > 0:
            features['top1_share'] = user_volumes.iloc[0] / user_volumes.sum()
            features['top5_share'] = user_volumes.head(5).sum() / user_volumes.sum()
        else:
            features['top1_share'] = 0.0
            features['top5_share'] = 0.0
    
    return features


def prepare_training_data(
    df_trades: pd.DataFrame,
    labels: Optional[pd.DataFrame] = None,
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Prepare training data from trade data and labels.
    
    Args:
        df_trades: Trade DataFrame
        labels: DataFrame with columns: market_id, user_id (optional), is_manipulation
        
    Returns:
        Tuple of (features_df, labels_series)
    """
    feature_list = []
    label_list = []
    
    # If no labels provided, use heuristic detection as labels
    if labels is None:
        from ml_service.training.notebooks.model_4_manipulation import detect_market_manipulation
        heuristic_results = detect_market_manipulation(df_trades)
        labels = heuristic_results[['market_id', 'user_id', 'is_manipulation_suspected']].rename(
            columns={'is_manipulation_suspected': 'is_manipulation'}
        )
    
    # Extract features for each market/user combination
    for _, label_row in labels.iterrows():
        market_id = label_row['market_id']
        user_id = label_row.get('user_id', None)
        
        features = extract_features_for_ml(df_trades, market_id, user_id)
        if features:
            feature_list.append(features)
            label_list.append(int(label_row['is_manipulation']))
    
    features_df = pd.DataFrame(feature_list)
    labels_series = pd.Series(label_list)
    
    return features_df, labels_series


def train_manipulation_classifier(
    df_trades: pd.DataFrame,
    labels: Optional[pd.DataFrame] = None,
    model_type: str = 'random_forest',
    test_size: float = 0.2,
    random_state: int = 42,
    save_path: Optional[Path] = None,
) -> Dict:
    """
    Train a manipulation detection classifier.
    
    Args:
        df_trades: Trade DataFrame
        labels: Optional labels DataFrame (if None, uses heuristic detection)
        model_type: 'random_forest' or 'gradient_boosting'
        test_size: Test set size
        random_state: Random seed
        save_path: Path to save trained model
        
    Returns:
        Dictionary with model, scaler, metrics, and feature importance
    """
    print("Preparing training data...")
    X, y = prepare_training_data(df_trades, labels)
    
    if len(X) == 0:
        raise ValueError("No features extracted. Check input data.")
    
    print(f"✅ Extracted {len(X)} samples with {len(X.columns)} features")
    print(f"📊 Class distribution: {y.value_counts().to_dict()}")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train model
    print(f"\nTraining {model_type} classifier...")
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
    y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
    
    print("\n📊 Model Performance:")
    print(classification_report(y_test, y_pred))
    print(f"\n📈 ROC-AUC Score: {roc_auc_score(y_test, y_pred_proba):.4f}")
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': X.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("\n🔝 Top 10 Most Important Features:")
    print(feature_importance.head(10))
    
    # Cross-validation
    cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring='roc_auc')
    print(f"\n📊 Cross-Validation ROC-AUC: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")
    
    # Save model
    if save_path is None:
        save_path = Path(__file__).parent.parent / 'models' / 'model4_manipulation.pkl'
    
    save_path.parent.mkdir(parents=True, exist_ok=True)
    
    model_data = {
        'model': model,
        'scaler': scaler,
        'feature_names': list(X.columns),
        'model_type': model_type,
        'trained_at': datetime.now().isoformat(),
    }
    
    with open(save_path, 'wb') as f:
        pickle.dump(model_data, f)
    
    print(f"\n✅ Model saved to: {save_path}")
    
    return {
        'model': model,
        'scaler': scaler,
        'feature_names': list(X.columns),
        'metrics': {
            'roc_auc': roc_auc_score(y_test, y_pred_proba),
            'cv_roc_auc_mean': cv_scores.mean(),
            'cv_roc_auc_std': cv_scores.std(),
        },
        'feature_importance': feature_importance,
        'confusion_matrix': confusion_matrix(y_test, y_pred),
        'classification_report': classification_report(y_test, y_pred, output_dict=True),
    }


def load_manipulation_model(model_path: Optional[Path] = None) -> Dict:
    """
    Load trained manipulation detection model.
    
    Args:
        model_path: Path to model file (default: models/model4_manipulation.pkl)
        
    Returns:
        Dictionary with model, scaler, and metadata
    """
    if model_path is None:
        model_path = Path(__file__).parent.parent / 'models' / 'model4_manipulation.pkl'
    
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found at: {model_path}")
    
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)
    
    return model_data


def predict_manipulation_ml(
    df_trades: pd.DataFrame,
    market_id: int,
    user_id: Optional[int] = None,
    model_path: Optional[Path] = None,
) -> Dict[str, float]:
    """
    Predict manipulation using trained ML model.
    
    Args:
        df_trades: Trade DataFrame
        market_id: Market to analyze
        user_id: User to analyze (None = market-level)
        model_path: Path to trained model
        
    Returns:
        Dictionary with prediction and probability
    """
    model_data = load_manipulation_model(model_path)
    model = model_data['model']
    scaler = model_data['scaler']
    
    # Extract features
    features = extract_features_for_ml(df_trades, market_id, user_id)
    if not features:
        return {
            'is_manipulation': 0,
            'manipulation_probability': 0.0,
            'manipulation_score': 0.0,
        }
    
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
    probability = model.predict_proba(X_scaled)[0, 1]
    
    return {
        'is_manipulation': int(prediction),
        'manipulation_probability': float(probability),
        'manipulation_score': float(probability),
    }

