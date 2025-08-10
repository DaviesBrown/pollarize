import uuid
from django.db import models
from django.conf import settings
from django.db.models import Sum


class PollManager(models.Manager):
    def active_public(self):
        return self.filter(is_active=True, is_public=True)
        
    def with_vote_counts(self):
        return self.annotate(
            total_votes=Sum('questions__choices__vote_count')
        )


class Poll(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='polls')
    category = models.ForeignKey(
        'core.Category', on_delete=models.SET_NULL, null=True, blank=True, related_name='polls')
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_public = models.BooleanField(default=True, db_index=True)
    allows_revote = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = PollManager()

    class Meta:
        indexes = [
            models.Index(fields=['is_active', 'is_public']),
            models.Index(fields=['creator', 'created_at']),
            models.Index(fields=['category', 'is_active']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Question(models.Model):
    QUESTION_TYPES = (
        ('single', 'Single Choice'),
        ('multiple', 'Multiple Choice'),
        ('text', 'Text Response'),
    )
    poll = models.ForeignKey(
        Poll, on_delete=models.CASCADE, related_name='questions')
    text = models.CharField(max_length=500)
    question_type = models.CharField(
        max_length=20, choices=QUESTION_TYPES, default='single')
    is_required = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.text


class Choice(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=255)
    vote_count = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.text


class VoteSession(models.Model):
    poll = models.ForeignKey(
        Poll, on_delete=models.CASCADE, related_name='vote_sessions')
    ip_address = models.GenericIPAddressField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('poll', 'ip_address')
        indexes = [
            models.Index(fields=['poll', 'ip_address']),
        ]


class Vote(models.Model):
    choice = models.ForeignKey(
        Choice, on_delete=models.CASCADE, related_name='votes')
    ip_address = models.GenericIPAddressField()
    created_at = models.DateTimeField(auto_now_add=True)


class Bookmark(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookmarks')
    poll = models.ForeignKey(
        Poll, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'poll')
        indexes = [
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} bookmarked {self.poll.title}"


class PollShare(models.Model):
    PLATFORM_CHOICES = (
        ('twitter', 'Twitter'),
        ('facebook', 'Facebook'),
        ('linkedin', 'LinkedIn'),
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
        ('telegram', 'Telegram'),
        ('reddit', 'Reddit'),
        ('other', 'Other'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shares')
    poll = models.ForeignKey(
        Poll, on_delete=models.CASCADE, related_name='shares')
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    referral_code = models.CharField(max_length=10, unique=True, blank=True)
    clicks = models.PositiveIntegerField(default=0)
    conversions = models.PositiveIntegerField(default=0)
    shared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['referral_code']),
            models.Index(fields=['user', 'shared_at']),
        ]

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = uuid.uuid4().hex[:10]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} shared {self.poll.title} on {self.platform}"
