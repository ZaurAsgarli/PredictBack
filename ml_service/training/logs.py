"""
Logging module for ML model predictions.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


LOG_DIR: Path = Path("ml_logs")
LOG_FILE: Path = LOG_DIR / "isolation_forest_predictions.log"
TOKEN_BEHAVIOR_LOG_FILE: Path = LOG_DIR / "token_behavior_predictions.log"


def _ensure_log_dir() -> None:
    """Create log directory if missing."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def log_model_output(
    user_id: Optional[int],
    score: float,
    label: int,
    risk_level: str,
) -> None:
    """
    Log a model prediction to file.

    Args:
        user_id: User identifier (can be None)
        score: Model decision function score
        label: Model prediction label (1 = normal, -1 = anomaly)
        risk_level: Risk level string
    """
    _ensure_log_dir()

    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "score": score,
        "label": label,
        "risk_level": risk_level,
    }

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")


def log_token_behavior_prediction(
    market_id: Optional[int],
    predicted_label: str,
    proba: Dict[str, float],
    risk_score: float,
    timestamp: Optional[str] = None,
) -> None:
    """
    Log a Model 3 token behavior prediction to file.
    
    Args:
        market_id: Market identifier (can be None)
        predicted_label: Predicted label ("UP", "FLAT", or "DOWN")
        proba: Dictionary with probabilities for each class
        risk_score: Risk score (0.0 to 1.0)
        timestamp: Optional timestamp string (ISO format). If None, uses current time.
    """
    _ensure_log_dir()
    
    log_entry = {
        "timestamp": timestamp or datetime.utcnow().isoformat(),
        "market_id": market_id,
        "predicted_label": predicted_label,
        "proba": proba,
        "risk_score": risk_score,
    }
    
    with open(TOKEN_BEHAVIOR_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")

