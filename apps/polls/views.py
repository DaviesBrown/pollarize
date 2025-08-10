from django.db.models import F
from django.core.cache import cache
from rest_framework import generics, permissions, viewsets
from rest_framework.throttling import ScopedRateThrottle

from .models import Choice, Poll, VoteSession
from .permissions import IsCreatorOrReadOnly
from .serializers import PollSerializer, VoteSerializer

CACHE_TTL = 600  # 10 minutes


def invalidate_poll_cache(poll_id: int | None = None):
    cache.delete('polls:public:list')
    if poll_id:
        cache.delete(f'polls:public:detail:{poll_id}')


class PollViewSet(viewsets.ModelViewSet):
    queryset = Poll.objects.all()
    serializer_class = PollSerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly, IsCreatorOrReadOnly]

    def get_queryset(self):
        queryset = (
            Poll.objects.all()
            .select_related('creator')
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
