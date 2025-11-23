"""
Admin views for indexer monitoring
"""
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render
from django.db.models import Count, Q
from django.contrib.admin import AdminSite
from .models import OnchainTransaction, OnchainEventLog
from utils.contracts import get_contract_service


@admin.register(OnchainTransaction)
class OnchainTransactionAdmin(admin.ModelAdmin):
    list_display = ['tx_hash_short', 'network', 'block_number', 'status', 'created_at']
    list_filter = ['status', 'network', 'created_at']
    search_fields = ['tx_hash']
    readonly_fields = ['tx_hash', 'network', 'block_number', 'status', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    def tx_hash_short(self, obj):
        return f"{obj.tx_hash[:10]}...{obj.tx_hash[-8:]}"
    tx_hash_short.short_description = 'Transaction Hash'


@admin.register(OnchainEventLog)
class OnchainEventLogAdmin(admin.ModelAdmin):
    list_display = ['event_name', 'tx_hash_short', 'log_index', 'market_link', 'processed_at', 'duplicate']
    list_filter = ['event_name', 'duplicate', 'processed_at', 'created_at']
    search_fields = ['tx_hash', 'user_address', 'event_name']
    readonly_fields = ['onchain_tx', 'event_name', 'tx_hash', 'log_index', 'market', 'user_address', 
                      'payload_json', 'processed_at', 'duplicate', 'created_at']
    ordering = ['-created_at']
    
    def tx_hash_short(self, obj):
        return f"{obj.tx_hash[:10]}...{obj.tx_hash[-8:]}"
    tx_hash_short.short_description = 'Transaction Hash'
    
    def market_link(self, obj):
        if obj.market:
            return format_html('<a href="/admin/markets/market/{}/change/">{}</a>', 
                             obj.market.id, obj.market.title)
        return '-'
    market_link.short_description = 'Market'


def recent_events_view(request):
    """View recent blockchain events"""
    from .models import OnchainEventLog
    recent_events = OnchainEventLog.objects.select_related('market', 'onchain_tx').order_by('-created_at')[:50]
    
    event_stats = OnchainEventLog.objects.values('event_name').annotate(
        count=Count('id')
    ).order_by('-count')
    
    context = {
        'recent_events': recent_events,
        'event_stats': event_stats,
        'title': 'Recent Blockchain Events',
    }
    return render(request, 'admin/indexer/recent_events.html', context)


def backfill_status_view(request):
    """View backfill status"""
    import os
    import json
    from django.conf import settings
    from .models import OnchainEventLog
    
    logs_dir = os.path.join(settings.BASE_DIR, 'LOGS', 'etl')
    backfill_logs = []
    
    if os.path.exists(logs_dir):
        for filename in sorted(os.listdir(logs_dir), reverse=True):
            if filename.startswith('backfill_') and filename.endswith('.json'):
                filepath = os.path.join(logs_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        log_data = json.load(f)
                        log_data['filename'] = filename
                        backfill_logs.append(log_data)
                except:
                    pass
    
    context = {
        'backfill_logs': backfill_logs[:20],  # Last 20
        'title': 'Backfill Status',
    }
    return render(request, 'admin/indexer/backfill_status.html', context)


def heartbeat_view(request):
    """View indexer heartbeat/health status"""
    from .models import OnchainEventLog, OnchainTransaction
    
    contract_service = get_contract_service()
    is_connected = contract_service.is_connected()
    latest_block = contract_service.get_latest_block() if is_connected else None
    
    # Recent processing stats
    last_hour = timezone.now() - timezone.timedelta(hours=1)
    recent_events = OnchainEventLog.objects.filter(created_at__gte=last_hour)
    processed_count = recent_events.filter(processed_at__isnull=False).count()
    duplicate_count = recent_events.filter(duplicate=True).count()
    
    # Error rate
    recent_errors = OnchainTransaction.objects.filter(
        created_at__gte=last_hour,
        status='FAILED'
    ).count()
    
    context = {
        'is_connected': is_connected,
        'latest_block': latest_block,
        'contract_address': contract_service.contract_address if is_connected else None,
        'recent_events_count': recent_events.count(),
        'processed_count': processed_count,
        'duplicate_count': duplicate_count,
        'error_count': recent_errors,
        'title': 'Indexer Heartbeat',
    }
    return render(request, 'admin/indexer/heartbeat.html', context)


# Note: Monitoring views are registered in config/urls.py
# from django.contrib.admin import admin
# from indexer.admin import recent_events_view, backfill_status_view, heartbeat_view
# 
# urlpatterns += [
#     path('admin/indexer/recent-events/', admin.site.admin_view(recent_events_view), name='indexer_recent_events'),
#     path('admin/indexer/backfill-status/', admin.site.admin_view(backfill_status_view), name='indexer_backfill_status'),
#     path('admin/indexer/heartbeat/', admin.site.admin_view(heartbeat_view), name='indexer_heartbeat'),
# ]

