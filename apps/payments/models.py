import uuid
import hmac
import hashlib
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone


class Payment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('core.User', on_delete=models.CASCADE, related_name='payments')
    poll = models.ForeignKey('polls.Poll', on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='NGN')
    votes_purchased = models.IntegerField(default=1)
    
    # Payment provider fields
    provider = models.CharField(max_length=50, default='paystack')
    provider_reference = models.CharField(max_length=255, unique=True, null=True, blank=True)
    provider_metadata = models.JSONField(default=dict, blank=True)
    
    # Tracking fields
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Referral tracking
    referred_by = models.ForeignKey(
        'core.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='referred_payments'
    )

    class Meta:
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['poll', 'status']),
            models.Index(fields=['provider_reference']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.id} - {self.user.username} - {self.amount} {self.currency}"


class Refund(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('rejected', 'Rejected'),
    )
    
    REASON_CHOICES = (
        ('user_request', 'User Requested'),
        ('fraud', 'Fraudulent Transaction'),
        ('duplicate', 'Duplicate Payment'),
        ('technical_error', 'Technical Error'),
        ('other', 'Other'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey('Payment', on_delete=models.CASCADE, related_name='refunds')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    reason_description = models.TextField(blank=True)
    
    # Provider fields
    provider_reference = models.CharField(max_length=255, null=True, blank=True)
    
    # Tracking fields
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Admin tracking
    requested_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='requested_refunds'
    )
    reviewed_by = models.ForeignKey(
        'core.User', 
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='reviewed_refunds'
    )

    class Meta:
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['payment', 'status']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Refund {self.id} - {self.payment.id} - {self.amount} {self.payment.currency}"


class ReferralReward(models.Model):
    """Track referral rewards earned by users"""
    user = models.ForeignKey('core.User', on_delete=models.CASCADE, related_name='rewards')
    payment = models.ForeignKey('Payment', on_delete=models.CASCADE, related_name='rewards')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Status tracking
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_paid']),
            models.Index(fields=['payment']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Reward {self.user.username} - {self.amount} - {'Paid' if self.is_paid else 'Pending'}"
