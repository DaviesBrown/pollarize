# Phase 4: Compliance & Analytics

## Architecture Overview

Phase 4 implements regulatory compliance features and comprehensive analytics tracking. We'll build a geolocation-based restriction system, develop compliance logging, and create time-series analytics for polls and user engagement metrics.

## Technical Design Decisions

1. **Compliance Framework**:
   - Middleware-based geoblocking with IP geolocation
   - Free IP geolocation service with Redis caching
   - Compliance logging for audit and reporting purposes
   - Age verification through self-declaration

2. **Analytics Architecture**:
   - Time-series data storage for performance metrics
   - Aggregated data model with background processing
   - Geographic distribution tracking
   - Denormalized metrics for performance optimization

3. **Data Processing Strategy**:
   - Scheduled aggregation tasks for analytics
   - Real-time compliance enforcement
   - Export capabilities for CSV/JSON formats

## Implementation Tasks

### 1. Compliance Models & Middleware (3 days)

```python
# apps/compliance/models.py
class ComplianceLog(models.Model):
    ACTION_CHOICES = (
        ('geo_block', 'Geographic Blocking'),
        ('age_verify', 'Age Verification'),
        ('fraud_detect', 'Fraud Detection'),
        ('vote_limit', 'Vote Limit'),
    )
    
    poll = models.ForeignKey('polls.Poll', on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    country_code = models.CharField(max_length=2, blank=True)
    blocked_reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['poll', 'action']),
            models.Index(fields=['country_code']),
        ]

# apps/compliance/middleware.py
class GeoRestrictionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only check poll-related endpoints
        if '/api/v1/polls/' in request.path and '/vote/' in request.path:
            # Extract poll ID
            parts = request.path.strip('/').split('/')
            try:
                poll_index = parts.index('polls')
                if len(parts) > poll_index + 1:
                    poll_id = parts[poll_index + 1]
                    
                    # Check poll restrictions
                    from apps.polls.models import Poll
                    poll = Poll.objects.get(id=poll_id)
                    
                    if poll.region_lock:
                        # Get user's country
                        ip = self.get_client_ip(request)
                        country_code = self.get_country_code(ip)
                        
                        # Check against allowed countries
                        if country_code not in poll.allowed_countries.split(','):
                            # Log and block
                            from apps.compliance.models import ComplianceLog
                            ComplianceLog.objects.create(
                                poll=poll,
                                ip_address=ip,
                                action='geo_block',
                                country_code=country_code,
                                blocked_reason=f"Country {country_code} not allowed"
                            )
                            
                            return JsonResponse({
                                'detail': 'This poll is not available in your region'
                            }, status=403)
            except Exception:
                pass
                
        return self.get_response(request)
    
    def get_country_code(self, ip):
        # Check cache first
        from django.core.cache import cache
        import requests
        
        cache_key = f'geo_ip_{ip}'
        country_code = cache.get(cache_key)
        
        if not country_code:
            # Use ipapi.co free service
            try:
                response = requests.get(f'https://ipapi.co/{ip}/country/', timeout=3)
                if response.status_code == 200:
                    country_code = response.text.strip()
                    # Cache for 24 hours
                    cache.set(cache_key, country_code, 60 * 60 * 24)
                else:
                    country_code = 'XX'  # Unknown
            except Exception:
                country_code = 'XX'  # Unknown
                
        return country_code
```

### 2. Poll Analytics Models (2 days)

```python
# apps/analytics/models.py
class PollAnalytics(models.Model):
    poll = models.OneToOneField('polls.Poll', on_delete=models.CASCADE, related_name='analytics')
    total_votes = models.IntegerField(default=0)
    unique_voters = models.IntegerField(default=0)
    completion_rate = models.FloatField(default=0)  # % of users who complete all questions
    avg_time_spent = models.FloatField(default=0)  # seconds
    
    # Serialized time-series data
    votes_by_hour = models.JSONField(default=dict)
    votes_by_day = models.JSONField(default=dict)
    votes_by_country = models.JSONField(default=dict)
    
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Poll analytics"
        indexes = [
            models.Index(fields=['poll']),
            models.Index(fields=['last_updated']),
        ]

class UserAnalytics(models.Model):
    user = models.OneToOneField('core.User', on_delete=models.CASCADE, related_name='analytics')
    polls_created = models.IntegerField(default=0)
    polls_voted = models.IntegerField(default=0)
    total_votes_made = models.IntegerField(default=0)
    total_votes_received = models.IntegerField(default=0)
    
    # Optional paid metrics
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "User analytics"
```

### 3. Analytics Aggregation Tasks (2 days)

```python
# apps/analytics/tasks.py
@shared_task
def update_poll_analytics(poll_id=None):
    """Update analytics for poll or all active polls"""
    if poll_id:
        polls = Poll.objects.filter(id=poll_id)
    else:
        # Only process active polls
        polls = Poll.objects.filter(is_active=True)
    
    for poll in polls:
        # Get or create analytics object
        analytics, _ = PollAnalytics.objects.get_or_create(poll=poll)
        
        # Calculate basic metrics
        total_votes = Vote.objects.filter(choice__question__poll=poll).count()
        unique_voters = VoteSession.objects.filter(poll=poll).values('user').distinct().count()
        
        # Calculate completion rate
        required_questions = poll.questions.filter(is_required=True).count()
        if required_questions > 0 and unique_voters > 0:
            completed_sessions = VoteSession.objects.annotate(
                votes_count=Count('votes')
            ).filter(
                poll=poll,
                votes_count__gte=required_questions
            ).count()
            
            completion_rate = (completed_sessions / unique_voters) * 100
        else:
            completion_rate = 0
            
        # Calculate time-series data - last 24 hours
        now = timezone.now()
        yesterday = now - timezone.timedelta(hours=24)
        
        hourly_votes = {}
        for hour in range(24):
            hour_start = yesterday + timezone.timedelta(hours=hour)
            hour_end = yesterday + timezone.timedelta(hours=hour+1)
            
            count = Vote.objects.filter(
                choice__question__poll=poll,
                created_at__gte=hour_start,
                created_at__lt=hour_end
            ).count()
            
            hourly_votes[hour] = count
        
        # Get geographic distribution
        geo_data = VoteSession.objects.filter(poll=poll).values(
            'country_code'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
        
        geo_counts = {item['country_code']: item['count'] for item in geo_data}
        
        # Update the analytics object
        analytics.total_votes = total_votes
        analytics.unique_voters = unique_voters
        analytics.completion_rate = completion_rate
        analytics.votes_by_hour = hourly_votes
        analytics.votes_by_country = geo_counts
        analytics.save()
```

### 4. Analytics API Endpoints (2 days)

```python
# apps/analytics/serializers.py
class PollAnalyticsSerializer(serializers.ModelSerializer):
    poll_title = serializers.CharField(source='poll.title', read_only=True)
    
    class Meta:
        model = PollAnalytics
        fields = ['id', 'poll', 'poll_title', 'total_votes', 'unique_voters', 
                 'completion_rate', 'votes_by_hour', 'votes_by_country', 
                 'last_updated']
        read_only_fields = fields

# apps/analytics/views.py
class PollAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PollAnalyticsSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrStaff]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return PollAnalytics.objects.all()
        return PollAnalytics.objects.filter(poll__creator=self.request.user)

class ExportAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrStaff]
    
    def get(self, request):
        poll_id = request.query_params.get('poll_id')
        if not poll_id:
            return Response({'error': 'poll_id parameter is required'}, status=400)
        
        try:
            poll = Poll.objects.get(id=poll_id)
            if not request.user.is_staff and poll.creator != request.user:
                return Response({'error': 'Not authorized'}, status=403)
                
            # Generate CSV
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename=poll_{poll_id}_analytics.csv'
            
            writer = csv.writer(response)
            writer.writerow(['Poll', 'Question', 'Choice', 'Votes', 'Percentage'])
            
            # Add data rows
            for question in poll.questions.all():
                total_votes = question.choices.aggregate(
                    total=Sum('vote_count'))['total'] or 0
                
                writer.writerow([poll.title, question.text, '', '', ''])
                
                for choice in question.choices.all():
                    percentage = 0
                    if total_votes > 0:
                        percentage = (choice.vote_count / total_votes) * 100
                    
                    writer.writerow(['', '', choice.text, choice.vote_count, f'{percentage:.2f}%'])
                
            return response
        except Poll.DoesNotExist:
            return Response({'error': 'Poll not found'}, status=404)
```

### 5. Compliance API Endpoints (1 day)

```python
# apps/compliance/serializers.py
class ComplianceLogSerializer(serializers.ModelSerializer):
    poll_title = serializers.CharField(source='poll.title', read_only=True)
    
    class Meta:
        model = ComplianceLog
        fields = ['id', 'poll', 'poll_title', 'action', 'ip_address', 
                 'country_code', 'blocked_reason', 'created_at']
        read_only_fields = fields

# apps/compliance/views.py
class ComplianceLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ComplianceLogSerializer
    permission_classes = [permissions.IsAdminUser]
    filterset_fields = ['action', 'country_code', 'poll']
    ordering_fields = ['created_at']
    
    def get_queryset(self):
        return ComplianceLog.objects.all().order_by('-created_at')

# api/v1/urls.py
router.register(r'compliance', ComplianceLogViewSet)
router.register(r'analytics', PollAnalyticsViewSet)

urlpatterns += [
    path('analytics/export/', ExportAnalyticsView.as_view(), name='export-analytics'),
]
```

## Performance Considerations

1. **Caching Strategies**:
   - Cache geolocation lookups for 24 hours
   - Cache poll analytics for 10 minutes
   - Use batch processing for analytics calculations

2. **Query Optimization**:
   - Proper indexing for compliance and analytics tables
   - Use database aggregations instead of Python loops
   - Denormalize analytics data to avoid joins

3. **Background Processing**:
   - Schedule analytics updates during off-peak hours
   - Process analytics in chunks to avoid memory issues
   - Implement timeout handling for geolocation API calls

## Testing Requirements

1. **Unit Tests**:
   - Test geolocation middleware with mock IPs
   - Validate analytics calculations with test datasets
   - Verify CSV export format correctness

2. **Integration Tests**:
   - Test compliance blocking with simulated requests
   - Verify analytics update workflow end-to-end
   - Test export functionality with large polls

3. **Performance Tests**:
   - Measure analytics aggregation speed with large datasets
   - Test geolocation middleware overhead
   - Verify caching effectiveness

## Definition of Done

- Geolocation middleware correctly blocks by country
- Analytics accurately track poll performance metrics
- Time-series data properly aggregated and displayed
- Compliance logs capture all restriction events
- CSV exports correctly formatted and downloadable
- All endpoints properly secured with permissions

---
