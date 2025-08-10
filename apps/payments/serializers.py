from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Payment, Refund, ReferralReward

User = get_user_model()


class PaymentSerializer(serializers.ModelSerializer):
    poll_title = serializers.CharField(source='poll.title', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'user', 'user_username', 'poll', 'poll_title', 'amount', 'currency',
            'votes_purchased', 'status', 'provider', 'created_at', 'completed_at',
            'referred_by'
        ]
        read_only_fields = ['id', 'status', 'provider', 'created_at', 'completed_at']


class PaymentInitializeSerializer(serializers.Serializer):
    poll_id = serializers.IntegerField()
    votes_count = serializers.IntegerField(default=1, min_value=1, max_value=10)
    referral_code = serializers.CharField(required=False, allow_blank=True, max_length=10)

    def validate_poll_id(self, value):
        from apps.polls.models import Poll
        
        try:
            poll = Poll.objects.get(id=value, is_active=True)
            if not poll.is_paid or poll.vote_price <= 0:
                raise serializers.ValidationError("This poll does not require payment")
            return value
        except Poll.DoesNotExist:
            raise serializers.ValidationError("Poll not found or inactive")

    def validate_referral_code(self, value):
        if value:
            try:
                User.objects.get(referral_code=value)
                return value
            except User.DoesNotExist:
                raise serializers.ValidationError("Invalid referral code")
        return value


class RefundSerializer(serializers.ModelSerializer):
    payment_id = serializers.CharField(source='payment.id', read_only=True)
    payment_amount = serializers.DecimalField(source='payment.amount', max_digits=10, decimal_places=2, read_only=True)
    requested_by_username = serializers.CharField(source='requested_by.username', read_only=True)
    reviewed_by_username = serializers.CharField(source='reviewed_by.username', read_only=True)
    
    class Meta:
        model = Refund
        fields = [
            'id', 'payment_id', 'payment_amount', 'amount', 'reason', 
            'reason_description', 'status', 'requested_by_username',
            'reviewed_by_username', 'created_at', 'completed_at'
        ]
        read_only_fields = ['id', 'status', 'created_at', 'completed_at']


class RefundCreateSerializer(serializers.Serializer):
    payment_id = serializers.UUIDField()
    reason = serializers.ChoiceField(choices=Refund.REASON_CHOICES)
    reason_description = serializers.CharField(required=False, allow_blank=True, max_length=500)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)

    def validate_payment_id(self, value):
        try:
            payment = Payment.objects.get(id=value, status='completed')
            return value
        except Payment.DoesNotExist:
            raise serializers.ValidationError("Payment not found or not completed")


class ReferralRewardSerializer(serializers.ModelSerializer):
    payment_id = serializers.CharField(source='payment.id', read_only=True)
    poll_title = serializers.CharField(source='payment.poll.title', read_only=True)
    
    class Meta:
        model = ReferralReward
        fields = [
            'id', 'payment_id', 'poll_title', 'amount', 'is_paid', 
            'created_at', 'paid_at'
        ]
        read_only_fields = ['id', 'amount', 'is_paid', 'created_at', 'paid_at']


class ReferralSummarySerializer(serializers.Serializer):
    total_rewards = serializers.DecimalField(max_digits=10, decimal_places=2)
    pending_rewards = serializers.DecimalField(max_digits=10, decimal_places=2)
    paid_rewards = serializers.DecimalField(max_digits=10, decimal_places=2)
    referral_code = serializers.CharField()
    total_referrals = serializers.IntegerField()
    this_month_rewards = serializers.DecimalField(max_digits=10, decimal_places=2)
