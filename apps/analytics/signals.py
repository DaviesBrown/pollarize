from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from apps.polls.models import Poll, Vote, VoteSession, Bookmark, PollShare
from .models import AnalyticsEvent, PollAnalytics, UserAnalytics
from .services import AnalyticsService

User = get_user_model()


@receiver(post_save, sender=Vote)
def track_vote_event(sender, instance, created, **kwargs):
    """Track vote events for analytics"""
    if created:
        analytics_service = AnalyticsService()

        # Get poll and user from the vote
        poll = instance.choice.question.poll

        # Try to find the vote session to get user info
        vote_session = VoteSession.objects.filter(
            poll=poll,
            ip_address=instance.ip_address
        ).first()

        user = vote_session.user if vote_session else None

        # Track the event
        analytics_service.track_event(
            event_type='poll_vote',
            user=user,
            poll=poll,
            ip_address=instance.ip_address,
            metadata={
                'choice_id': instance.choice.id,
                'choice_text': instance.choice.text,
                'question_id': instance.choice.question.id,
                'question_text': instance.choice.question.text,
            }
        )


@receiver(post_save, sender=Poll)
def track_poll_creation(sender, instance, created, **kwargs):
    """Track poll creation events"""
    if created:
        analytics_service = AnalyticsService()

        analytics_service.track_event(
            event_type='poll_create',
            user=instance.creator,
            poll=instance,
            metadata={
                'is_paid': instance.is_paid,
                'vote_price': float(instance.vote_price),
                'category': instance.category.name if instance.category else None,
                'question_count': instance.questions.count(),
            }
        )

        # Create analytics record for the poll
        PollAnalytics.objects.get_or_create(poll=instance)


@receiver(post_save, sender=Bookmark)
def track_bookmark_event(sender, instance, created, **kwargs):
    """Track bookmark events"""
    if created:
        analytics_service = AnalyticsService()

        analytics_service.track_event(
            event_type='poll_bookmark',
            user=instance.user,
            poll=instance.poll,
            metadata={
                'poll_title': instance.poll.title,
            }
        )


@receiver(post_save, sender=PollShare)
def track_share_event(sender, instance, created, **kwargs):
    """Track poll share events"""
    if created:
        analytics_service = AnalyticsService()

        analytics_service.track_event(
            event_type='poll_share',
            user=instance.user,
            poll=instance.poll,
            metadata={
                'platform': instance.platform,
                'referral_code': instance.referral_code,
            }
        )


@receiver(post_save, sender=User)
def track_user_registration(sender, instance, created, **kwargs):
    """Track user registration events"""
    if created:
        analytics_service = AnalyticsService()

        analytics_service.track_event(
            event_type='user_register',
            user=instance,
            metadata={
                'username': instance.username,
                'email': instance.email,
            }
        )

        # Create analytics record for the user
        UserAnalytics.objects.get_or_create(user=instance)


@receiver(post_save, sender=VoteSession)
def update_session_analytics(sender, instance, created, **kwargs):
    """Update analytics when vote sessions are created or updated"""
    if created:
        # Update poll analytics in real-time
        analytics_service = AnalyticsService()
        analytics_service._update_poll_analytics_realtime(instance.poll)


@receiver(post_delete, sender=Vote)
def handle_vote_deletion(sender, instance, **kwargs):
    """Handle vote deletion for analytics"""
    # Update vote counts when votes are deleted
    poll = instance.choice.question.poll

    # Update analytics
    analytics_service = AnalyticsService()
    analytics_service._update_poll_analytics_realtime(poll)


@receiver(post_delete, sender=Poll)
def handle_poll_deletion(sender, instance, **kwargs):
    """Handle poll deletion for analytics"""
    # Analytics records are deleted via CASCADE
    # Track the deletion event
    analytics_service = AnalyticsService()

    analytics_service.track_event(
        event_type='poll_delete',
        user=instance.creator,
        metadata={
            'poll_title': instance.title,
            'was_paid': instance.is_paid,
            'vote_price': float(instance.vote_price),
        }
    )
