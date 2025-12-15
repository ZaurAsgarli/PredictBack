from django.contrib import admin
from .models import Position


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ['user', 'market', 'yes_tokens', 'no_tokens', 'total_staked', 'updated_at']
    list_filter = ['updated_at']
    search_fields = ['user__username', 'market__title']
    readonly_fields = ['created_at', 'updated_at']

