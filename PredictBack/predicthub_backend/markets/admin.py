from django.contrib import admin
from .models import Market, MarketCategory, OutcomeToken, PriceHistory, Resolution


@admin.register(MarketCategory)
class MarketCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'status', 'liquidity_pool', 'created_at', 'ends_at']
    list_filter = ['status', 'category', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'category', 'created_by')
        }),
        ('Market Details', {
            'fields': ('status', 'resolution_outcome', 'liquidity_pool', 'fee_percentage')
        }),
        ('Timing', {
            'fields': ('created_at', 'ends_at')
        }),
    )


@admin.register(OutcomeToken)
class OutcomeTokenAdmin(admin.ModelAdmin):
    list_display = ['market', 'outcome_type', 'price', 'supply', 'updated_at']
    list_filter = ['outcome_type', 'updated_at']
    search_fields = ['market__title']
    readonly_fields = ['updated_at']


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ['market', 'yes_price', 'no_price', 'timestamp']
    list_filter = ['timestamp']
    search_fields = ['market__title']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'


@admin.register(Resolution)
class ResolutionAdmin(admin.ModelAdmin):
    list_display = ['market', 'resolved_outcome', 'resolver', 'dispute_window', 'created_at']
    list_filter = ['resolved_outcome', 'created_at']
    search_fields = ['market__title']
    readonly_fields = ['created_at']

