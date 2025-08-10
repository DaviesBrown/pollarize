from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    SUBSCRIPTION_TIERS = (
        ('free', 'Free'),
        ('pro', 'Pro'),
        ('enterprise', 'Enterprise'),
    )

    subscription_tier = models.CharField(max_length=20, choices=SUBSCRIPTION_TIERS, default='free')
    is_premium = models.BooleanField(default=False)

    def __str__(self):
        return self.username
