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
from ml.services.exposure_service import (
    get_user_exposure,
    get_market_risk,
    get_user_risk_profile,
    get_all_market_risks,
    get_user_risk_profile_all,
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
        log_model_output(
            user_id=int(user_id) if user_id is not None else None,
            score=result["score"],
            label=result["label"],
            risk_level=result["risk_level"],
        )

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

