"""
GraphQL schema for PredictHub
"""
import strawberry
from typing import List, Optional
from datetime import datetime

# GraphQL types for main models
@strawberry.type
class UserType:
    id: int
    username: str
    email: str
    total_points: float
    win_rate: float
    streak: int
    created_at: datetime

@strawberry.type
class MarketType:
    id: int
    title: str
    description: str
    status: str
    resolution_outcome: Optional[str]
    liquidity_pool: float
    fee_percentage: float
    created_at: datetime
    ends_at: datetime

@strawberry.type
class TradeType:
    id: int
    outcome_type: str
    trade_type: str
    amount_staked: float
    tokens_amount: float
    price_at_execution: float
    created_at: datetime

@strawberry.type
class PositionType:
    id: int
    yes_tokens: float
    no_tokens: float
    total_staked: float
    created_at: datetime
    updated_at: datetime

@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "Hello from PredictHub GraphQL API"
    
    @strawberry.field
    def markets(self, status: Optional[str] = None) -> List[MarketType]:
        """Get all markets, optionally filtered by status"""
        from markets.models import Market
        queryset = Market.objects.all()
        if status:
            queryset = queryset.filter(status=status)
        markets = queryset[:100]  # Limit to 100
        return [
            MarketType(
                id=m.id,
                title=m.title,
                description=m.description,
                status=m.status,
                resolution_outcome=m.resolution_outcome,
                liquidity_pool=float(m.liquidity_pool),
                fee_percentage=float(m.fee_percentage),
                created_at=m.created_at,
                ends_at=m.ends_at,
            )
            for m in markets
        ]
    
    @strawberry.field
    def market(self, id: int) -> Optional[MarketType]:
        """Get a specific market by ID"""
        from markets.models import Market
        try:
            m = Market.objects.get(id=id)
            return MarketType(
                id=m.id,
                title=m.title,
                description=m.description,
                status=m.status,
                resolution_outcome=m.resolution_outcome,
                liquidity_pool=float(m.liquidity_pool),
                fee_percentage=float(m.fee_percentage),
                created_at=m.created_at,
                ends_at=m.ends_at,
            )
        except Market.DoesNotExist:
            return None

schema = strawberry.Schema(query=Query)

