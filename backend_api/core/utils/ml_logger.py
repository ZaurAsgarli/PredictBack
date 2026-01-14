import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional

# Import the specific services
from ml_service.training.logs import log_model_output as log_to_file
from ml_service.training.services.db_storage_service import save_trade_risk_prediction as save_to_db

logger = logging.getLogger(__name__)

class DualLogger:
    """
    Unified logging utility for ML events.
    Writes to BOTH File (for debugging) and Database (for Admin Dashboard).
    """

    @staticmethod
    def log_risk_event(
        user_id: int,
        trade_id: Optional[int],
        market_id: Optional[int],
        input_features: Dict[str, Any],
        model_result: Dict[str, Any]
    ) -> None:
        """
        Log a trade risk prediction event.
        """
        score = model_result.get('score', 0.0)
        label = model_result.get('label', 1)
        risk_level = model_result.get('risk_level', 'LOW')

        # 1. Log to File
        try:
            log_to_file(
                user_id=user_id,
                score=score,
                label=label,
                risk_level=risk_level
            )
            # logger.info(f"Logged to file: User {user_id} Score {score}")
        except Exception as e:
            logger.error(f"Failed to log to file: {e}")

        # 2. Log to Database
        try:
            save_to_db(
                user_id=user_id,
                trade_id=trade_id,
                market_id=market_id,
                score=score,
                label=label,
                risk_level=risk_level,
                features=input_features
            )
            # logger.info(f"Logged to DB: User {user_id} Score {score}")
        except Exception as e:
            logger.error(f"Failed to log to DB: {e}")
