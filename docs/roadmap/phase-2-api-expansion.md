# Phase 2: Enhanced API Features & Permissions

## Architecture Overview

Phase 2 extends our API with advanced features, robust permissions, filtering capabilities, and relational endpoints. We introduce bookmark functionality, implement complex permission hierarchies, and establish advanced query patterns for scalability.

## Technical Design Decisions

1. **Advanced Permission System**:
   - Fine-grained permissions with policy objects
   - Role-based access control with custom permissions
   - Object-level permissions for creators vs. viewers

2. **Query Optimization**:
   - Implement database indexes for frequent query patterns
   - Use custom managers for common query operations
   - Leverage Django ORM's `select_related`/`prefetch_related` for N+1 avoidance

3. **Serialization Strategy**:
   - Nested serializers with controlled depth
   - Custom field-level validation
   - Serializer method fields for computed values

## Implementation Tasks

### 1. Enhanced Poll Serializers (2 days)

```python
# apps/polls/serializers.py
class PollListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""
    question_count = serializers.IntegerField(source='questions.count', read_only=True)
    vote_count = serializers.SerializerMethodField()
    creator_username = serializers.ReadOnlyField(source='creator.username')
    
    class Meta:
        model = Poll
        fields = ['id', 'title', 'description', 'creator_username', 
                 'is_active', 'expires_at', 'is_public', 'created_at',
                 'question_count', 'vote_count']
    
    def get_vote_count(self, obj):
        return Choice.objects.filter(question__poll=obj).aggregate(
            total_votes=Sum('vote_count'))['total_votes'] or 0

class PollDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer with nested questions and choices"""
    questions = QuestionSerializer(many=True, read_only=True)
    creator = UserSerializer(read_only=True)
    is_bookmarked = serializers.SerializerMethodField()
    
    class Meta:
        model = Poll
        fields = ['id', 'title', 'description', 'creator', 'is_active',
                 'expires_at', 'is_public', 'created_at', 'questions',
                 'allows_revote', 'category', 'is_bookmarked']
    
    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Bookmark.objects.filter(user=request.user, poll=obj).exists()
        return False

# apps/polls/views.py
class PollViewSet(viewsets.ModelViewSet):
    queryset = Poll.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsCreatorOrReadOnly]
    filterset_class = PollFilter
    search_fields = ['title', 'description', 'category__name']
    ordering_fields = ['created_at', 'expires_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PollListSerializer
        return PollDetailSerializer
```

### 2. Category Management API (1 day)

```python
# apps/core/serializers.py
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description']
        read_only_fields = ['slug']

# apps/core/views.py
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'slug'

# api/v1/urls.py
router.register(r'categories', CategoryViewSet)
```

### 3. User Profile API (2 days)

```python
# apps/core/serializers.py
class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'bio', 'avatar', 'location', 'social_links',
                 'total_referrals', 'referral_earnings']
        read_only_fields = ['total_referrals', 'referral_earnings']

# apps/core/views.py
class UserProfileViewSet(viewsets.ModelViewSet):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return UserProfile.objects.all()
        return UserProfile.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

# api/v1/urls.py
router.register(r'profiles', UserProfileViewSet)
```

### 4. Bookmark System (1 day)

```python
# apps/polls/serializers.py
class BookmarkSerializer(serializers.ModelSerializer):
    poll_title = serializers.ReadOnlyField(source='poll.title')
    
    class Meta:
        model = Bookmark
        fields = ['id', 'poll', 'poll_title', 'created_at']
        read_only_fields = ['created_at']
    
    def validate(self, attrs):
        request = self.context.get('request')
        if Bookmark.objects.filter(user=request.user, poll=attrs['poll']).exists():
            raise serializers.ValidationError("Poll already bookmarked")
        return attrs

# apps/polls/views.py
class BookmarkViewSet(viewsets.ModelViewSet):
    serializer_class = BookmarkSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Bookmark.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

# api/v1/urls.py
router.register(r'bookmarks', BookmarkViewSet)
```

### 5. Advanced Poll Filtering (2 days)

```python
# apps/polls/filters.py
class PollFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(lookup_expr='icontains')
    category = django_filters.ModelChoiceFilter(queryset=Category.objects.all())
    creator = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    is_active = django_filters.BooleanFilter()
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    expires_after = django_filters.DateTimeFilter(field_name='expires_at', lookup_expr='gte')
    expires_before = django_filters.DateTimeFilter(field_name='expires_at', lookup_expr='lte')
    
    class Meta:
        model = Poll
        fields = ['title', 'category', 'creator', 'is_active', 'is_public']
```

### 6. Social Sharing API (2 days)

```python
# apps/polls/serializers.py
class PollShareSerializer(serializers.ModelSerializer):
    class Meta:
        model = PollShare
        fields = ['id', 'poll', 'platform', 'shared_at', 
                 'referral_code', 'clicks', 'conversions']
        read_only_fields = ['shared_at', 'clicks', 'conversions', 'referral_code']
    
    def create(self, validated_data):
        # Generate a unique referral code
        validated_data['referral_code'] = uuid.uuid4().hex[:10]
        return super().create(validated_data)

# apps/polls/views.py
class PollShareView(generics.CreateAPIView):
    serializer_class = PollShareSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user,
            shared_at=timezone.now()
        )

class TrackShareClickView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, *args, **kwargs):
        referral_code = self.kwargs.get('referral_code')
        try:
            share = PollShare.objects.get(referral_code=referral_code)
            share.clicks += 1
            share.save(update_fields=['clicks'])
            # Redirect to the poll
            return Response({'poll_id': share.poll_id})
        except PollShare.DoesNotExist:
            return Response({'error': 'Invalid referral code'}, status=404)

# api/v1/urls.py
urlpatterns += [
    path('shares/', PollShareView.as_view(), name='poll-share'),
    path('shares/<str:referral_code>/track/', TrackShareClickView.as_view(), name='track-share'),
]
```

## Performance Considerations

1. **Database Query Optimization**:
   - Add composite indexes for common filter patterns:
     ```python
     class Poll(models.Model):
         # ... fields ...
         
         class Meta:
             indexes = [
                 models.Index(fields=['is_active', 'is_public']),
                 models.Index(fields=['creator', 'created_at']),
                 models.Index(fields=['category', 'is_active']),
             ]
     ```

2. **Serializer Performance**:
   - Use different serializers for list vs. detail views
   - Avoid serializing large nested structures in list views
   - Use `SerializerMethodField` sparingly with caching

3. **Query Reduction**:
   - Implement custom managers for common query patterns:
     ```python
     class PollManager(models.Manager):
         def active_public(self):
             return self.filter(is_active=True, is_public=True)
             
         def with_vote_counts(self):
             return self.annotate(
                 total_votes=Sum('questions__choices__vote_count')
             )
     ```

## Testing Requirements

1. **Unit Tests**:
   - Test filter combinations for expected result counts
   - Verify permission enforcement with various user roles
   - Validate serializer edge cases

2. **Integration Tests**:
   - Test bookmark operations end-to-end
   - Verify social sharing flow with click tracking
   - Test category association with polls

3. **Performance Tests**:
   - Profile filterset performance with large datasets
   - Measure response time for common query patterns

## Definition of Done

- All CRUD operations for each model work correctly
- Filtering, ordering, and search functions as expected
- Permissions are enforced at object and field levels
- All nested serialization works for complex object graphs
- Bookmarking and social sharing flows are functional
- Tests demonstrate query optimization is working effectively
