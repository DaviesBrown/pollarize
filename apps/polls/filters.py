import django_filters
from django.contrib.auth import get_user_model

from apps.core.models import Category
from .models import Poll

User = get_user_model()


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
