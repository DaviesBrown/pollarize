from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import generics, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.core.cache import cache

from .models import Category, UserProfile
from .serializers import (
    TokenObtainPairResponseSerializer, UserSerializer,
    CategorySerializer, UserProfileSerializer
)
from apps.polls.permissions import IsOwnerOrReadOnly

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        # Create user profile automatically
        UserProfile.objects.create(user=user)


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'slug'


class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        if self.request.user.is_staff:
            return UserProfile.objects.all().select_related('user')
        return UserProfile.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Custom claims if needed
        token['username'] = user.username
        token['is_premium'] = user.is_premium
        token['subscription_tier'] = user.subscription_tier
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    response_serializer = TokenObtainPairResponseSerializer


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return Response({'detail': 'Not authenticated'}, status=401)
        raw = auth_header.split(' ', 1)[1]
        try:
            token = AccessToken(raw)
        except Exception:
            return Response({'detail': 'Invalid token'}, status=401)
        jti = token.get('jti')
        exp = token.get('exp')
        now_ts = int(timezone.now().timestamp())
        ttl = max(int(exp - now_ts), 0) if isinstance(exp, int) else 0
        cache.set(f'jwt:blacklist:{jti}', True, ttl or 1)
        return Response({'detail': 'Logged out'})
