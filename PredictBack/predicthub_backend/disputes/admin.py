from django.contrib import admin
from .models import Dispute


@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ['market', 'user', 'status', 'bond_amount', 'created_at', 'resolved_at']
    list_filter = ['status', 'created_at']
    search_fields = ['market__title', 'user__username', 'reason']
    readonly_fields = ['created_at', 'resolved_at']
    date_hierarchy = 'created_at'

