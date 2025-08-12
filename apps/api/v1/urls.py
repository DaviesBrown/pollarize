from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from apps.core.views import (
    CustomTokenObtainPairView,
    RegisterView,
    UserProfileView,
    LogoutView,
    CategoryViewSet,
    UserProfileViewSet,
)
from apps.polls.views import (
    PollViewSet, VoteView, BookmarkViewSet,
    PollShareView, TrackShareClickView
)
from apps.payments.views import (
    PaymentViewSet, RefundViewSet, ReferralRewardViewSet,
    PaystackWebhookView
)
from apps.analytics.views import (
    PollAnalyticsViewSet, UserAnalyticsViewSet, AnalyticsEventViewSet,
    AnalyticsSnapshotViewSet, AnalyticsDashboardView, ExportAnalyticsView
)
from apps.compliance.views import (
    ComplianceLogViewSet, GeolocationCacheViewSet,
    ComplianceRuleViewSet, ComplianceCheckView
)

router = DefaultRouter()
router.register(r'polls', PollViewSet)
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'refunds', RefundViewSet, basename='refund')
router.register(r'rewards', ReferralRewardViewSet, basename='reward')

router.register(r'categories', CategoryViewSet)
router.register(r'profiles', UserProfileViewSet)
router.register(r'bookmarks', BookmarkViewSet, basename='bookmark')

# Analytics endpoints
router.register(r'analytics/polls', PollAnalyticsViewSet,
                basename='poll-analytics')
router.register(r'analytics/users', UserAnalyticsViewSet,
                basename='user-analytics')
router.register(r'analytics/events', AnalyticsEventViewSet,
                basename='analytics-events')
router.register(r'analytics/snapshots', AnalyticsSnapshotViewSet,
                basename='analytics-snapshots')

# Compliance endpoints
router.register(r'compliance/logs', ComplianceLogViewSet,
                basename='compliance-logs')
router.register(r'compliance/geolocation',
                GeolocationCacheViewSet, basename='geolocation-cache')
router.register(r'compliance/rules', ComplianceRuleViewSet,
                basename='compliance-rules')


urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/token/', CustomTokenObtainPairView.as_view(),
         name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),

    path('users/me/', UserProfileView.as_view(), name='user-profile'),

    # Payment webhook
    path('webhook/paystack/', PaystackWebhookView.as_view(),
         name='paystack-webhook'),

    path('shares/', PollShareView.as_view(), name='poll-share'),
    path('shares/<str:referral_code>/track/',
         TrackShareClickView.as_view(), name='track-share'),

    # Analytics endpoints
    path('analytics/dashboard/', AnalyticsDashboardView.as_view(),
         name='analytics-dashboard'),
    path('analytics/export/', ExportAnalyticsView.as_view(),
         name='analytics-export'),

    # Compliance endpoints
    path('compliance/check/', ComplianceCheckView.as_view(),
         name='compliance-check'),

    path('', include(router.urls)),
    path('votes/', VoteView.as_view(), name='vote-create'),
]
