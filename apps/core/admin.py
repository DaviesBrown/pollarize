from django.contrib import admin
from django.contrib.auth import get_user_model

User = get_user_model()


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'subscription_tier', 'is_premium', 'is_active')
    search_fields = ('username', 'email')
    list_filter = ('subscription_tier', 'is_premium', 'is_active')
