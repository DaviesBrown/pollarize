from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ComplianceLogViewSet, GeolocationCacheViewSet,
    ComplianceRuleViewSet, ComplianceCheckView
)

router = DefaultRouter()
router.register(r'logs', ComplianceLogViewSet, basename='compliance-logs')
router.register(r'geolocation', GeolocationCacheViewSet,
                basename='geolocation-cache')
router.register(r'rules', ComplianceRuleViewSet, basename='compliance-rules')

urlpatterns = [
    path('', include(router.urls)),
    path('check/', ComplianceCheckView.as_view(), name='compliance-check'),
]
