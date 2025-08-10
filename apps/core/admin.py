from django.contrib import admin
from django.contrib.auth import get_user_model

from .models import Category, UserProfile

User = get_user_model()


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email',
                    'subscription_tier', 'is_premium', 'is_active')
    search_fields = ('username', 'email')
    list_filter = ('subscription_tier', 'is_premium', 'is_active')
    inlines = [UserProfileInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'location',
                    'total_referrals', 'referral_earnings')
    search_fields = ('user__username', 'user__email', 'bio', 'location')
    list_filter = ('total_referrals', 'created_at')
    readonly_fields = ('total_referrals', 'referral_earnings',
                       'created_at', 'updated_at')
