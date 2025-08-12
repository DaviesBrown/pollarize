import csv
import json
from datetime import timedelta
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q
from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as filters

from .models import PollAnalytics, UserAnalytics, AnalyticsEvent, AnalyticsSnapshot
from .serializers import (
    PollAnalyticsSerializer, UserAnalyticsSerializer, AnalyticsEventSerializer,
    AnalyticsSnapshotSerializer, PollAnalyticsSummarySerializer,
    UserAnalyticsSummarySerializer, AnalyticsDashboardSerializer,
    ExportAnalyticsSerializer
)
from .services import AnalyticsService

User = get_user_model()


class IsOwnerOrStaff(permissions.BasePermission):
    """Custom permission for owners or staff"""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Check ownership based on model type
        if hasattr(obj, 'poll') and hasattr(obj.poll, 'creator'):
            return obj.poll.creator == request.user
        elif hasattr(obj, 'user'):
            return obj.user == request.user

        return False


class PollAnalyticsFilter(filters.FilterSet):
    """Filter set for poll analytics"""

    poll_creator = filters.NumberFilter(field_name='poll__creator__id')
    poll_category = filters.NumberFilter(field_name='poll__category__id')
    is_paid = filters.BooleanFilter(field_name='poll__is_paid')
    min_votes = filters.NumberFilter(
        field_name='total_votes', lookup_expr='gte')
    max_votes = filters.NumberFilter(
        field_name='total_votes', lookup_expr='lte')
    min_completion_rate = filters.NumberFilter(
        field_name='completion_rate', lookup_expr='gte')
    date_from = filters.DateTimeFilter(
        field_name='last_updated', lookup_expr='gte')
    date_to = filters.DateTimeFilter(
        field_name='last_updated', lookup_expr='lte')

    class Meta:
        model = PollAnalytics
        fields = ['poll_creator', 'poll_category', 'is_paid']


class PollAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for poll analytics"""

    serializer_class = PollAnalyticsSerializer
    permission_classes = [IsOwnerOrStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PollAnalyticsFilter
    ordering_fields = ['total_votes', 'unique_voters',
                       'completion_rate', 'total_revenue', 'last_updated']
    ordering = ['-last_updated']

    def get_queryset(self):
        """Filter queryset based on user permissions"""
        if self.request.user.is_staff or self.request.user.is_superuser:
            return PollAnalytics.objects.all().select_related('poll__creator')
        else:
            return PollAnalytics.objects.filter(
                poll__creator=self.request.user
            ).select_related('poll__creator')

    @action(detail=True, methods=['post'])
    def refresh(self, request, pk=None):
        """Manually refresh analytics for a specific poll"""

        analytics = self.get_object()
        analytics_service = AnalyticsService()

        success = analytics_service.update_poll_analytics(analytics.poll.id)

        if success:
            # Return updated data
            analytics.refresh_from_db()
            serializer = self.get_serializer(analytics)
            return Response({
                'message': 'Analytics refreshed successfully',
                'data': serializer.data
            })
        else:
            return Response({
                'error': 'Failed to refresh analytics'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get summarized analytics for multiple polls"""

        queryset = self.filter_queryset(self.get_queryset())

        # Calculate summary metrics
        summary_data = []
        for analytics in queryset:
            # Find peak voting hour
            votes_by_hour = analytics.votes_by_hour or {}
            peak_hour = max(votes_by_hour.keys(
            ), key=lambda k: votes_by_hour[k]) if votes_by_hour else 12

            # Find top country
            votes_by_country = analytics.votes_by_country or {}
            top_country = max(votes_by_country.keys(
            ), key=lambda k: votes_by_country[k]) if votes_by_country else 'XX'

            summary_data.append({
                'poll_id': analytics.poll.id,
                'poll_title': analytics.poll.title,
                'total_votes': analytics.total_votes,
                'unique_voters': analytics.unique_voters,
                'completion_rate': analytics.completion_rate,
                'view_count': analytics.view_count,
                'view_to_vote_rate': analytics.view_to_vote_rate,
                'revenue': analytics.total_revenue,
                'top_country': top_country,
                'peak_voting_hour': int(peak_hour) if peak_hour.isdigit() else 12,
            })

        serializer = PollAnalyticsSummarySerializer(summary_data, many=True)
        return Response(serializer.data)


class UserAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for user analytics"""

    serializer_class = UserAnalyticsSerializer
    permission_classes = [IsOwnerOrStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['primary_country', 'most_active_hour']
    ordering_fields = ['polls_created', 'total_votes_made',
                       'total_revenue', 'last_updated']
    ordering = ['-last_updated']

    def get_queryset(self):
        """Filter queryset based on user permissions"""
        if self.request.user.is_staff or self.request.user.is_superuser:
            return UserAnalytics.objects.all().select_related('user')
        else:
            return UserAnalytics.objects.filter(
                user=self.request.user
            ).select_related('user')

    @action(detail=True, methods=['post'])
    def refresh(self, request, pk=None):
        """Manually refresh analytics for a specific user"""

        analytics = self.get_object()
        analytics_service = AnalyticsService()

        success = analytics_service.update_user_analytics(analytics.user.id)

        if success:
            analytics.refresh_from_db()
            serializer = self.get_serializer(analytics)
            return Response({
                'message': 'User analytics refreshed successfully',
                'data': serializer.data
            })
        else:
            return Response({
                'error': 'Failed to refresh user analytics'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def leaderboard(self, request):
        """Get user leaderboard based on various metrics"""

        metric = request.query_params.get('metric', 'total_revenue')
        limit = min(int(request.query_params.get('limit', 10)), 100)

        valid_metrics = [
            'polls_created', 'total_votes_made', 'total_votes_received',
            'total_revenue', 'polls_voted'
        ]

        if metric not in valid_metrics:
            return Response({
                'error': f'Invalid metric. Choose from: {", ".join(valid_metrics)}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Only show public leaderboard unless user is staff
        if not (request.user.is_staff or request.user.is_superuser):
            # For non-staff, show anonymized data
            queryset = UserAnalytics.objects.all()
        else:
            queryset = self.get_queryset()

        leaderboard = queryset.order_by(f'-{metric}')[:limit]

        leaderboard_data = []
        for i, analytics in enumerate(leaderboard, 1):
            # Calculate engagement score
            engagement_score = (
                analytics.polls_created * 10 +
                analytics.total_votes_made * 2 +
                analytics.bookmarks_made * 1 +
                analytics.shares_made * 5
            ) / 100.0

            data = {
                'rank': i,
                'user_id': analytics.user.id if request.user.is_staff else None,
                'username': analytics.user.username if request.user.is_staff else f'User_{i}',
                'polls_created': analytics.polls_created,
                'total_votes_made': analytics.total_votes_made,
                'total_votes_received': analytics.total_votes_received,
                'total_revenue': analytics.total_revenue,
                'engagement_score': round(engagement_score, 2),
                'primary_country': analytics.primary_country,
            }
            leaderboard_data.append(data)

        return Response({
            'metric': metric,
            'leaderboard': leaderboard_data
        })


class AnalyticsEventViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for analytics events"""

    serializer_class = AnalyticsEventSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['event_type', 'device_type', 'country_code']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        # Limit to recent events to prevent performance issues
        recent_date = timezone.now() - timedelta(days=30)
        return AnalyticsEvent.objects.filter(
            created_at__gte=recent_date
        ).select_related('user', 'poll')


class AnalyticsSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for analytics snapshots"""

    serializer_class = AnalyticsSnapshotSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['snapshot_type']
    ordering_fields = ['timestamp']
    ordering = ['-timestamp']

    def get_queryset(self):
        return AnalyticsSnapshot.objects.all()


class AnalyticsDashboardView(APIView):
    """Analytics dashboard with overview metrics and charts"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get dashboard data"""

        # Date range for comparisons
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        comparison_start = start_date - timedelta(days=days)

        # Check if user can see all data or just their own
        is_admin = request.user.is_staff or request.user.is_superuser

        from apps.polls.models import Poll, Vote

        if is_admin:
            # System-wide metrics
            current_polls = Poll.objects.filter(created_at__gte=start_date)
            previous_polls = Poll.objects.filter(
                created_at__gte=comparison_start,
                created_at__lt=start_date
            )

            current_votes = Vote.objects.filter(created_at__gte=start_date)
            previous_votes = Vote.objects.filter(
                created_at__gte=comparison_start,
                created_at__lt=start_date
            )

            current_users = User.objects.filter(date_joined__gte=start_date)
            previous_users = User.objects.filter(
                date_joined__gte=comparison_start,
                date_joined__lt=start_date
            )
        else:
            # User-specific metrics
            current_polls = Poll.objects.filter(
                creator=request.user,
                created_at__gte=start_date
            )
            previous_polls = Poll.objects.filter(
                creator=request.user,
                created_at__gte=comparison_start,
                created_at__lt=start_date
            )

            current_votes = Vote.objects.filter(
                choice__question__poll__creator=request.user,
                created_at__gte=start_date
            )
            previous_votes = Vote.objects.filter(
                choice__question__poll__creator=request.user,
                created_at__gte=comparison_start,
                created_at__lt=start_date
            )

            current_users = User.objects.filter(id=request.user.id)
            previous_users = User.objects.none()

        # Calculate metrics
        total_polls = current_polls.count()
        total_votes = current_votes.count()
        total_users = current_users.count()

        # Calculate changes
        prev_polls = previous_polls.count()
        prev_votes = previous_votes.count()
        prev_users = previous_users.count()

        polls_change = ((total_polls - prev_polls) / max(prev_polls, 1)) * 100
        votes_change = ((total_votes - prev_votes) / max(prev_votes, 1)) * 100
        users_change = ((total_users - prev_users) / max(prev_users, 1)) * 100

        # Revenue calculation
        try:
            from apps.payments.models import Transaction
            if is_admin:
                current_revenue = Transaction.objects.filter(
                    created_at__gte=start_date,
                    status='completed'
                ).aggregate(total=Sum('amount'))['total'] or 0

                previous_revenue = Transaction.objects.filter(
                    created_at__gte=comparison_start,
                    created_at__lt=start_date,
                    status='completed'
                ).aggregate(total=Sum('amount'))['total'] or 0
            else:
                current_revenue = Transaction.objects.filter(
                    poll__creator=request.user,
                    created_at__gte=start_date,
                    status='completed'
                ).aggregate(total=Sum('amount'))['total'] or 0

                previous_revenue = Transaction.objects.filter(
                    poll__creator=request.user,
                    created_at__gte=comparison_start,
                    created_at__lt=start_date,
                    status='completed'
                ).aggregate(total=Sum('amount'))['total'] or 0

            revenue_change = (
                (current_revenue - previous_revenue) / max(previous_revenue, 1)) * 100
        except:
            current_revenue = 0
            revenue_change = 0

        # Generate trend data
        votes_trend = self._generate_trend_data(
            current_votes, days, 'created_at')
        user_growth = self._generate_trend_data(
            current_users, days, 'date_joined')

        # Geographic distribution
        geo_events = AnalyticsEvent.objects.filter(
            created_at__gte=start_date
        ).values('country_code').annotate(
            count=Count('id')
        ).order_by('-count')[:10]

        geographic_distribution = {
            item['country_code']: item['count'] for item in geo_events
        }

        # Top polls (for admins) or user's top polls
        if is_admin:
            top_polls = list(
                PollAnalytics.objects.filter(
                    last_updated__gte=start_date
                ).order_by('-total_votes')[:5].values(
                    'poll__title', 'total_votes', 'unique_voters'
                )
            )
        else:
            top_polls = list(
                PollAnalytics.objects.filter(
                    poll__creator=request.user,
                    last_updated__gte=start_date
                ).order_by('-total_votes')[:5].values(
                    'poll__title', 'total_votes', 'unique_voters'
                )
            )

        dashboard_data = {
            'total_polls': total_polls,
            'total_votes': total_votes,
            'total_users': total_users if is_admin else 1,
            'total_revenue': float(current_revenue),
            'polls_change': round(polls_change, 2),
            'votes_change': round(votes_change, 2),
            'users_change': round(users_change, 2) if is_admin else 0,
            'revenue_change': round(revenue_change, 2),
            'votes_trend': votes_trend,
            'revenue_trend': {},  # Would implement if needed
            'user_growth': user_growth,
            'geographic_distribution': geographic_distribution,
            'top_polls': top_polls,
            'top_creators': [],  # Would implement for admin view
            'top_countries': list(geographic_distribution.keys())[:5],
        }

        serializer = AnalyticsDashboardSerializer(dashboard_data)
        return Response(serializer.data)

    def _generate_trend_data(self, queryset, days, date_field):
        """Generate trend data for charts"""
        from django.db.models import Count
        from django.db.models.functions import TruncDate

        trend_data = queryset.annotate(
            date=TruncDate(date_field)
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')

        # Convert to dict with date strings as keys
        result = {}
        for item in trend_data:
            if item['date']:
                result[item['date'].strftime('%Y-%m-%d')] = item['count']

        return result


class ExportAnalyticsView(APIView):
    """Export analytics data in various formats"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Export analytics data"""

        serializer = ExportAnalyticsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        export_type = data['export_type']
        export_format = data['export_format']

        # Check permissions
        is_admin = request.user.is_staff or request.user.is_superuser

        if export_type in ['user', 'events'] and not is_admin:
            return Response({
                'error': 'Insufficient permissions for this export type'
            }, status=status.HTTP_403_FORBIDDEN)

        try:
            if export_type == 'poll':
                return self._export_poll_analytics(request, data, export_format)
            elif export_type == 'user':
                return self._export_user_analytics(request, data, export_format)
            elif export_type == 'events':
                return self._export_analytics_events(request, data, export_format)
            elif export_type == 'compliance':
                return self._export_compliance_logs(request, data, export_format)

        except Exception as e:
            return Response({
                'error': f'Export failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _export_poll_analytics(self, request, data, export_format):
        """Export poll analytics data"""

        queryset = PollAnalytics.objects.all()

        # Apply filters
        if not (request.user.is_staff or request.user.is_superuser):
            queryset = queryset.filter(poll__creator=request.user)

        if data.get('poll_ids'):
            queryset = queryset.filter(poll_id__in=data['poll_ids'])

        if data.get('date_from'):
            queryset = queryset.filter(last_updated__gte=data['date_from'])

        if data.get('date_to'):
            queryset = queryset.filter(last_updated__lte=data['date_to'])

        if export_format == 'csv':
            return self._export_as_csv(queryset, 'poll_analytics.csv', [
                'poll__title', 'poll__creator__username', 'total_votes',
                'unique_voters', 'completion_rate', 'total_revenue',
                'last_updated'
            ])
        elif export_format == 'json':
            serializer = PollAnalyticsSerializer(queryset, many=True)
            return self._export_as_json(serializer.data, 'poll_analytics.json')

    def _export_user_analytics(self, request, data, export_format):
        """Export user analytics data"""
        # Implementation similar to poll analytics
        pass

    def _export_analytics_events(self, request, data, export_format):
        """Export analytics events data"""
        # Implementation similar to poll analytics
        pass

    def _export_compliance_logs(self, request, data, export_format):
        """Export compliance logs data"""
        # Implementation similar to poll analytics
        pass

    def _export_as_csv(self, queryset, filename, fields):
        """Export queryset as CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)

        # Write headers
        headers = [field.replace('__', '_').replace(
            '_', ' ').title() for field in fields]
        writer.writerow(headers)

        # Write data
        for obj in queryset:
            row = []
            for field in fields:
                value = obj
                for attr in field.split('__'):
                    value = getattr(value, attr, '')
                    if value is None:
                        value = ''
                row.append(str(value))
            writer.writerow(row)

        return response

    def _export_as_json(self, data, filename):
        """Export data as JSON"""
        response = HttpResponse(
            json.dumps(data, indent=2, default=str),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
