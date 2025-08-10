# Phase 1: API Foundation - RESTful Core

## Architecture Overview

This phase establishes the core REST API foundation with JWT authentication, serialization patterns, and essential CRUD endpoints. We'll implement the minimal viable API surface to support basic polling functionality.

## Technical Design Decisions

1. **Authentication Strategy**:
   - JWT-based with refresh token rotation for security
   - Token blacklisting via Redis for logout/invalidation
   - Custom permission classes for object-level authorization

2. **API Versioning**:
   - URL-based versioning (`/api/v1/`) for clear client compatibility
   - API resources properly namespaced under apps

3. **Response Structure**:
   - Consistent envelope format for all responses
   - Standardized error responses with error codes and messages
   - Field-level validation error reporting

## Implementation Tasks

### 1. Authentication API (2 days)

```python
# apps/core/serializers.py
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'subscription_tier', 'is_premium')
        read_only_fields = ('subscription_tier', 'is_premium')
    
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user
        
class TokenObtainPairResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()

# apps/core/views.py
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

# api/v1/urls.py
urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]
```

### 2. Core User API (1 day)

```python
# apps/core/views.py
class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user

# api/v1/urls.py
urlpatterns += [
    path('users/me/', UserProfileView.as_view(), name='user-profile'),
]
```

### 3. Poll API Core (3 days)

```python
# apps/polls/serializers.py
class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text', 'vote_count', 'order']
        read_only_fields = ['vote_count']

class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, required=False)
    
    class Meta:
        model = Question
        fields = ['id', 'text', 'question_type', 'is_required', 'order', 'choices']
    
    def create(self, validated_data):
        choices_data = validated_data.pop('choices', [])
        question = Question.objects.create(**validated_data)
        
        for choice_data in choices_data:
            Choice.objects.create(question=question, **choice_data)
        return question

class PollSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, required=False)
    creator = serializers.ReadOnlyField(source='creator.username')
    
    class Meta:
        model = Poll
        fields = ['id', 'title', 'description', 'creator', 'is_active', 
                 'expires_at', 'is_public', 'created_at', 'questions']
    
    def create(self, validated_data):
        questions_data = validated_data.pop('questions', [])
        poll = Poll.objects.create(**validated_data)
        
        for question_data in questions_data:
            choices_data = question_data.pop('choices', [])
            question = Question.objects.create(poll=poll, **question_data)
            
            for choice_data in choices_data:
                Choice.objects.create(question=question, **choice_data)
        return poll

# apps/polls/views.py
class PollViewSet(viewsets.ModelViewSet):
    queryset = Poll.objects.all()
    serializer_class = PollSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, 
                          IsCreatorOrReadOnly]
    
    def get_queryset(self):
        queryset = Poll.objects.all()
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_public=True)
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

# api/v1/urls.py
router = DefaultRouter()
router.register(r'polls', PollViewSet)

urlpatterns += [
    path('', include(router.urls)),
]
```

### 4. Voting API (2 days)

```python
# apps/polls/serializers.py
class VoteSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoteSession
        fields = ['id', 'poll', 'ip_address']
        read_only_fields = ['ip_address']

class VoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vote
        fields = ['id', 'choice', 'ip_address']
        read_only_fields = ['ip_address']
    
    def validate(self, attrs):
        # Check if user already voted on this poll
        choice = attrs['choice']
        poll = choice.question.poll
        ip_address = self.context['request'].META.get('REMOTE_ADDR')
        
        if VoteSession.objects.filter(poll=poll, ip_address=ip_address).exists():
            raise serializers.ValidationError("You have already voted on this poll")
        
        return attrs

# apps/polls/views.py
class VoteView(generics.CreateAPIView):
    serializer_class = VoteSerializer
    permission_classes = [permissions.AllowAny]
    
    def perform_create(self, serializer):
        ip_address = self.request.META.get('REMOTE_ADDR')
        choice = serializer.validated_data['choice']
        poll = choice.question.poll
        
        # Create vote
        vote = serializer.save(ip_address=ip_address)
        
        # Create vote session
        VoteSession.objects.create(poll=poll, ip_address=ip_address)
        
        # Update choice vote count (atomically)
        Choice.objects.filter(pk=choice.pk).update(vote_count=F('vote_count') + 1)
        
        return vote

# api/v1/urls.py
urlpatterns += [
    path('votes/', VoteView.as_view(), name='vote-create'),
]
```

### 5. API Documentation with drf-yasg (1 day)

```python
# config/urls.py
schema_view = get_schema_view(
    openapi.Info(
        title="Polling API",
        default_version='v1',
        description="API documentation for Polling System",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@polling.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns += [
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
```

## Performance Considerations

1. **Database Optimization**:
   - Add indexes for query patterns: `Poll.is_public` and `VoteSession.(poll_id, ip_address)`
   - Use `select_related` and `prefetch_related` for related objects

2. **Caching Strategy**:
   - Cache polls and questions with Redis (TTL: 10 minutes)
   - Cache vote counts with high-frequency invalidation

3. **Security Hardening**:
   - Rate limiting endpoints with Redis counters
   - Validate all inputs with strict serializers
   - Add CORS configuration for frontend

## Testing Requirements

1. **Unit Tests**:
   - 100% coverage for serializers with edge cases
   - Mock auth flow for all protected endpoints

2. **Integration Tests**:
   - E2E test for voting flow
   - Permission tests for CRUD operations

3. **Load Tests**:
   - Simulate 100 concurrent votes on the same poll
   - Measure response time degradation

## Definition of Done

- All API endpoints respond with proper status codes and formats
- Swagger documentation is complete and accurate
- Authentication flow works with token refresh
- All unit and integration tests pass
- Poll creation and voting works end-to-end
- Rate limiting is functional and configurable
