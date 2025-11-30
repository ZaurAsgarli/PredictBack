from rest_framework import viewsets, status, permissions
from rest_framework.decorators import api_view, permission_classes
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import Trade
from .serializers import TradeSerializer, TradeCreateSerializer
from markets.models import Market
from positions.models import Position
from positions.serializers import PositionSerializer
from .services import TradeExecutionService
from utils.serializer import success, error


class TradeViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing trades"""
    queryset = Trade.objects.select_related('user', 'market').all()
    serializer_class = TradeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        market_id = self.request.query_params.get('market', None)
        
        if market_id:
            queryset = queryset.filter(market_id=market_id)
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Handle POST /trades/ - Create a new trade"""
        return create_trade(request)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_trade(request):
    """Create a trade using TradeExecutionService"""
    # Validate user (already authenticated via permission_classes)
    user = request.user
    
    # Validate request data
    serializer = TradeCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return error(f"Validation error: {serializer.errors}", status.HTTP_400_BAD_REQUEST)
    
    # Extract and validate market
    market_id = serializer.validated_data.get('market_id')
    try:
        market = Market.objects.get(id=market_id)
    except Market.DoesNotExist:
        return error('Market not found', status.HTTP_400_BAD_REQUEST)
    
    # Validate market status
    if market.status != 'active':
        return error('Market is not active', status.HTTP_400_BAD_REQUEST)
    
    # Extract and validate outcome_type
    outcome_type = serializer.validated_data.get('outcome_type')
    if outcome_type not in ['YES', 'NO']:
        return error('Invalid outcome_type. Must be YES or NO', status.HTTP_400_BAD_REQUEST)
    
    # Extract trade details
    trade_type = serializer.validated_data.get('trade_type')
    amount = Decimal(str(serializer.validated_data.get('amount_staked')))
    
    # Convert trade_type to side (BUY/SELL)
    if trade_type == 'buy':
        side = 'BUY'
    elif trade_type == 'sell':
        side = 'SELL'
    else:
        return error('Invalid trade_type. Must be buy or sell', status.HTTP_400_BAD_REQUEST)
    
    # Execute trade using TradeExecutionService
    try:
        result = TradeExecutionService.execute_trade(
            user=user,
            market=market,
            outcome_type=outcome_type,
            amount=amount,
            side=side
        )
    except ValidationError as e:
        return error(str(e), status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return error(f'Trade execution failed: {str(e)}', status.HTTP_400_BAD_REQUEST)
    
    # Get the created trade
    try:
        trade = Trade.objects.get(id=result['trade_id'])
    except Trade.DoesNotExist:
        return error('Trade was created but could not be retrieved', status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Get the updated position
    try:
        position = Position.objects.get(user=user, market=market)
    except Position.DoesNotExist:
        return error('Position was created but could not be retrieved', status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Serialize trade and position
    trade_serializer = TradeSerializer(trade)
    position_serializer = PositionSerializer(position)
    
    # Prepare response data
    response_data = {
        'trade': trade_serializer.data,
        'position': position_serializer.data,
        'price': result['prices']
    }
    
    return success(response_data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_trades(request):
    """Get current user's trades"""
    trades = Trade.objects.filter(user=request.user).order_by('-created_at')
    
    from rest_framework.pagination import PageNumberPagination
    paginator = PageNumberPagination()
    page = paginator.paginate_queryset(trades, request)
    serializer = TradeSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)

