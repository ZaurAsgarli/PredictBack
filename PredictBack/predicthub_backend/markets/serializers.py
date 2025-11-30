from rest_framework import serializers
from .models import Market, MarketCategory, OutcomeToken, PriceHistory, Resolution
from users.serializers import UserSerializer


class MarketCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketCategory
        fields = ['id', 'name', 'slug', 'description', 'created_at']


class OutcomeTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutcomeToken
        fields = ['id', 'outcome_type', 'price', 'supply', 'updated_at']


class MarketSerializer(serializers.ModelSerializer):
    category = MarketCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=MarketCategory.objects.all(),
        source='category',
        write_only=True
    )
    outcome_tokens = OutcomeTokenSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)
    prices = serializers.SerializerMethodField()
    
    class Meta:
        model = Market
        fields = [
            'id', 'title', 'description', 'category', 'category_id',
            'status', 'resolution_outcome', 'liquidity_pool', 'fee_percentage',
            'created_at', 'ends_at', 'created_by', 'outcome_tokens', 'prices'
        ]
        read_only_fields = ['created_at', 'created_by', 'status', 'resolution_outcome']
    
    def get_prices(self, obj):
        return obj.calculate_prices()


class MarketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Market
        fields = ['title', 'description', 'category', 'ends_at']
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class PriceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceHistory
        fields = ['id', 'market', 'yes_price', 'no_price', 'timestamp']


class ResolutionSerializer(serializers.ModelSerializer):
    resolver = UserSerializer(read_only=True)
    
    class Meta:
        model = Resolution
        fields = ['id', 'market', 'resolved_outcome', 'resolver', 'dispute_window', 'bond_amount', 'created_at']
        read_only_fields = ['resolver', 'created_at']

