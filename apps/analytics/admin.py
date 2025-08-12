from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Sum
from .models import PollAnalytics, UserAnalytics, AnalyticsEvent, AnalyticsSnapshot


@admin.register(PollAnalytics)
class PollAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'poll_link', 'total_votes', 'unique_voters', 'completion_rate',
        'total_revenue', 'view_to_vote_rate', 'last_updated'
    ]
    list_filter = [
        'poll__is_paid', 'poll__category', 'last_updated'
    ]
    search_fields = [
        'poll__title', 'poll__creator__username'
    ]
    readonly_fields = [
        'poll', 'total_votes', 'unique_voters', 'completion_rate',
        'avg_time_spent', 'bookmark_count', 'share_count', 'view_count',
        'votes_by_country', 'top_countries', 'votes_by_hour', 'votes_by_day',
        'votes_by_platform', 'total_revenue', 'avg_revenue_per_vote',
        'view_to_vote_rate', 'last_updated', 'last_calculated'
    ]
    date_hierarchy = 'last_updated'
    ordering = ['-last_updated']

    def has_add_permission(self, request):
        return False  # Analytics are created automatically

    def has_change_permission(self, request, obj=None):
        return False  # Analytics should not be manually modified

    def poll_link(self, obj):
        url = reverse('admin:polls_poll_change', args=[obj.poll.id])
        return format_html('<a href="{}">{}</a>', url, obj.poll.title)
    poll_link.short_description = 'Poll'

    def completion_rate(self, obj):
        rate = obj.completion_rate
        color = 'green' if rate >= 70 else 'orange' if rate >= 40 else 'red'
        return format_html('<span style="color: {};">{:.1f}%</span>', color, rate)
    completion_rate.short_description = 'Completion Rate'

    def view_to_vote_rate(self, obj):
        rate = obj.view_to_vote_rate
        color = 'green' if rate >= 20 else 'orange' if rate >= 10 else 'red'
        return format_html('<span style="color: {};">{:.1f}%</span>', color, rate)
    view_to_vote_rate.short_description = 'Conversion Rate'


@admin.register(UserAnalytics)
class UserAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'user_link', 'polls_created', 'total_votes_made', 'total_votes_received',
        'total_revenue', 'engagement_score_display', 'primary_country', 'last_updated'
    ]
    list_filter = [
        'primary_country', 'most_active_hour', 'last_updated'
    ]
    search_fields = [
        'user__username', 'user__email'
    ]
    readonly_fields = [
        'user', 'polls_created', 'active_polls', 'total_poll_views',
        'polls_voted', 'total_votes_made', 'total_votes_received',
        'bookmarks_made', 'shares_made', 'avg_session_duration',
        'total_revenue', 'total_spent', 'most_active_hour', 'most_active_day',
        'primary_country', 'last_updated', 'last_calculated'
    ]
    date_hierarchy = 'last_updated'
    ordering = ['-last_updated']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def user_link(self, obj):
        url = reverse('admin:core_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'

    def engagement_score_display(self, obj):
        # Calculate engagement score
        score = (
            obj.polls_created * 10 +
            obj.total_votes_made * 2 +
            obj.bookmarks_made * 1 +
            obj.shares_made * 5
        ) / 100.0

        color = 'green' if score >= 50 else 'orange' if score >= 20 else 'red'
        return format_html('<span style="color: {};">{:.1f}</span>', color, score)
    engagement_score_display.short_description = 'Engagement Score'


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    list_display = [
        'created_at', 'event_type', 'user_link', 'poll_link',
        'country_code', 'device_type', 'ip_address'
    ]
    list_filter = [
        'event_type', 'device_type', 'country_code', 'created_at'
    ]
    search_fields = [
        'user__username', 'poll__title', 'ip_address'
    ]
    readonly_fields = [
        'event_type', 'user', 'poll', 'ip_address', 'user_agent',
        'device_type', 'country_code', 'region', 'city', 'metadata', 'created_at'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:core_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return '-'
    user_link.short_description = 'User'

    def poll_link(self, obj):
        if obj.poll:
            url = reverse('admin:polls_poll_change', args=[obj.poll.id])
            return format_html('<a href="{}">{}</a>', url, obj.poll.title)
        return '-'
    poll_link.short_description = 'Poll'

    # Limit queryset to recent events for performance
    def get_queryset(self, request):
        from datetime import timedelta
        from django.utils import timezone

        qs = super().get_queryset(request)
        # Only show events from last 30 days by default
        recent_date = timezone.now() - timedelta(days=30)
        return qs.filter(created_at__gte=recent_date)


@admin.register(AnalyticsSnapshot)
class AnalyticsSnapshotAdmin(admin.ModelAdmin):
    list_display = [
        'timestamp', 'snapshot_type', 'total_users', 'active_users',
        'total_polls', 'total_votes', 'new_votes', 'total_revenue', 'new_revenue'
    ]
    list_filter = [
        'snapshot_type', 'timestamp'
    ]
    readonly_fields = [
        'snapshot_type', 'timestamp', 'total_users', 'active_users',
        'total_polls', 'active_polls', 'total_votes', 'new_votes',
        'total_revenue', 'new_revenue', 'avg_session_duration', 'bounce_rate',
        'top_countries', 'country_distribution', 'metrics', 'created_at'
    ]
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# Custom admin site modifications
class AnalyticsAdminSite:
    """Custom analytics admin views"""

    def get_urls(self):
        from django.urls import path

        urls = [
            path('analytics-dashboard/', self.analytics_dashboard_view,
                 name='analytics-dashboard'),
        ]
        return urls

    def analytics_dashboard_view(self, request):
        from django.shortcuts import render
        from datetime import timedelta
        from django.utils import timezone
        from django.db.models import Count, Sum, Avg

        # Get summary statistics
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)

        # Basic metrics
        total_polls = PollAnalytics.objects.count()
        total_users = UserAnalytics.objects.count()
        total_events = AnalyticsEvent.objects.filter(
            created_at__gte=start_date).count()

        # Revenue metrics
        total_revenue = PollAnalytics.objects.aggregate(
            total=Sum('total_revenue')
        )['total'] or 0

        # Top performing polls
        top_polls = PollAnalytics.objects.select_related('poll').order_by(
            '-total_votes'
        )[:10]

        # Top countries
        top_countries = AnalyticsEvent.objects.filter(
            created_at__gte=start_date
        ).values('country_code').annotate(
            count=Count('id')
        ).order_by('-count')[:10]

        # Event distribution
        event_distribution = AnalyticsEvent.objects.filter(
            created_at__gte=start_date
        ).values('event_type').annotate(
            count=Count('id')
        ).order_by('-count')

        context = {
            'title': 'Analytics Dashboard',
            'total_polls': total_polls,
            'total_users': total_users,
            'total_events': total_events,
            'total_revenue': total_revenue,
            'top_polls': top_polls,
            'top_countries': top_countries,
            'event_distribution': event_distribution,
            'date_range': f"{start_date.date()} to {end_date.date()}"
        }

        return render(request, 'admin/analytics_dashboard.html', context)
