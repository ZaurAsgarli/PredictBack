from rest_framework import serializers
from decimal import Decimal
from .models import Trade
from backend_api.api.markets.serializers import MarketSerializer
from backend_api.api.markets.models import Market
from backend_api.api.users.serializers import UserSerializer


class TradeSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    market = MarketSerializer(read_only=True)
    market_id = serializers.PrimaryKeyRelatedField(
        queryset=Market.objects.all(),
        source='market',
        write_only=True
    )
    
    class Meta:
        model = Trade
        fields = [
            'id', 'user', 'market', 'market_id', 'outcome_type',
            'trade_type', 'amount_staked', 'tokens_amount',
            'price_at_execution', 'created_at'
        ]
        read_only_fields = ['user', 'created_at']


class TradeCreateSerializer(serializers.Serializer):
    """Serializer for creating a trade"""
    market_id = serializers.IntegerField()
    outcome_type = serializers.ChoiceField(choices=['YES', 'NO'])
    trade_type = serializers.ChoiceField(choices=['buy', 'sell'])
    amount_staked = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0'))
    
    def validate(self, attrs):
        market_id = attrs['market_id']
        try:
            market = Market.objects.get(id=market_id)
        except Market.DoesNotExist:
            raise serializers.ValidationError("Market not found")
        
        if market.status != 'active':
            raise serializers.ValidationError("Market is not active")
        
        return attrs

