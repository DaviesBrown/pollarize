import csv
from datetime import timedelta
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Count, Q
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as filters

from .models import ComplianceLog, GeolocationCache, ComplianceRule
from .serializers import (
    ComplianceLogSerializer, GeolocationCacheSerializer,
    ComplianceRuleSerializer, ComplianceStatsSerializer
)
from .services import ComplianceService


class IsAdminOrStaff(permissions.BasePermission):
    """Custom permission for admin/staff only access"""

    def has_permission(self, request, view):
        return request.user and (request.user.is_staff or request.user.is_superuser)


class ComplianceLogFilter(filters.FilterSet):
    """Filter set for compliance logs"""

    action = filters.ChoiceFilter(choices=ComplianceLog.ACTION_CHOICES)
    status = filters.ChoiceFilter(choices=ComplianceLog.STATUS_CHOICES)
    country_code = filters.CharFilter(
        field_name='country_code', lookup_expr='iexact')
    date_from = filters.DateTimeFilter(
        field_name='created_at', lookup_expr='gte')
    date_to = filters.DateTimeFilter(
        field_name='created_at', lookup_expr='lte')
    poll_id = filters.NumberFilter(field_name='poll__id')
    user_id = filters.NumberFilter(field_name='user__id')

    class Meta:
        model = ComplianceLog
        fields = ['action', 'status', 'country_code', 'poll_id', 'user_id']


class ComplianceLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for compliance logs - read-only for auditing"""

    queryset = ComplianceLog.objects.all().select_related('poll', 'user')
    serializer_class = ComplianceLogSerializer
    permission_classes = [IsAdminOrStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ComplianceLogFilter
    ordering_fields = ['created_at', 'action', 'status', 'country_code']
    ordering = ['-created_at']

    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        """Export compliance logs as CSV"""

        # Apply filters
        queryset = self.filter_queryset(self.get_queryset())

        # Limit to prevent huge exports
        if queryset.count() > 10000:
            return Response({
                'error': 'Too many records. Please use filters to limit the results.'
            }, status=status.HTTP_400_BAD_REQUEST)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="compliance_logs.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Date', 'Action', 'Status', 'IP Address', 'Country Code',
            'Poll Title', 'Username', 'Reason', 'Request Path'
        ])

        for log in queryset:
            writer.writerow([
                log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                log.get_action_display(),
                log.get_status_display(),
                log.ip_address,
                log.country_code,
                log.poll.title if log.poll else '',
                log.user.username if log.user else '',
                log.blocked_reason,
                log.request_path
            ])

        return response

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get compliance statistics"""

        # Date range filter
        days = int(request.query_params.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)

        queryset = self.get_queryset().filter(created_at__gte=start_date)

        # Basic stats
        total_logs = queryset.count()
        blocked_requests = queryset.filter(status='blocked').count()
        allowed_requests = queryset.filter(status='allowed').count()
        flagged_requests = queryset.filter(status='flagged').count()

        # Top blocked countries
        top_blocked_countries = list(
            queryset.filter(status='blocked')
            .values('country_code')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        # Top blocked actions
        top_blocked_actions = list(
            queryset.filter(status='blocked')
            .values('action')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        # Block rate by hour
        block_rate_by_hour = {}
        for hour in range(24):
            hour_logs = queryset.filter(created_at__hour=hour)
            total_hour = hour_logs.count()
            blocked_hour = hour_logs.filter(status='blocked').count()

            if total_hour > 0:
                block_rate_by_hour[str(hour)] = round(
                    (blocked_hour / total_hour) * 100, 2)
            else:
                block_rate_by_hour[str(hour)] = 0

        # Geographic distribution
        geographic_distribution = dict(
            queryset.values('country_code')
            .annotate(count=Count('id'))
            .values_list('country_code', 'count')
        )

        stats_data = {
            'total_logs': total_logs,
            'blocked_requests': blocked_requests,
            'allowed_requests': allowed_requests,
            'flagged_requests': flagged_requests,
            'top_blocked_countries': top_blocked_countries,
            'top_blocked_actions': top_blocked_actions,
            'block_rate_by_hour': block_rate_by_hour,
            'geographic_distribution': geographic_distribution
        }

        serializer = ComplianceStatsSerializer(stats_data)
        return Response(serializer.data)


class GeolocationCacheViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for geolocation cache - read-only"""

    queryset = GeolocationCache.objects.all()
    serializer_class = GeolocationCacheSerializer
    permission_classes = [IsAdminOrStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['country_code', 'is_valid', 'provider']
    ordering_fields = ['created_at', 'country_code', 'expires_at']
    ordering = ['-created_at']

    @action(detail=False, methods=['post'])
    def clear_expired(self, request):
        """Clear expired cache entries"""

        deleted_count = GeolocationCache.objects.filter(
            expires_at__lt=timezone.now()
        ).delete()[0]

        return Response({
            'message': f'Cleared {deleted_count} expired cache entries'
        })


class ComplianceRuleViewSet(viewsets.ModelViewSet):
    """ViewSet for compliance rules"""

    queryset = ComplianceRule.objects.all()
    serializer_class = ComplianceRuleSerializer
    permission_classes = [IsAdminOrStaff]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['rule_type', 'is_active']
    ordering_fields = ['created_at', 'name', 'rule_type']
    ordering = ['-created_at']

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Toggle rule active status"""

        rule = self.get_object()
        rule.is_active = not rule.is_active
        rule.save()

        return Response({
            'message': f'Rule {rule.name} is now {"active" if rule.is_active else "inactive"}',
            'is_active': rule.is_active
        })


class ComplianceCheckView(APIView):
    """API endpoint for manual compliance checks"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Perform a compliance check"""

        poll_id = request.data.get('poll_id')
        if not poll_id:
            return Response({
                'error': 'poll_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            from apps.polls.models import Poll
            poll = Poll.objects.get(id=poll_id)
        except Poll.DoesNotExist:
            return Response({
                'error': 'Poll not found'
            }, status=status.HTTP_404_NOT_FOUND)

        compliance_service = ComplianceService()

        # Get client IP
        ip_address = compliance_service.get_client_ip(request)

        # Perform checks
        geo_result = compliance_service.check_geographic_restrictions(
            poll=poll,
            ip_address=ip_address,
            user=request.user
        )

        voting_result = compliance_service.check_voting_limits(
            poll=poll,
            user=request.user,
            ip_address=ip_address
        )

        return Response({
            'poll_id': poll_id,
            'poll_title': poll.title,
            'geographic_check': geo_result,
            'voting_check': voting_result,
            'overall_allowed': not (geo_result['blocked'] or voting_result['blocked'])
        })
