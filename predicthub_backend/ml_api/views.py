"""API views for ML model predictions."""

from typing import Any, Dict, List

import pandas as pd
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ml.features import build_features
from ml.logs import log_model_output
from ml.model_loader import predict_trade_risk
from ml.services.db_storage_service import save_trade_risk_prediction
from ml.services.exposure_service import (
    get_user_exposure,
    get_market_risk,
    get_user_risk_profile,
    get_all_market_risks,
    get_user_risk_profile_all,
)
from ml.services.manipulation_service import (
    get_market_manipulation_analysis,
    get_all_markets_manipulation_analysis,
    get_user_manipulation_risk,
)
from ml.services.mhews_service import (
    get_platform_health_status,
    get_health_dashboard_data,
)


REQUIRED_FIELDS: List[str] = ["user_id", "amount_staked", "created_at"]


def validate_request_data(data: Dict[str, Any]) -> List[str]:
    """Return list of missing required fields."""
    return [field for field in REQUIRED_FIELDS if field not in data]


@api_view(["POST"])
@permission_classes([AllowAny])
def predict_trade_risk_view(request: Request) -> Response:
    """
    Predict risk level for a single trade.

    POST /api/ml/risk/predict/
    {
        "user_id": 123,
        "amount_staked": 150.0,
        "created_at": "2025-01-01T12:34:56Z"
    }
    """
    missing_fields = validate_request_data(request.data)
    if missing_fields:
        return Response(
            {
                "error": "Missing required fields",
                "missing_fields": missing_fields,
                "required_fields": REQUIRED_FIELDS,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        df_raw = pd.DataFrame([request.data])

        features = build_features(df_raw)

        result = predict_trade_risk(features)

        user_id = request.data.get("user_id")
        trade_id = request.data.get("trade_id")
        market_id = request.data.get("market_id")
        
        # Log to file (existing)
        log_model_output(
            user_id=int(user_id) if user_id is not None else None,
            score=result["score"],
            label=result["label"],
            risk_level=result["risk_level"],
        )
        
        # Save to database (NEW)
        try:
            save_trade_risk_prediction(
                user_id=int(user_id) if user_id else None,
                trade_id=int(trade_id) if trade_id else None,
                market_id=int(market_id) if market_id else None,
                score=result["score"],
                label=result["label"],
                risk_level=result["risk_level"],
                features=request.data,  # Save input features for audit
            )
        except Exception as e:
            # Don't fail the request if DB save fails, but log it
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to save prediction to DB: {e}")

        return Response(
            {
                "input": request.data,
                "score": result["score"],
                "label": result["label"],
                "risk_level": result["risk_level"],
            },
            status=status.HTTP_200_OK,
        )

    except FileNotFoundError as e:
        return Response(
            {"error": "Model not found", "detail": str(e)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except ValueError as e:
        return Response(
            {"error": "Invalid input data", "detail": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        return Response(
            {"error": "Prediction failed", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class UserExposureView(APIView):
    """
    GET /api/ml/exposure/user/<user_id>/
    Returns exposure info for one user across all markets.
    """
    permission_classes = [AllowAny]

    def get(self, request: Request, user_id: int) -> Response:
        data = get_user_exposure(user_id)
        if data is None:
            return Response(
                {"detail": "No exposure found for this user."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"user_id": user_id, "exposures": data})


class MarketRiskView(APIView):
    """
    GET /api/ml/exposure/market/<market_id>/
    Returns market-level risk KPIs.
    """
    permission_classes = [AllowAny]

    def get(self, request: Request, market_id: int) -> Response:
        data = get_market_risk(market_id)
        if data is None:
            return Response(
                {"detail": "No positions found for this market."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(data)


class UserRiskProfileView(APIView):
    """
    GET /api/ml/exposure/user/<user_id>/profile/
    Returns risk profile for one user.
    """
    permission_classes = [AllowAny]

    def get(self, request: Request, user_id: int) -> Response:
        data = get_user_risk_profile(user_id)
        if data is None:
            return Response(
                {"detail": "No risk profile found for this user."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(data)


class AllMarketRisksView(APIView):
    """
    GET /api/ml/exposure/markets/
    Returns risk KPIs for all markets with positions.
    """
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        data = get_all_market_risks()
        return Response({"markets": data, "count": len(data)})


class AllUserRiskProfilesView(APIView):
    """
    GET /api/ml/exposure/users/
    Returns risk profiles for all users with positions.
    """
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        data = get_user_risk_profile_all()
        return Response({"users": data, "count": len(data)})


# ============================================================================
# Model 4: Market Manipulation Detection
# ============================================================================

class MarketManipulationView(APIView):
    """
    GET /api/ml/manipulation/market/<market_id>/
    Returns manipulation analysis for a specific market.
    """
    permission_classes = [AllowAny]

    def get(self, request: Request, market_id: int) -> Response:
        time_window = request.query_params.get('time_window_minutes', 60)
        try:
            time_window = int(time_window)
        except (ValueError, TypeError):
            time_window = 60

        data = get_market_manipulation_analysis(market_id, time_window_minutes=time_window)
        if data is None:
            return Response(
                {"detail": "No trades found for this market."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(data)


class AllMarketsManipulationView(APIView):
    """
    GET /api/ml/manipulation/markets/
    Returns manipulation analysis for all markets.
    """
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        time_window = request.query_params.get('time_window_minutes', 60)
        try:
            time_window = int(time_window)
        except (ValueError, TypeError):
            time_window = 60

        data = get_all_markets_manipulation_analysis(time_window_minutes=time_window)
        return Response({"markets": data, "count": len(data)})


class UserManipulationRiskView(APIView):
    """
    GET /api/ml/manipulation/user/<user_id>/
    Returns manipulation risk profile for a specific user.
    """
    permission_classes = [AllowAny]

    def get(self, request: Request, user_id: int) -> Response:
        time_window = request.query_params.get('time_window_minutes', 60)
        try:
            time_window = int(time_window)
        except (ValueError, TypeError):
            time_window = 60

        data = get_user_manipulation_risk(user_id, time_window_minutes=time_window)
        if data is None:
            return Response(
                {"detail": "No trades found for this user."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(data)


# ============================================================================
# Model 5: Market Health Early Warning System (MHEWS)
# ============================================================================

class PlatformHealthView(APIView):
    """
    GET /api/ml/health/
    Returns current platform health status and metrics.
    """
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        aggregation_window = request.query_params.get('aggregation_window_hours', 24)
        try:
            aggregation_window = int(aggregation_window)
        except (ValueError, TypeError):
            aggregation_window = 24

        data = get_platform_health_status(aggregation_window_hours=aggregation_window)
        if 'error' in data:
            return Response(
                data,
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(data)


class HealthDashboardView(APIView):
    """
    GET /api/ml/health/dashboard/
    Returns comprehensive dashboard data for health monitoring.
    """
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        data = get_health_dashboard_data()
        return Response(data)

