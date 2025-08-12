import logging
from datetime import timedelta
from typing import Dict, Any, Optional
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q
from django.contrib.auth import get_user_model
from .models import PollAnalytics, UserAnalytics, AnalyticsEvent, AnalyticsSnapshot

logger = logging.getLogger(__name__)
User = get_user_model()


class AnalyticsService:
    """Service for handling analytics calculations and aggregations"""

    def __init__(self):
        self.logger = logger

    def track_event(self, event_type: str, user=None, poll=None, ip_address: str = '',
                    country_code: str = '', device_type: str = 'unknown',
                    metadata: Dict = None) -> Optional[AnalyticsEvent]:
        """Track an analytics event"""
        try:
            event = AnalyticsEvent.objects.create(
                event_type=event_type,
                user=user,
                poll=poll,
                ip_address=ip_address,
                country_code=country_code,
                device_type=device_type,
                metadata=metadata or {}
            )

            # Trigger real-time updates for important events
            if event_type in ['poll_vote', 'poll_view']:
                self._update_poll_analytics_realtime(poll)

            return event
        except Exception as e:
            self.logger.error(f"Error tracking analytics event: {e}")
            return None

    def update_poll_analytics(self, poll_id: int = None) -> bool:
        """Update analytics for a specific poll or all active polls"""
        from apps.polls.models import Poll, Vote, VoteSession

        try:
            if poll_id:
                polls = Poll.objects.filter(id=poll_id)
            else:
                polls = Poll.objects.filter(is_active=True)

            for poll in polls:
                analytics, created = PollAnalytics.objects.get_or_create(
                    poll=poll)

                # Basic metrics
                analytics.total_votes = Vote.objects.filter(
                    choice__question__poll=poll
                ).count()

                analytics.unique_voters = VoteSession.objects.filter(
                    poll=poll
                ).values('user', 'ip_address').distinct().count()

                # Calculate completion rate
                if analytics.unique_voters > 0:
                    required_questions = poll.questions.filter(
                        is_required=True).count()
                    if required_questions > 0:
                        completed_sessions = VoteSession.objects.annotate(
                            votes_count=Count('votes__id')
                        ).filter(
                            poll=poll,
                            votes_count__gte=required_questions
                        ).count()

                        analytics.completion_rate = (
                            completed_sessions / analytics.unique_voters) * 100

                # Time-series data - last 24 hours
                analytics.votes_by_hour = self._calculate_hourly_votes(poll)
                analytics.votes_by_day = self._calculate_daily_votes(poll)

                # Geographic distribution
                analytics.votes_by_country = self._calculate_geographic_distribution(
                    poll)

                # Platform distribution
                analytics.votes_by_platform = self._calculate_platform_distribution(
                    poll)

                # Revenue metrics for paid polls
                if poll.is_paid:
                    analytics.total_revenue = self._calculate_poll_revenue(
                        poll)
                    if analytics.total_votes > 0:
                        analytics.avg_revenue_per_vote = analytics.total_revenue / analytics.total_votes

                # Engagement metrics
                analytics.bookmark_count = poll.bookmarks.count()
                analytics.share_count = poll.shares.count()
                analytics.view_count = AnalyticsEvent.objects.filter(
                    poll=poll,
                    event_type='poll_view'
                ).count()

                # View to vote conversion rate
                if analytics.view_count > 0:
                    analytics.view_to_vote_rate = (
                        analytics.total_votes / analytics.view_count) * 100

                analytics.last_calculated = timezone.now()
                analytics.save()

            return True

        except Exception as e:
            self.logger.error(f"Error updating poll analytics: {e}")
            return False

    def update_user_analytics(self, user_id: int = None) -> bool:
        """Update analytics for a specific user or all users"""
        try:
            if user_id:
                users = User.objects.filter(id=user_id)
            else:
                # Only update analytics for users with recent activity
                recent_date = timezone.now() - timedelta(days=30)
                users = User.objects.filter(
                    Q(last_login__gte=recent_date) |
                    Q(polls__created_at__gte=recent_date) |
                    Q(vote_sessions__created_at__gte=recent_date)
                ).distinct()

            for user in users:
                analytics, created = UserAnalytics.objects.get_or_create(
                    user=user)

                # Poll metrics
                user_polls = user.polls.all()
                analytics.polls_created = user_polls.count()
                analytics.active_polls = user_polls.filter(
                    is_active=True).count()

                # Voting metrics
                from apps.polls.models import VoteSession, Vote
                analytics.polls_voted = VoteSession.objects.filter(
                    user=user
                ).values('poll').distinct().count()

                analytics.total_votes_made = Vote.objects.filter(
                    choice__question__poll__vote_sessions__user=user
                ).count()

                analytics.total_votes_received = Vote.objects.filter(
                    choice__question__poll__creator=user
                ).count()

                # Engagement metrics
                analytics.bookmarks_made = user.bookmarks.count()
                analytics.shares_made = user.shares.count()

                # Revenue metrics
                analytics.total_revenue = self._calculate_user_revenue(user)
                analytics.total_spent = self._calculate_user_spending(user)

                # Activity patterns
                analytics.most_active_hour = self._calculate_most_active_hour(
                    user)
                analytics.most_active_day = self._calculate_most_active_day(
                    user)

                # Primary country
                analytics.primary_country = self._calculate_primary_country(
                    user)

                analytics.last_calculated = timezone.now()
                analytics.save()

            return True

        except Exception as e:
            self.logger.error(f"Error updating user analytics: {e}")
            return False

    def create_snapshot(self, snapshot_type: str = 'daily') -> bool:
        """Create analytics snapshot for trend analysis"""
        try:
            now = timezone.now()

            # Round timestamp based on snapshot type
            if snapshot_type == 'hourly':
                timestamp = now.replace(minute=0, second=0, microsecond=0)
            elif snapshot_type == 'daily':
                timestamp = now.replace(
                    hour=0, minute=0, second=0, microsecond=0)
            elif snapshot_type == 'weekly':
                days_since_monday = now.weekday()
                timestamp = (now - timedelta(days=days_since_monday)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
            elif snapshot_type == 'monthly':
                timestamp = now.replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                timestamp = now

            # Check if snapshot already exists
            existing = AnalyticsSnapshot.objects.filter(
                snapshot_type=snapshot_type,
                timestamp=timestamp
            ).first()

            if existing:
                return True  # Already exists

            # Calculate metrics
            from apps.polls.models import Poll, Vote, VoteSession

            snapshot = AnalyticsSnapshot.objects.create(
                snapshot_type=snapshot_type,
                timestamp=timestamp,
                total_users=User.objects.count(),
                total_polls=Poll.objects.count(),
                active_polls=Poll.objects.filter(is_active=True).count(),
                total_votes=Vote.objects.count(),
                total_revenue=self._calculate_total_revenue(),
                top_countries=self._get_top_countries(),
                country_distribution=self._get_country_distribution(),
            )

            # Calculate period-specific metrics
            period_start = self._get_period_start(timestamp, snapshot_type)
            period_end = timestamp + self._get_period_duration(snapshot_type)

            snapshot.new_votes = Vote.objects.filter(
                created_at__gte=period_start,
                created_at__lt=period_end
            ).count()

            snapshot.new_revenue = self._calculate_period_revenue(
                period_start, period_end)

            # Active users in period
            snapshot.active_users = User.objects.filter(
                Q(last_login__gte=period_start) |
                Q(vote_sessions__created_at__gte=period_start)
            ).distinct().count()

            snapshot.save()
            return True

        except Exception as e:
            self.logger.error(f"Error creating analytics snapshot: {e}")
            return False

    def _update_poll_analytics_realtime(self, poll):
        """Quick update for real-time analytics"""
        if not poll:
            return

        try:
            analytics, created = PollAnalytics.objects.get_or_create(poll=poll)

            # Update basic counters only
            from apps.polls.models import Vote
            analytics.total_votes = Vote.objects.filter(
                choice__question__poll=poll
            ).count()

            analytics.view_count = AnalyticsEvent.objects.filter(
                poll=poll,
                event_type='poll_view'
            ).count()

            if analytics.view_count > 0:
                analytics.view_to_vote_rate = (
                    analytics.total_votes / analytics.view_count) * 100

            analytics.save(
                update_fields=['total_votes', 'view_count', 'view_to_vote_rate'])

        except Exception as e:
            self.logger.error(f"Error in real-time analytics update: {e}")

    def _calculate_hourly_votes(self, poll) -> Dict[str, int]:
        """Calculate votes by hour for the last 24 hours"""
        from apps.polls.models import Vote

        now = timezone.now()
        yesterday = now - timedelta(hours=24)

        hourly_votes = {}
        for hour in range(24):
            hour_start = yesterday + timedelta(hours=hour)
            hour_end = yesterday + timedelta(hours=hour + 1)

            count = Vote.objects.filter(
                choice__question__poll=poll,
                created_at__gte=hour_start,
                created_at__lt=hour_end
            ).count()

            hourly_votes[str(hour)] = count

        return hourly_votes

    def _calculate_daily_votes(self, poll) -> Dict[str, int]:
        """Calculate votes by day for the last 30 days"""
        from apps.polls.models import Vote

        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)

        daily_votes = {}
        for day in range(30):
            day_start = thirty_days_ago + timedelta(days=day)
            day_end = day_start + timedelta(days=1)

            count = Vote.objects.filter(
                choice__question__poll=poll,
                created_at__gte=day_start,
                created_at__lt=day_end
            ).count()

            date_str = day_start.strftime('%Y-%m-%d')
            daily_votes[date_str] = count

        return daily_votes

    def _calculate_geographic_distribution(self, poll) -> Dict[str, int]:
        """Calculate votes by country"""
        events = AnalyticsEvent.objects.filter(
            poll=poll,
            event_type='poll_vote'
        ).values('country_code').annotate(
            count=Count('id')
        ).order_by('-count')

        return {item['country_code']: item['count'] for item in events}

    def _calculate_platform_distribution(self, poll) -> Dict[str, int]:
        """Calculate votes by device type"""
        events = AnalyticsEvent.objects.filter(
            poll=poll,
            event_type='poll_vote'
        ).values('device_type').annotate(
            count=Count('id')
        ).order_by('-count')

        return {item['device_type']: item['count'] for item in events}

    def _calculate_poll_revenue(self, poll) -> float:
        """Calculate total revenue for a poll"""
        try:
            from apps.payments.models import Transaction
            return Transaction.objects.filter(
                poll=poll,
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or 0
        except:
            return 0

    def _calculate_user_revenue(self, user) -> float:
        """Calculate total revenue earned by user"""
        try:
            from apps.payments.models import Transaction
            return Transaction.objects.filter(
                poll__creator=user,
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or 0
        except:
            return 0

    def _calculate_user_spending(self, user) -> float:
        """Calculate total amount spent by user"""
        try:
            from apps.payments.models import Transaction
            return Transaction.objects.filter(
                user=user,
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or 0
        except:
            return 0

    def _calculate_most_active_hour(self, user) -> int:
        """Calculate user's most active hour"""
        from django.db.models import Count

        hours = AnalyticsEvent.objects.filter(
            user=user
        ).extra(
            select={'hour': 'EXTRACT(hour FROM created_at)'}
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('-count')

        return int(hours.first()['hour']) if hours else 12

    def _calculate_most_active_day(self, user) -> int:
        """Calculate user's most active day of week"""
        from django.db.models import Count

        days = AnalyticsEvent.objects.filter(
            user=user
        ).extra(
            select={'dow': 'EXTRACT(dow FROM created_at)'}
        ).values('dow').annotate(
            count=Count('id')
        ).order_by('-count')

        return int(days.first()['dow']) if days else 1

    def _calculate_primary_country(self, user) -> str:
        """Calculate user's primary country"""
        country = AnalyticsEvent.objects.filter(
            user=user
        ).values('country_code').annotate(
            count=Count('id')
        ).order_by('-count').first()

        return country['country_code'] if country else ''

    def _calculate_total_revenue(self) -> float:
        """Calculate system-wide revenue"""
        try:
            from apps.payments.models import Transaction
            return Transaction.objects.filter(
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or 0
        except:
            return 0

    def _get_top_countries(self, limit: int = 10) -> list:
        """Get top countries by activity"""
        countries = AnalyticsEvent.objects.values('country_code').annotate(
            count=Count('id')
        ).order_by('-count')[:limit]

        return [item['country_code'] for item in countries]

    def _get_country_distribution(self) -> Dict[str, int]:
        """Get complete country distribution"""
        countries = AnalyticsEvent.objects.values('country_code').annotate(
            count=Count('id')
        ).order_by('-count')

        return {item['country_code']: item['count'] for item in countries}

    def _get_period_start(self, timestamp, snapshot_type):
        """Get the start of the period for snapshot calculations"""
        if snapshot_type == 'hourly':
            return timestamp - timedelta(hours=1)
        elif snapshot_type == 'daily':
            return timestamp - timedelta(days=1)
        elif snapshot_type == 'weekly':
            return timestamp - timedelta(weeks=1)
        elif snapshot_type == 'monthly':
            return timestamp - timedelta(days=30)
        return timestamp

    def _get_period_duration(self, snapshot_type):
        """Get the duration of the snapshot period"""
        if snapshot_type == 'hourly':
            return timedelta(hours=1)
        elif snapshot_type == 'daily':
            return timedelta(days=1)
        elif snapshot_type == 'weekly':
            return timedelta(weeks=1)
        elif snapshot_type == 'monthly':
            return timedelta(days=30)
        return timedelta(days=1)

    def _calculate_period_revenue(self, start, end) -> float:
        """Calculate revenue for a specific period"""
        try:
            from apps.payments.models import Transaction
            return Transaction.objects.filter(
                status='completed',
                created_at__gte=start,
                created_at__lt=end
            ).aggregate(total=Sum('amount'))['total'] or 0
        except:
            return 0
