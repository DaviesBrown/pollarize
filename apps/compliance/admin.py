from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from .models import ComplianceLog, GeolocationCache, ComplianceRule


@admin.register(ComplianceLog)
class ComplianceLogAdmin(admin.ModelAdmin):
    list_display = [
        'created_at', 'action', 'status', 'ip_address', 'country_code',
        'poll_link', 'user_link', 'blocked_reason_short'
    ]
    list_filter = [
        'action', 'status', 'country_code', 'created_at'
    ]
    search_fields = [
        'ip_address', 'blocked_reason', 'poll__title', 'user__username'
    ]
    readonly_fields = [
        'created_at', 'poll', 'user', 'ip_address', 'action', 'status',
        'country_code', 'blocked_reason', 'metadata', 'request_path', 'user_agent'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    def has_add_permission(self, request):
        return False  # Logs are created automatically

    def has_change_permission(self, request, obj=None):
        return False  # Logs should not be modified

    def poll_link(self, obj):
        if obj.poll:
            url = reverse('admin:polls_poll_change', args=[obj.poll.id])
            return format_html('<a href="{}">{}</a>', url, obj.poll.title)
        return '-'
    poll_link.short_description = 'Poll'

    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:core_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return '-'
    user_link.short_description = 'User'

    def blocked_reason_short(self, obj):
        if len(obj.blocked_reason) > 50:
            return obj.blocked_reason[:50] + '...'
        return obj.blocked_reason
    blocked_reason_short.short_description = 'Reason'


@admin.register(GeolocationCache)
class GeolocationCacheAdmin(admin.ModelAdmin):
    list_display = [
        'ip_address', 'country_code', 'country_name', 'city',
        'provider', 'is_valid', 'expires_at', 'is_expired_display'
    ]
    list_filter = [
        'country_code', 'provider', 'is_valid', 'expires_at'
    ]
    search_fields = [
        'ip_address', 'country_name', 'city'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'is_expired_display'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    def is_expired_display(self, obj):
        is_expired = obj.is_expired()
        color = 'red' if is_expired else 'green'
        text = 'Expired' if is_expired else 'Valid'
        return format_html('<span style="color: {};">{}</span>', color, text)
    is_expired_display.short_description = 'Status'

    actions = ['clear_expired_entries']

    def clear_expired_entries(self, request, queryset):
        from django.utils import timezone
        expired_count = GeolocationCache.objects.filter(
            expires_at__lt=timezone.now()
        ).delete()[0]

        self.message_user(
            request,
            f'Cleared {expired_count} expired geolocation cache entries.'
        )
    clear_expired_entries.short_description = 'Clear expired cache entries'


@admin.register(ComplianceRule)
class ComplianceRuleAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'rule_type', 'is_active', 'applies_to_all_polls',
        'specific_polls_count', 'created_at'
    ]
    list_filter = [
        'rule_type', 'is_active', 'applies_to_all_polls', 'created_at'
    ]
    search_fields = [
        'name', 'description'
    ]
    filter_horizontal = ['specific_polls']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'rule_type', 'description', 'is_active')
        }),
        ('Rule Configuration', {
            'fields': ('config',),
            'description': 'JSON configuration for the rule. Format depends on rule type.'
        }),
        ('Scope', {
            'fields': ('applies_to_all_polls', 'specific_polls'),
            'description': 'Define which polls this rule applies to.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    readonly_fields = ['created_at', 'updated_at']

    def specific_polls_count(self, obj):
        return obj.specific_polls.count()
    specific_polls_count.short_description = 'Specific Polls'

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('specific_polls')


# Add some custom admin views for reports
class ComplianceReportView:
    """Custom admin view for compliance reports"""

    def compliance_stats_view(self, request):
        from django.shortcuts import render
        from django.db.models import Count
        from datetime import timedelta
        from django.utils import timezone

        # Get last 30 days of data
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)

        logs = ComplianceLog.objects.filter(created_at__gte=start_date)

        # Calculate stats
        stats = {
            'total_logs': logs.count(),
            'blocked_requests': logs.filter(status='blocked').count(),
            'allowed_requests': logs.filter(status='allowed').count(),
            'flagged_requests': logs.filter(status='flagged').count(),
        }

        # Top countries
        top_countries = logs.values('country_code').annotate(
            count=Count('id')
        ).order_by('-count')[:10]

        # Daily breakdown
        daily_stats = logs.extra(
            select={'day': 'date(created_at)'}
        ).values('day').annotate(
            total=Count('id'),
            blocked=Count('id', filter=models.Q(status='blocked'))
        ).order_by('day')

        context = {
            'title': 'Compliance Statistics',
            'stats': stats,
            'top_countries': top_countries,
            'daily_stats': daily_stats,
            'date_range': f"{start_date.date()} to {end_date.date()}"
        }

        return render(request, 'admin/compliance_stats.html', context)
