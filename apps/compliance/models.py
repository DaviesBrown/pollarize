from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class ComplianceLog(models.Model):
    """Logs compliance-related actions for audit and monitoring purposes"""

    ACTION_CHOICES = (
        ('geo_block', 'Geographic Blocking'),
        ('age_verify', 'Age Verification'),
        ('fraud_detect', 'Fraud Detection'),
        ('vote_limit', 'Vote Limit Exceeded'),
        ('region_restrict', 'Regional Restriction'),
        ('payment_block', 'Payment Blocking'),
    )

    STATUS_CHOICES = (
        ('blocked', 'Blocked'),
        ('allowed', 'Allowed'),
        ('flagged', 'Flagged for Review'),
    )

    # Core fields
    poll = models.ForeignKey(
        'polls.Poll',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='compliance_logs'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='compliance_logs'
    )

    # Request metadata
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    request_path = models.CharField(max_length=500, blank=True)

    # Compliance details
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='blocked')
    country_code = models.CharField(max_length=2, blank=True)
    blocked_reason = models.TextField()

    # Additional metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Compliance Log"
        verbose_name_plural = "Compliance Logs"
        indexes = [
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['poll', 'action']),
            models.Index(fields=['country_code', 'action']),
            models.Index(fields=['ip_address', 'created_at']),
            models.Index(fields=['user', 'action']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} - {self.ip_address} - {self.status}"


class GeolocationCache(models.Model):
    """Cache for IP geolocation data to reduce API calls"""

    ip_address = models.GenericIPAddressField(unique=True, db_index=True)
    country_code = models.CharField(max_length=2)
    country_name = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    # Cache metadata
    provider = models.CharField(max_length=50, default='ipapi.co')
    is_valid = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()

    class Meta:
        verbose_name = "Geolocation Cache"
        verbose_name_plural = "Geolocation Cache"
        indexes = [
            models.Index(fields=['expires_at']),
            models.Index(fields=['country_code']),
        ]

    def save(self, *args, **kwargs):
        if not self.expires_at:
            # Cache for 24 hours by default
            self.expires_at = timezone.now() + timezone.timedelta(hours=24)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.ip_address} -> {self.country_code}"


class ComplianceRule(models.Model):
    """Define compliance rules for different poll types and regions"""

    RULE_TYPES = (
        ('geo_restriction', 'Geographic Restriction'),
        ('age_verification', 'Age Verification'),
        ('payment_limit', 'Payment Limit'),
        ('vote_frequency', 'Vote Frequency Limit'),
    )

    name = models.CharField(max_length=255)
    rule_type = models.CharField(max_length=50, choices=RULE_TYPES)
    description = models.TextField(blank=True)

    # Rule configuration
    is_active = models.BooleanField(default=True)
    config = models.JSONField(default=dict)  # Flexible rule configuration

    # Scope
    applies_to_all_polls = models.BooleanField(default=False)
    specific_polls = models.ManyToManyField(
        'polls.Poll',
        blank=True,
        related_name='compliance_rules'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Compliance Rule"
        verbose_name_plural = "Compliance Rules"
        indexes = [
            models.Index(fields=['rule_type', 'is_active']),
            models.Index(fields=['is_active', 'created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.rule_type})"
