from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import PollAnalytics, UserAnalytics, AnalyticsEvent, AnalyticsSnapshot

User = get_user_model()


class PollAnalyticsSerializer(serializers.ModelSerializer):
    poll_title = serializers.CharField(source='poll.title', read_only=True)
    poll_creator = serializers.CharField(
        source='poll.creator.username', read_only=True)
    poll_is_paid = serializers.BooleanField(
        source='poll.is_paid', read_only=True)

    class Meta:
        model = PollAnalytics
        fields = [
            'id', 'poll', 'poll_title', 'poll_creator', 'poll_is_paid',
            'total_votes', 'unique_voters', 'completion_rate', 'avg_time_spent',
            'bookmark_count', 'share_count', 'view_count', 'votes_by_country',
            'top_countries', 'votes_by_hour', 'votes_by_day', 'votes_by_platform',
            'total_revenue', 'avg_revenue_per_vote', 'view_to_vote_rate',
            'last_updated', 'last_calculated'
        ]
        read_only_fields = fields


class UserAnalyticsSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_date_joined = serializers.DateTimeField(
        source='user.date_joined', read_only=True)

    class Meta:
        model = UserAnalytics
        fields = [
            'id', 'user', 'username', 'user_email', 'user_date_joined',
            'polls_created', 'active_polls', 'total_poll_views', 'polls_voted',
            'total_votes_made', 'total_votes_received', 'bookmarks_made', 'shares_made',
            'avg_session_duration', 'total_revenue', 'total_spent', 'most_active_hour',
            'most_active_day', 'primary_country', 'last_updated', 'last_calculated'
        ]
        read_only_fields = fields


class AnalyticsEventSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    poll_title = serializers.CharField(source='poll.title', read_only=True)

    class Meta:
        model = AnalyticsEvent
        fields = [
            'id', 'event_type', 'user', 'username', 'poll', 'poll_title',
            'ip_address', 'user_agent', 'device_type', 'country_code',
            'region', 'city', 'metadata', 'created_at'
        ]
        read_only_fields = fields


class AnalyticsSnapshotSerializer(serializers.ModelSerializer):

    class Meta:
        model = AnalyticsSnapshot
        fields = [
            'id', 'snapshot_type', 'timestamp', 'total_users', 'active_users',
            'total_polls', 'active_polls', 'total_votes', 'new_votes',
            'total_revenue', 'new_revenue', 'avg_session_duration', 'bounce_rate',
            'top_countries', 'country_distribution', 'metrics', 'created_at'
        ]
        read_only_fields = fields


class PollAnalyticsSummarySerializer(serializers.Serializer):
    """Serializer for poll analytics summary"""
    poll_id = serializers.IntegerField()
    poll_title = serializers.CharField()
    total_votes = serializers.IntegerField()
    unique_voters = serializers.IntegerField()
    completion_rate = serializers.FloatField()
    view_count = serializers.IntegerField()
    view_to_vote_rate = serializers.FloatField()
    revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    top_country = serializers.CharField()
    peak_voting_hour = serializers.IntegerField()


class UserAnalyticsSummarySerializer(serializers.Serializer):
    """Serializer for user analytics summary"""
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    polls_created = serializers.IntegerField()
    total_votes_made = serializers.IntegerField()
    total_votes_received = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    engagement_score = serializers.FloatField()
    primary_country = serializers.CharField()


class AnalyticsDashboardSerializer(serializers.Serializer):
    """Serializer for analytics dashboard data"""

    # Overview metrics
    total_polls = serializers.IntegerField()
    total_votes = serializers.IntegerField()
    total_users = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)

    # Period comparisons
    polls_change = serializers.FloatField()
    votes_change = serializers.FloatField()
    users_change = serializers.FloatField()
    revenue_change = serializers.FloatField()

    # Charts data
    votes_trend = serializers.DictField()
    revenue_trend = serializers.DictField()
    user_growth = serializers.DictField()
    geographic_distribution = serializers.DictField()

    # Top performers
    top_polls = serializers.ListField()
    top_creators = serializers.ListField()
    top_countries = serializers.ListField()


class ExportAnalyticsSerializer(serializers.Serializer):
    """Serializer for analytics export requests"""

    EXPORT_TYPES = (
        ('poll', 'Poll Analytics'),
        ('user', 'User Analytics'),
        ('events', 'Analytics Events'),
        ('compliance', 'Compliance Logs'),
    )

    EXPORT_FORMATS = (
        ('csv', 'CSV'),
        ('json', 'JSON'),
        ('xlsx', 'Excel'),
    )

    export_type = serializers.ChoiceField(choices=EXPORT_TYPES)
    export_format = serializers.ChoiceField(
        choices=EXPORT_FORMATS, default='csv')
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)
    poll_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True
    )
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True
    )
    include_metadata = serializers.BooleanField(default=False)

    def validate(self, data):
        """Validate export request"""
        date_from = data.get('date_from')
        date_to = data.get('date_to')

        if date_from and date_to and date_from >= date_to:
            raise serializers.ValidationError(
                "date_from must be before date_to"
            )

        # Limit date range to prevent huge exports
        if date_from and date_to:
            from datetime import timedelta
            max_range = timedelta(days=365)  # 1 year max

            if date_to - date_from > max_range:
                raise serializers.ValidationError(
                    "Date range cannot exceed 365 days"
                )

        return data
