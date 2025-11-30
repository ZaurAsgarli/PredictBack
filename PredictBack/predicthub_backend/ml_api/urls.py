from django.urls import path

from .views import (
    predict_trade_risk_view,
    UserExposureView,
    MarketRiskView,
    UserRiskProfileView,
    AllMarketRisksView,
    AllUserRiskProfilesView,
)


urlpatterns = [
    # Model 1: Trade Risk (Isolation Forest)
    path("risk/predict/", predict_trade_risk_view, name="predict_trade_risk"),

    # Model 2: Exposure Risk (Heuristic)
    path("exposure/user/<int:user_id>/", UserExposureView.as_view(), name="user-exposure"),
    path("exposure/user/<int:user_id>/profile/", UserRiskProfileView.as_view(), name="user-risk-profile"),
    path("exposure/market/<int:market_id>/", MarketRiskView.as_view(), name="market-risk"),
    path("exposure/markets/", AllMarketRisksView.as_view(), name="all-market-risks"),
    path("exposure/users/", AllUserRiskProfilesView.as_view(), name="all-user-profiles"),
]

