from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from apps.core.views import (
    CustomTokenObtainPairView,
    RegisterView,
    UserProfileView,
    LogoutView,
)
from apps.polls.views import PollViewSet, VoteView

router = DefaultRouter()
router.register(r'polls', PollViewSet)

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),

    path('users/me/', UserProfileView.as_view(), name='user-profile'),

    path('', include(router.urls)),
    path('votes/', VoteView.as_view(), name='vote-create'),
]
