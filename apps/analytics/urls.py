from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PollAnalyticsViewSet, UserAnalyticsViewSet, AnalyticsEventViewSet,
    AnalyticsSnapshotViewSet, AnalyticsDashboardView, ExportAnalyticsView
)

router = DefaultRouter()
router.register(r'polls', PollAnalyticsViewSet, basename='poll-analytics')
router.register(r'users', UserAnalyticsViewSet, basename='user-analytics')
router.register(r'events', AnalyticsEventViewSet, basename='analytics-events')
router.register(r'snapshots', AnalyticsSnapshotViewSet,
                basename='analytics-snapshots')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', AnalyticsDashboardView.as_view(),
         name='analytics-dashboard'),
    path('export/', ExportAnalyticsView.as_view(), name='analytics-export'),
]
