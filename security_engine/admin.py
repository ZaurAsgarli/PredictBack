from django.contrib import admin
from .models import SecurityLog, LoginAttempt


@admin.register(SecurityLog)
class SecurityLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'event_type', 'severity', 'ip', 'path', 'user']
    list_filter = ['event_type', 'severity', 'timestamp']
    search_fields = ['ip', 'message', 'path']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        # Security logs should only be created by the system
        return False


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = [
        'timestamp', 'email', 'success', 'status', 'ip_address',
        'is_suspicious', 'risk_score', 'user'
    ]
    list_filter = [
        'success', 'status', 'is_suspicious', 'failure_reason',
        'timestamp', 'device_type'
    ]
    search_fields = ['email', 'ip_address', 'user_agent']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Authentication', {
            'fields': ('email', 'success', 'status', 'failure_reason', 'user')
        }),
        ('Request Details', {
            'fields': ('ip_address', 'user_agent', 'request_path')
        }),
        ('Device Information', {
            'fields': ('browser', 'os', 'device_type', 'country', 'city')
        }),
        ('Security', {
            'fields': ('is_suspicious', 'is_bot', 'risk_score', 'metadata')
        }),
        ('Timestamp', {
            'fields': ('timestamp',)
        }),
    )
    
    def has_add_permission(self, request):
        # Login attempts should only be created by the system
        return False

