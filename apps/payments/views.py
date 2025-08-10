import json
import logging
from datetime import timedelta
from decimal import Decimal
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Sum, Q
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import User
from .models import Payment, Refund, ReferralReward
from .serializers import (
    PaymentSerializer, PaymentInitializeSerializer, RefundSerializer,
    RefundCreateSerializer, ReferralRewardSerializer, ReferralSummarySerializer
)
from .services.payment_service import PaymentService
from .services.paystack_client import PaystackClient

logger = logging.getLogger(__name__)


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Payment.objects.all().select_related('user', 'poll', 'referred_by')
        return Payment.objects.filter(user=self.request.user).select_related('poll', 'referred_by')

    @action(detail=False, methods=['post'])
    def initialize(self, request):
        """Initialize a payment for a poll"""
        serializer = PaymentInitializeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Check for referral
        referred_by = None
        if serializer.validated_data.get('referral_code'):
            try:
                referred_by = User.objects.get(
                    referral_code=serializer.validated_data['referral_code']
                )
                # Prevent self-referrals
                if referred_by.id == request.user.id:
                    referred_by = None
            except User.DoesNotExist:
                pass

        # Create payment
        service = PaymentService()
        payment, payment_url, error = service.create_payment(
            user=request.user,
            poll_id=serializer.validated_data['poll_id'],
            votes_count=serializer.validated_data['votes_count'],
            referred_by=referred_by
        )

        if error:
            return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'payment_id': payment.id,
            'payment_url': payment_url,
            'amount': payment.amount,
            'currency': payment.currency,
            'votes_purchased': payment.votes_purchased
        })

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify a payment"""
        try:
            payment = self.get_object()

            if payment.status == 'completed':
                return Response({'message': 'Payment already verified'})

            service = PaymentService()
            success, message = service.verify_payment(
                payment.provider_reference)

            if success:
                return Response({'message': message})
            else:
                return Response(
                    {'error': message},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            logger.error(f"Payment verification error: {str(e)}")
            return Response(
                {'error': 'Verification failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RefundViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RefundSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Refund.objects.all().select_related('payment__user', 'requested_by', 'reviewed_by')
        return Refund.objects.filter(
            Q(requested_by=self.request.user) | Q(
                payment__user=self.request.user)
        ).select_related('payment', 'requested_by', 'reviewed_by')

    @action(detail=False, methods=['post'])
    def create_request(self, request):
        """Create a refund request"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only staff can create refund requests'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = RefundCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = PaymentService()
        refund, error = service.create_refund(
            payment_id=serializer.validated_data['payment_id'],
            reason=serializer.validated_data['reason'],
            reason_description=serializer.validated_data.get(
                'reason_description', ''),
            requested_by=request.user,
            amount=serializer.validated_data.get('amount')
        )

        if error:
            return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)

        return Response(RefundSerializer(refund).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve and process a refund"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only staff can approve refunds'},
                status=status.HTTP_403_FORBIDDEN
            )

        refund = self.get_object()

        if refund.status != 'pending':
            return Response(
                {'error': 'Refund is not in pending status'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = PaymentService()
        success, message = service.process_refund(refund.id, request.user)

        if success:
            return Response({'message': message})
        else:
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)


class ReferralRewardViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ReferralRewardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return ReferralReward.objects.all().select_related('user', 'payment__poll')
        return ReferralReward.objects.filter(user=self.request.user).select_related('payment__poll')

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get referral reward summary for the authenticated user"""
        rewards = self.get_queryset()

        total_rewards = rewards.aggregate(total=Sum('amount'))[
            'total'] or Decimal('0.00')
        pending_rewards = rewards.filter(is_paid=False).aggregate(
            total=Sum('amount'))['total'] or Decimal('0.00')
        paid_rewards = total_rewards - pending_rewards

        # This month's rewards
        this_month = timezone.now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0)
        this_month_rewards = rewards.filter(
            created_at__gte=this_month
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        summary_data = {
            'total_rewards': total_rewards,
            'pending_rewards': pending_rewards,
            'paid_rewards': paid_rewards,
            'referral_code': request.user.referral_code,
            'total_referrals': rewards.count(),
            'this_month_rewards': this_month_rewards
        }

        serializer = ReferralSummarySerializer(summary_data)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def mark_paid(self, request):
        """Mark rewards as paid (staff only)"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only staff can mark rewards as paid'},
                status=status.HTTP_403_FORBIDDEN
            )

        reward_ids = request.data.get('reward_ids', [])
        if not reward_ids:
            return Response(
                {'error': 'No reward IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        updated_count = ReferralReward.objects.filter(
            id__in=reward_ids,
            is_paid=False
        ).update(
            is_paid=True,
            paid_at=timezone.now()
        )

        return Response({
            'message': f'{updated_count} rewards marked as paid'
        })


class PaystackWebhookView(APIView):
    permission_classes = []  # Public endpoint

    def post(self, request):
        """Handle Paystack webhook events"""
        payload = request.body
        signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE')

        # Verify signature
        client = PaystackClient()
        if not client.verify_webhook_signature(payload, signature):
            logger.warning("Invalid webhook signature received")
            return HttpResponse(status=401)

        try:
            # Parse event
            event_data = json.loads(payload)
            event_type = event_data.get('event')

            logger.info(f"Received webhook event: {event_type}")

            # Process webhook
            service = PaymentService()
            success, message = service.process_webhook(
                event_type, event_data.get('data', {}))

            if success:
                logger.info(f"Webhook processed successfully: {message}")
            else:
                logger.error(f"Webhook processing failed: {message}")

        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook payload")
        except Exception as e:
            logger.error(f"Webhook processing error: {str(e)}")

        # Always return 200 to acknowledge receipt
        return HttpResponse(status=200)
