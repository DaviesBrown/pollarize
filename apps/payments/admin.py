from django.contrib import admin
from django.utils.html import format_html
from .models import Payment, Refund, ReferralReward


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'poll_title', 'amount', 'currency', 'votes_purchased',
        'status', 'provider', 'created_at', 'completed_at'
    ]
    list_filter = ['status', 'provider', 'currency', 'created_at']
    search_fields = ['user__username', 'user__email', 'poll__title', 'provider_reference']
    readonly_fields = ['id', 'provider_reference', 'provider_metadata', 'created_at', 'updated_at']
    raw_id_fields = ['user', 'poll', 'referred_by']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'poll', 'amount', 'currency', 'votes_purchased')
        }),
        ('Provider Details', {
            'fields': ('provider', 'provider_reference', 'provider_metadata')
        }),
        ('Status & Tracking', {
            'fields': ('status', 'created_at', 'updated_at', 'completed_at')
        }),
        ('Referral', {
            'fields': ('referred_by',)
        }),
    )
    
    def poll_title(self, obj):
        return obj.poll.title
    poll_title.short_description = 'Poll'
    
    def has_add_permission(self, request):
        return False  # Payments should only be created through API


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'payment_id', 'amount', 'reason', 'status',
        'requested_by', 'reviewed_by', 'created_at'
    ]
    list_filter = ['status', 'reason', 'created_at']
    search_fields = ['payment__id', 'payment__user__username', 'reason_description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['payment', 'requested_by', 'reviewed_by']
    
    fieldsets = (
        ('Refund Details', {
            'fields': ('id', 'payment', 'amount', 'reason', 'reason_description')
        }),
        ('Status & Tracking', {
            'fields': ('status', 'created_at', 'updated_at', 'completed_at')
        }),
        ('Admin Tracking', {
            'fields': ('requested_by', 'reviewed_by')
        }),
        ('Provider Details', {
            'fields': ('provider_reference',)
        }),
    )
    
    def payment_id(self, obj):
        return format_html(
            '<a href="/admin/payments/payment/{}/change/">{}</a>',
            obj.payment.id, obj.payment.id
        )
    payment_id.short_description = 'Payment'


@admin.register(ReferralReward)
class ReferralRewardAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'payment_id', 'amount', 'is_paid',
        'created_at', 'paid_at'
    ]
    list_filter = ['is_paid', 'created_at', 'paid_at']
    search_fields = ['user__username', 'payment__id']
    readonly_fields = ['id', 'created_at']
    raw_id_fields = ['user', 'payment']
    
    actions = ['mark_as_paid']
    
    def mark_as_paid(self, request, queryset):
        from django.utils import timezone
        
        count = queryset.filter(is_paid=False).update(
            is_paid=True,
            paid_at=timezone.now()
        )
        self.message_user(
            request,
            f'{count} rewards marked as paid.'
        )
    mark_as_paid.short_description = 'Mark selected rewards as paid'
    
    def payment_id(self, obj):
        return format_html(
            '<a href="/admin/payments/payment/{}/change/">{}</a>',
            obj.payment.id, obj.payment.id
        )
    payment_id.short_description = 'Payment'
