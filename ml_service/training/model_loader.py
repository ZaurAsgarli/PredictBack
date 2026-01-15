"""
Model loader module for trade anomaly detection and token behavior forecasting.
"""

from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import pandas as pd
import pickle


MODEL_DIR: Path = Path(__file__).resolve().parent / "models"

ISOLATION_FOREST_PATH: Path = MODEL_DIR / "isolation_forest.pkl"
SCALER_PATH: Path = MODEL_DIR / "feature_scaler.pkl"

# Model 3 paths
TOKEN_BEHAVIOR_MODEL_PATH: Path = MODEL_DIR / "model3_token_xgb.pkl"
TOKEN_BEHAVIOR_FEATURES_PATH: Path = MODEL_DIR / "model3_token_xgb_features.pkl"

_isolation_forest: Any = None
_scaler: Any = None

# Model 3 cache
_token_behavior_model: Any = None
_token_behavior_features: List[str] = None


def _load_models() -> None:
    """Load models from disk."""
    global _isolation_forest, _scaler

    if not ISOLATION_FOREST_PATH.exists():
        raise FileNotFoundError(
            f"Isolation Forest model not found at: {ISOLATION_FOREST_PATH}"
        )

    if not SCALER_PATH.exists():
        raise FileNotFoundError(
            f"Feature scaler not found at: {SCALER_PATH}"
        )

    _isolation_forest = joblib.load(ISOLATION_FOREST_PATH)
    _scaler = joblib.load(SCALER_PATH)


def get_models() -> tuple:
    """Get loaded model and scaler instances."""
    global _isolation_forest, _scaler

    if _isolation_forest is None or _scaler is None:
        _load_models()

    return _isolation_forest, _scaler


def predict_trade_risk(features: pd.DataFrame) -> Dict[str, Any]:
    """
    Predict risk level using HEURISTIC LOGIC (Audit Requirement).
    
    Formula:
    Risk Score = (failed_logins * 0.2) + (trade_velocity_factor * 0.5) + (stake_factor * 0.3)
    
    Args:
        features: DataFrame with columns from build_features()
                  + optional 'failed_logins', 'wallet_age_days'
    
    Returns:
        Dict with score, label, risk_level
    """
    # 1. Extract Features (Handling defaults if missing)
    row = features.iloc[0]
    
    failed_logins = row.get('failed_logins', 0)
    
    # Velocity: Close to 0 seconds since last trade = High Velocity
    time_diff = row.get('time_since_last_trade', 3600)
    velocity_factor = 1.0 if time_diff < 10 else (100 / (time_diff + 1))
    velocity_factor = min(velocity_factor, 1.0) # Cap at 1.0
    
    # Stake: High stake relative to avg = High Risk
    amount = row.get('amount_staked', 0)
    avg_stake = row.get('user_avg_stake', amount)
    stake_ratio = amount / (avg_stake + 1.0)
    stake_factor = 1.0 if stake_ratio > 3.0 else (stake_ratio / 3.0)
    
    # Wallet Age (Mock/Default if missing)
    wallet_age_days = row.get('wallet_age_days', 30) 
    age_penalty = 0.5 if wallet_age_days < 1 else 0.0

    # 2. Calculate Heuristic Score
    score = (failed_logins * 0.2) + (velocity_factor * 0.3) + (stake_factor * 0.5) + age_penalty
    
    # Cap score
    score = min(score, 1.0)

    # 3. Determine Label
    # Threshold > 0.85 = High Risk
    if score > 0.85:
        risk_level = "HIGH"
        label = -1
    elif score > 0.5:
        risk_level = "MEDIUM"
        label = 0 # Suspicious
    else:
        risk_level = "LOW"
        label = 1 # Normal

    # Mock return for consistency
    return {
        "score": float(score),
        "label": label,
        "risk_level": risk_level,
    }


# ============================================================================
# Model 3: Token Behavior Forecasting
# ============================================================================


class TokenBehaviorModelError(Exception):
    """Custom exception for Model 3 errors."""
    pass


def load_token_behavior_model() -> Tuple[Any, List[str]]:
    """
    Lazily load and cache the XGBoost token behavior model and feature list.
    
    Returns:
        Tuple of (model, feature_names)
        
    Raises:
        TokenBehaviorModelError: If model or feature files are missing.
    """
    global _token_behavior_model, _token_behavior_features
    
    # Return cached if already loaded
    if _token_behavior_model is not None and _token_behavior_features is not None:
        return _token_behavior_model, _token_behavior_features
    
    # Check if files exist
    if not TOKEN_BEHAVIOR_MODEL_PATH.exists():
        raise TokenBehaviorModelError(
            f"Token behavior model not found at: {TOKEN_BEHAVIOR_MODEL_PATH}"
        )
    
    if not TOKEN_BEHAVIOR_FEATURES_PATH.exists():
        raise TokenBehaviorModelError(
            f"Token behavior features file not found at: {TOKEN_BEHAVIOR_FEATURES_PATH}"
        )
    
    # Load model
    try:
        _token_behavior_model = joblib.load(TOKEN_BEHAVIOR_MODEL_PATH)
    except Exception as e:
        raise TokenBehaviorModelError(
            f"Failed to load token behavior model: {str(e)}"
        )
    
    # Load feature names
    try:
        with open(TOKEN_BEHAVIOR_FEATURES_PATH, 'rb') as f:
            _token_behavior_features = pickle.load(f)
    except Exception as e:
        raise TokenBehaviorModelError(
            f"Failed to load token behavior features: {str(e)}"
        )
    
    # Validate feature names is a list
    if not isinstance(_token_behavior_features, list):
        raise TokenBehaviorModelError(
            f"Features file must contain a list, got {type(_token_behavior_features)}"
        )
    
    return _token_behavior_model, _token_behavior_features


def predict_token_behavior(features_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Predict token behavior (price movement direction) using Model 3.
    
    Args:
        features_df: pandas DataFrame with exactly the same feature columns
                     as stored in model3_token_xgb_features.pkl.
                     Each row represents one time window for prediction.
    
    Returns:
        List of dicts, one per row in features_df, each containing:
        {
            "predicted_label": "UP" | "FLAT" | "DOWN",
            "proba": {
                "DOWN": float,
                "FLAT": float,
                "UP": float
            },
            "risk_score": float  # Range [0, 1], higher = more confident directional prediction
        }
    
    Risk Score Formula:
        The risk_score is computed as:
        - max_prob = max(probas.values())
        - If max_prob >= 0.5: risk_score = 2 * (max_prob - 0.5)  # Maps [0.5, 1.0] to [0.0, 1.0]
        - If max_prob < 0.5: risk_score = 0.0  # Low confidence = low risk
        
        This means:
        - High confidence in UP or DOWN → high risk_score (close to 1.0)
        - High confidence in FLAT → lower risk_score
        - Low confidence overall → low risk_score
    
    Raises:
        TokenBehaviorModelError: If model/features not loaded or features mismatch.
        ValueError: If features_df doesn't have required columns.
    """
    model, feature_names = load_token_behavior_model()
    
    # Validate input
    if features_df.empty:
        return []
    
    # Check feature columns match
    missing_features = set(feature_names) - set(features_df.columns)
    if missing_features:
        raise ValueError(
            f"Missing required features: {sorted(missing_features)}. "
            f"Required features: {sorted(feature_names)}"
        )
    
    # Select and order features exactly as model expects
    X = features_df[feature_names].copy()
    
    # Get predictions
    # XGBoost returns probabilities in order of classes (sorted alphabetically)
    # Classes are typically: ['DOWN', 'FLAT', 'UP'] (alphabetically sorted)
    proba_matrix = model.predict_proba(X)
    predictions = model.predict(X)
    
    # Get class names from model
    # XGBoost models trained with LabelEncoder will have numeric classes [0, 1, 2]
    # which correspond to ['DOWN', 'FLAT', 'UP'] in alphabetical order
    class_names = model.classes_
    
    # Map class indices to labels
    # Check if classes are numeric or string
    if len(class_names) == 3:
        # Standard 3-class case: assume ['DOWN', 'FLAT', 'UP'] order
        # LabelEncoder sorts alphabetically, so: ['DOWN', 'FLAT', 'UP'] -> [0, 1, 2]
        expected_labels = ['DOWN', 'FLAT', 'UP']
        
        if isinstance(class_names[0], (int, float)):
            # Numeric labels from LabelEncoder
            # Map indices to labels in alphabetical order
            label_map = {int(class_names[i]): expected_labels[i] for i in range(len(class_names))}
        else:
            # String labels - use directly but ensure order
            label_map = {i: str(class_names[i]) for i in range(len(class_names))}
    else:
        # Fallback: use class names as-is
        label_map = {i: str(class_names[i]) for i in range(len(class_names))}
    
    results = []
    for i in range(len(X)):
        # Get probabilities for this sample
        proba_dict = {
            label_map[j]: float(proba_matrix[i][j])
            for j in range(len(class_names))
        }
        
        # Get predicted label
        pred_idx = int(predictions[i])
        predicted_label = label_map[pred_idx]
        
        # Calculate risk score
        max_prob = max(proba_dict.values())
        if max_prob >= 0.5:
            risk_score = float(2 * (max_prob - 0.5))  # Maps [0.5, 1.0] to [0.0, 1.0]
        else:
            risk_score = 0.0
        
        results.append({
            "predicted_label": predicted_label,
            "proba": proba_dict,
            "risk_score": risk_score,
        })
    
    return results

