from rest_framework import viewsets, status, permissions
from rest_framework.decorators import api_view, permission_classes
from django.core.exceptions import ValidationError
from decimal import Decimal, InvalidOperation
import traceback
import logging
from .models import Trade
from .serializers import TradeSerializer, TradeCreateSerializer
from backend_api.api.markets.models import Market
from backend_api.api.positions.models import Position
from backend_api.api.positions.serializers import PositionSerializer
from .services import TradeExecutionService
from backend_api.core.utils.serializer import success, error

logger = logging.getLogger(__name__)


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
    try:
        # Validate user (already authenticated via permission_classes)
        user = request.user
        if user is None:
            return error('User authentication failed', status.HTTP_401_UNAUTHORIZED)
        
        # Validate request data
        serializer = TradeCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return error(f"Validation error: {serializer.errors}", status.HTTP_400_BAD_REQUEST)
        
        # Extract and validate market
        market_id = serializer.validated_data.get('market_id')
        if market_id is None:
            return error('market_id is required', status.HTTP_400_BAD_REQUEST)
        
        try:
            market = Market.objects.get(id=market_id)
        except Market.DoesNotExist:
            return error(f'Market not found with id: {market_id}', status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error fetching market {market_id}: {str(e)}")
            traceback.print_exc()
            return error(f'Error fetching market: {str(e)}', status.HTTP_400_BAD_REQUEST)
        
        # Validate market status
        if market.status != 'active':
            return error(f'Market is not active. Current status: {market.status}', status.HTTP_400_BAD_REQUEST)
        
        # Extract and validate outcome_type
        outcome_type = serializer.validated_data.get('outcome_type')
        if outcome_type is None:
            return error('outcome_type is required', status.HTTP_400_BAD_REQUEST)
        if outcome_type not in ['YES', 'NO']:
            return error(f'Invalid outcome_type: {outcome_type}. Must be YES or NO', status.HTTP_400_BAD_REQUEST)
        
        # Extract trade details
        trade_type = serializer.validated_data.get('trade_type')
        if trade_type is None:
            return error('trade_type is required', status.HTTP_400_BAD_REQUEST)
        
        amount_staked_raw = serializer.validated_data.get('amount_staked')
        if amount_staked_raw is None:
            return error('amount_staked is required', status.HTTP_400_BAD_REQUEST)
        
        try:
            amount = Decimal(str(amount_staked_raw))
        except (InvalidOperation, ValueError, TypeError) as e:
            logger.error(f"Invalid amount_staked value: {amount_staked_raw}, Error: {str(e)}")
            traceback.print_exc()
            return error(f'Invalid amount_staked: {amount_staked_raw}. Must be a valid number', status.HTTP_400_BAD_REQUEST)
        
        if amount <= 0:
            return error('amount_staked must be greater than zero', status.HTTP_400_BAD_REQUEST)
        
        # Convert trade_type to side (BUY/SELL)
        if trade_type == 'buy':
            side = 'BUY'
        elif trade_type == 'sell':
            side = 'SELL'
        else:
            return error(f'Invalid trade_type: {trade_type}. Must be buy or sell', status.HTTP_400_BAD_REQUEST)
        
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
            logger.warning(f"Trade validation error: {str(e)}")
            return error(str(e), status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Trade execution failed: {str(e)}")
            logger.error(f"Trade execution error type: {type(e).__name__}")
            traceback.print_exc()
            return error(f'Trade execution failed: {str(e)}', status.HTTP_400_BAD_REQUEST)
        
        # Validate result structure
        if result is None:
            logger.error("TradeExecutionService.execute_trade returned None")
            traceback.print_exc()
            return error('Trade execution returned no result', status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        if 'trade_id' not in result:
            logger.error(f"Trade execution result missing trade_id: {result}")
            traceback.print_exc()
            return error('Trade execution result missing trade_id', status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Get the created trade
        try:
            trade = Trade.objects.get(id=result['trade_id'])
        except Trade.DoesNotExist:
            logger.error(f"Trade {result['trade_id']} was created but could not be retrieved")
            traceback.print_exc()
            return error(f'Trade was created but could not be retrieved (id: {result["trade_id"]})', status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Error retrieving trade {result['trade_id']}: {str(e)}")
            traceback.print_exc()
            return error(f'Error retrieving trade: {str(e)}', status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Get the updated position
        try:
            position = Position.objects.get(user=user, market=market)
        except Position.DoesNotExist:
            logger.error(f"Position for user {user.id} and market {market.id} was created but could not be retrieved")
            traceback.print_exc()
            return error('Position was created but could not be retrieved', status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Error retrieving position: {str(e)}")
            traceback.print_exc()
            return error(f'Error retrieving position: {str(e)}', status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Serialize trade and position
        try:
            trade_serializer = TradeSerializer(trade)
            position_serializer = PositionSerializer(position)
        except Exception as e:
            logger.error(f"Error serializing trade/position: {str(e)}")
            traceback.print_exc()
            return error(f'Error serializing response: {str(e)}', status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Prepare response data
        try:
            response_data = {
                'trade': trade_serializer.data,
                'position': position_serializer.data,
                'price': result.get('prices', {})
            }
        except Exception as e:
            logger.error(f"Error preparing response data: {str(e)}")
            traceback.print_exc()
            return error(f'Error preparing response: {str(e)}', status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return success(response_data)
        
    except Exception as e:
        # Catch-all for any unexpected errors
        logger.error(f"Unexpected error in create_trade: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        traceback.print_exc()
        return error(f'Internal server error: {str(e)}', status.HTTP_500_INTERNAL_SERVER_ERROR)


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

