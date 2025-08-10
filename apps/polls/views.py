import uuid
from django.db.models import F
from django.core.cache import cache
from django.utils import timezone
from rest_framework import generics, permissions, viewsets, status
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Choice, Poll, VoteSession, Bookmark, PollShare
from .permissions import IsCreatorOrReadOnly
from .serializers import (
    PollSerializer, PollListSerializer, PollDetailSerializer,
    VoteSerializer, BookmarkSerializer, PollShareSerializer
)

CACHE_TTL = 600  # 10 minutes


def invalidate_poll_cache(poll_id: int | None = None):
    cache.delete('polls:public:list')
    if poll_id:
        cache.delete(f'polls:public:detail:{poll_id}')


class PollViewSet(viewsets.ModelViewSet):
    queryset = Poll.objects.all()
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly, IsCreatorOrReadOnly]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['title', 'description', 'category__name']
    ordering_fields = ['created_at', 'expires_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return PollListSerializer
        elif self.action == 'retrieve':
            return PollDetailSerializer
        return PollSerializer

    def get_queryset(self):
        queryset = (
            Poll.objects.all()
            .select_related('creator', 'category')
            .prefetch_related('questions__choices')
        )
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_public=True)
        return queryset

    def list(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            cached = cache.get('polls:public:list')
            if cached is not None:
                from rest_framework.response import Response

                return Response(cached)
        response = super().list(request, *args, **kwargs)
        if not request.user.is_authenticated and response.status_code == 200:
            cache.set('polls:public:list', response.data, CACHE_TTL)
        return response

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.is_public and not request.user.is_authenticated:
            key = f'polls:public:detail:{obj.id}'
            cached = cache.get(key)
            if cached is not None:
                from rest_framework.response import Response

                return Response(cached)
            response = super().retrieve(request, *args, **kwargs)
            if response.status_code == 200:
                cache.set(key, response.data, CACHE_TTL)
            return response
        return super().retrieve(request, *args, **kwargs)

    def perform_create(self, serializer):
        instance = serializer.save(creator=self.request.user)
        invalidate_poll_cache(instance.id)

    def perform_update(self, serializer):
        instance = serializer.save()
        invalidate_poll_cache(instance.id)

    def perform_destroy(self, instance):
        pid = instance.id
        super().perform_destroy(instance)
        invalidate_poll_cache(pid)


class VoteView(generics.CreateAPIView):
    serializer_class = VoteSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'votes'

    def perform_create(self, serializer):
        request = self.request
        ip_address = request.META.get('REMOTE_ADDR')
        choice = serializer.validated_data['choice']
        poll = choice.question.poll

        vote = serializer.save(ip_address=ip_address)
        VoteSession.objects.create(poll=poll, ip_address=ip_address)
        Choice.objects.filter(pk=choice.pk).update(
            vote_count=F('vote_count') + 1)
        invalidate_poll_cache(poll.id)
        return vote


class BookmarkViewSet(viewsets.ModelViewSet):
    serializer_class = BookmarkSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Bookmark.objects.filter(user=self.request.user).select_related('poll')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


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
            # Return the poll information for redirect
            return Response({
                'poll_id': share.poll_id,
                'poll_title': share.poll.title,
                'success': True
            })
        except PollShare.DoesNotExist:
            return Response({
                'error': 'Invalid referral code',
                'success': False
            }, status=status.HTTP_404_NOT_FOUND)
