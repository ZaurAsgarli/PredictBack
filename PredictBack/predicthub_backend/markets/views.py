from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from .models import Market, MarketCategory, OutcomeToken, PriceHistory, Resolution
from .serializers import (
    MarketSerializer, MarketCreateSerializer, MarketCategorySerializer,
    PriceHistorySerializer, ResolutionSerializer
)
from trades.models import Trade
from positions.models import Position
from utils.serializer import success, error


class MarketViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Market operations"""
    queryset = Market.objects.select_related('category', 'created_by').prefetch_related('outcome_tokens').all()
    serializer_class = MarketSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status', None)
        category_filter = self.request.query_params.get('category', None)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if category_filter:
            queryset = queryset.filter(category__slug=category_filter)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured markets (active markets with highest liquidity)"""
        featured = self.queryset.filter(
            status='active',
            ends_at__gt=timezone.now()
        ).order_by('-liquidity_pool')[:10]
        serializer = self.get_serializer(featured, many=True)
        return success(serializer.data)
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Get all market categories"""
        categories = MarketCategory.objects.all()
        serializer = MarketCategorySerializer(categories, many=True)
        return success(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def resolve(self, request, pk=None):
        """Resolve a market (admin only)"""
        market = self.get_object()
        
        if market.status == 'resolved':
            return error('Market already resolved', status.HTTP_400_BAD_REQUEST)
        
        resolved_outcome = request.data.get('resolved_outcome')
        if resolved_outcome not in ['YES', 'NO']:
            return error('Invalid outcome. Must be YES or NO', status.HTTP_400_BAD_REQUEST)
        
        # Create resolution
        dispute_window = timezone.now() + timedelta(hours=settings.MARKET_DISPUTE_WINDOW_HOURS)
        resolution = Resolution.objects.create(
            market=market,
            resolved_outcome=resolved_outcome,
            resolver=request.user,
            dispute_window=dispute_window,
            bond_amount=settings.MARKET_DEFAULT_BOND_AMOUNT
        )
        
        # Update market status
        market.status = 'resolved'
        market.resolution_outcome = resolved_outcome
        market.save()
        
        # Settle positions (this would trigger Celery task in production)
        from trades.tasks import settle_market_positions
        settle_market_positions.delay(market.id, resolved_outcome)
        
        serializer = ResolutionSerializer(resolution)
        return success(serializer.data)
    
    @action(detail=True, methods=['get'])
    def trades(self, request, pk=None):
        """Get trades for a specific market"""
        market = self.get_object()
        trades = Trade.objects.filter(market=market).order_by('-created_at')
        
        from trades.serializers import TradeSerializer
        from rest_framework.pagination import PageNumberPagination
        
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(trades, request)
        serializer = TradeSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def position(self, request, pk=None):
        """Get user's position for a specific market"""
        market = self.get_object()
        if not request.user.is_authenticated:
            return error('Authentication required', status.HTTP_401_UNAUTHORIZED)
        
        position, created = Position.objects.get_or_create(
            user=request.user,
            market=market,
            defaults={'yes_tokens': 0, 'no_tokens': 0, 'total_staked': 0}
        )
        
        from positions.serializers import PositionSerializer
        serializer = PositionSerializer(position)
        return success(serializer.data)


class MarketCreateViewSet(viewsets.ModelViewSet):
    """ViewSet for creating markets (admin only)"""
    queryset = Market.objects.all()
    serializer_class = MarketCreateSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return MarketCreateSerializer
        return MarketSerializer
    
    def perform_create(self, serializer):
        market = serializer.save()
        
        # Create outcome tokens
        OutcomeToken.objects.create(market=market, outcome_type='YES', supply=0, price=0.5)
        OutcomeToken.objects.create(market=market, outcome_type='NO', supply=0, price=0.5)
        
        # Create initial price history
        PriceHistory.objects.create(
            market=market,
            yes_price=0.5,
            no_price=0.5
        )

