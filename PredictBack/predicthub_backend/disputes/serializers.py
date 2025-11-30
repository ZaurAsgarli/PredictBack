from rest_framework import serializers
from .models import Dispute
from markets.serializers import MarketSerializer
from markets.models import Market
from users.serializers import UserSerializer


class DisputeSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    market = MarketSerializer(read_only=True)
    market_id = serializers.PrimaryKeyRelatedField(
        queryset=Market.objects.all(),
        source='market',
        write_only=True
    )
    
    class Meta:
        model = Dispute
        fields = [
            'id', 'market', 'market_id', 'user', 'bond_amount',
            'status', 'reason', 'created_at', 'resolved_at'
        ]
        read_only_fields = ['user', 'status', 'created_at', 'resolved_at']

