"""
Model loader module for trade anomaly detection.
"""

from pathlib import Path
from typing import Any, Dict

import joblib
import pandas as pd


MODEL_DIR: Path = Path(__file__).resolve().parent / "models"

ISOLATION_FOREST_PATH: Path = MODEL_DIR / "isolation_forest.pkl"
SCALER_PATH: Path = MODEL_DIR / "feature_scaler.pkl"

_isolation_forest: Any = None
_scaler: Any = None


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
    Predict risk level for a trade.

    Args:
        features: DataFrame with 5 feature columns from build_features()

    Returns:
        Dict with score, label, risk_level
    """
    model, scaler = get_models()

    X_scaled = scaler.transform(features.values)

    score = float(model.decision_function(X_scaled)[0])
    label = int(model.predict(X_scaled)[0])

    if score < -0.2:
        risk_level = "HIGH"
    elif score < 0.0:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "score": score,
        "label": label,
        "risk_level": risk_level,
    }

