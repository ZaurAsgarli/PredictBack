from django.contrib import admin
from .models import Trade


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ['user', 'market', 'outcome_type', 'trade_type', 'amount_staked', 'price_at_execution', 'created_at']
    list_filter = ['trade_type', 'outcome_type', 'created_at']
    search_fields = ['user__username', 'market__title']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

