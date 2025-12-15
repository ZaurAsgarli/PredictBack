from django.urls import path

from .views import (
    predict_trade_risk_view,
    UserExposureView,
    MarketRiskView,
    UserRiskProfileView,
    AllMarketRisksView,
    AllUserRiskProfilesView,
    MarketManipulationView,
    AllMarketsManipulationView,
    UserManipulationRiskView,
    PlatformHealthView,
    HealthDashboardView,
    TokenBehaviorForecastView,
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

    # Model 4: Market Manipulation Detection
    path("manipulation/market/<int:market_id>/", MarketManipulationView.as_view(), name="market-manipulation"),
    path("manipulation/markets/", AllMarketsManipulationView.as_view(), name="all-markets-manipulation"),
    path("manipulation/user/<int:user_id>/", UserManipulationRiskView.as_view(), name="user-manipulation-risk"),

    # Model 5: Market Health Early Warning System (MHEWS)
    path("health/", PlatformHealthView.as_view(), name="platform-health"),
    path("health/dashboard/", HealthDashboardView.as_view(), name="health-dashboard"),
    
    # Model 3: Token Behavior Forecasting
    path(
        "token-behavior/market/<int:market_id>/",
        TokenBehaviorForecastView.as_view(),
        name="token-behavior-forecast",
    ),
]

