from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import JSONField

User = get_user_model()


class PollAnalytics(models.Model):
    """Aggregated analytics data for polls"""

    poll = models.OneToOneField(
        'polls.Poll',
        on_delete=models.CASCADE,
        related_name='analytics'
    )

    # Basic metrics
    total_votes = models.IntegerField(default=0)
    unique_voters = models.IntegerField(default=0)
    # % of users who complete all required questions
    completion_rate = models.FloatField(default=0.0)
    avg_time_spent = models.FloatField(
        default=0.0)  # average seconds spent on poll

    # Engagement metrics
    bookmark_count = models.IntegerField(default=0)
    share_count = models.IntegerField(default=0)
    view_count = models.IntegerField(default=0)

    # Geographic distribution
    votes_by_country = JSONField(default=dict)  # {'US': 100, 'CA': 50, ...}
    top_countries = JSONField(default=list)  # ['US', 'CA', 'UK', ...]

    # Time-series data (last 30 days)
    # {'0': 10, '1': 5, ...} (24 hours)
    votes_by_hour = JSONField(default=dict)
    # {'2024-01-01': 100, ...} (30 days)
    votes_by_day = JSONField(default=dict)

    # Platform distribution
    # {'mobile': 60, 'desktop': 40}
    votes_by_platform = JSONField(default=dict)

    # Revenue metrics (for paid polls)
    total_revenue = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    avg_revenue_per_vote = models.DecimalField(
        max_digits=8, decimal_places=2, default=0)

    # Conversion metrics
    view_to_vote_rate = models.FloatField(
        default=0.0)  # % of views that result in votes

    # Cache timestamps
    last_updated = models.DateTimeField(auto_now=True)
    last_calculated = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Poll Analytics"
        verbose_name_plural = "Poll Analytics"
        indexes = [
            models.Index(fields=['poll']),
            models.Index(fields=['last_updated']),
            models.Index(fields=['total_votes']),
            models.Index(fields=['completion_rate']),
        ]

    def __str__(self):
        return f"Analytics for {self.poll.title}"

    def update_basic_metrics(self):
        """Update basic analytics metrics"""
        from apps.polls.models import Vote, VoteSession

        # Calculate total votes and unique voters
        self.total_votes = Vote.objects.filter(
            choice__question__poll=self.poll
        ).count()

        self.unique_voters = VoteSession.objects.filter(
            poll=self.poll
        ).values('user', 'ip_address').distinct().count()

        # Calculate completion rate
        if self.unique_voters > 0:
            required_questions = self.poll.questions.filter(
                is_required=True).count()
            if required_questions > 0:
                from django.db.models import Count
                completed_sessions = VoteSession.objects.annotate(
                    votes_count=Count('votes')
                ).filter(
                    poll=self.poll,
                    votes_count__gte=required_questions
                ).count()

                self.completion_rate = (
                    completed_sessions / self.unique_voters) * 100

        # Update bookmarks and shares
        self.bookmark_count = self.poll.bookmarks.count()
        self.share_count = self.poll.shares.count()

        self.last_calculated = timezone.now()
        self.save()


class UserAnalytics(models.Model):
    """Aggregated analytics data for users"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='analytics'
    )

    # Poll creation metrics
    polls_created = models.IntegerField(default=0)
    active_polls = models.IntegerField(default=0)
    total_poll_views = models.IntegerField(default=0)

    # Voting metrics
    polls_voted = models.IntegerField(default=0)
    total_votes_made = models.IntegerField(default=0)
    total_votes_received = models.IntegerField(
        default=0)  # votes on user's polls

    # Engagement metrics
    bookmarks_made = models.IntegerField(default=0)
    shares_made = models.IntegerField(default=0)
    avg_session_duration = models.FloatField(default=0.0)

    # Revenue metrics (for paid features)
    total_revenue = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    total_spent = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)

    # Activity patterns
    most_active_hour = models.IntegerField(default=12)  # 0-23
    most_active_day = models.IntegerField(default=1)    # 1-7 (Monday-Sunday)

    # Geographic info
    primary_country = models.CharField(max_length=2, blank=True)

    # Cache timestamps
    last_updated = models.DateTimeField(auto_now=True)
    last_calculated = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "User Analytics"
        verbose_name_plural = "User Analytics"
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['total_revenue']),
            models.Index(fields=['polls_created']),
        ]

    def __str__(self):
        return f"Analytics for {self.user.username}"

    def update_metrics(self):
        """Update user analytics metrics"""
        from apps.polls.models import Vote, VoteSession
        from apps.payments.models import Transaction

        # Poll creation metrics
        user_polls = self.user.polls.all()
        self.polls_created = user_polls.count()
        self.active_polls = user_polls.filter(is_active=True).count()

        # Voting metrics
        self.polls_voted = VoteSession.objects.filter(
            user=self.user).values('poll').distinct().count()
        self.total_votes_made = Vote.objects.filter(
            choice__question__poll__vote_sessions__user=self.user
        ).count()

        # Calculate votes received on user's polls
        self.total_votes_received = Vote.objects.filter(
            choice__question__poll__creator=self.user
        ).count()

        # Engagement metrics
        self.bookmarks_made = self.user.bookmarks.count()
        self.shares_made = self.user.shares.count()

        # Revenue metrics (if payments app exists)
        try:
            revenue_transactions = Transaction.objects.filter(
                poll__creator=self.user,
                status='completed'
            )
            self.total_revenue = sum(t.amount for t in revenue_transactions)

            spent_transactions = Transaction.objects.filter(
                user=self.user,
                status='completed'
            )
            self.total_spent = sum(t.amount for t in spent_transactions)
        except:
            pass

        self.last_calculated = timezone.now()
        self.save()


class AnalyticsEvent(models.Model):
    """Raw events for detailed analytics tracking"""

    EVENT_TYPES = (
        ('poll_view', 'Poll Viewed'),
        ('poll_vote', 'Poll Vote'),
        ('poll_share', 'Poll Shared'),
        ('poll_bookmark', 'Poll Bookmarked'),
        ('user_register', 'User Registration'),
        ('user_login', 'User Login'),
        ('payment_made', 'Payment Made'),
        ('export_data', 'Data Export'),
    )

    DEVICE_TYPES = (
        ('mobile', 'Mobile'),
        ('desktop', 'Desktop'),
        ('tablet', 'Tablet'),
        ('unknown', 'Unknown'),
    )

    # Core event data
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='analytics_events'
    )

    # Related objects
    poll = models.ForeignKey(
        'polls.Poll',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='analytics_events'
    )

    # Request metadata
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    device_type = models.CharField(
        max_length=20, choices=DEVICE_TYPES, default='unknown')

    # Geographic data
    country_code = models.CharField(max_length=2, blank=True)
    region = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)

    # Additional event data
    metadata = JSONField(default=dict)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Analytics Event"
        verbose_name_plural = "Analytics Events"
        indexes = [
            models.Index(fields=['event_type', 'created_at']),
            models.Index(fields=['user', 'event_type']),
            models.Index(fields=['poll', 'event_type']),
            models.Index(fields=['country_code', 'created_at']),
            models.Index(fields=['device_type', 'created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.event_type} - {self.ip_address} - {self.created_at}"


class AnalyticsSnapshot(models.Model):
    """Daily/hourly snapshots for trend analysis"""

    SNAPSHOT_TYPES = (
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    )

    snapshot_type = models.CharField(max_length=20, choices=SNAPSHOT_TYPES)
    timestamp = models.DateTimeField()

    # System-wide metrics
    total_users = models.IntegerField(default=0)
    active_users = models.IntegerField(default=0)  # users active in period
    total_polls = models.IntegerField(default=0)
    active_polls = models.IntegerField(default=0)
    total_votes = models.IntegerField(default=0)
    new_votes = models.IntegerField(default=0)  # votes in period

    # Revenue metrics
    total_revenue = models.DecimalField(
        max_digits=12, decimal_places=2, default=0)
    new_revenue = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)

    # Engagement metrics
    avg_session_duration = models.FloatField(default=0.0)
    bounce_rate = models.FloatField(default=0.0)

    # Geographic breakdown
    top_countries = JSONField(default=list)
    country_distribution = JSONField(default=dict)

    # Detailed metrics
    metrics = JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Analytics Snapshot"
        verbose_name_plural = "Analytics Snapshots"
        unique_together = ('snapshot_type', 'timestamp')
        indexes = [
            models.Index(fields=['snapshot_type', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.snapshot_type} snapshot - {self.timestamp}"
