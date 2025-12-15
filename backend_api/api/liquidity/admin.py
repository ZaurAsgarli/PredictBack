from django.contrib import admin
from .models import LiquidityEvent


@admin.register(LiquidityEvent)
class LiquidityEventAdmin(admin.ModelAdmin):
    list_display = ['market', 'user', 'event_type', 'amount', 'created_at']
    list_filter = ['event_type', 'created_at']
    search_fields = ['market__title', 'user__username']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

