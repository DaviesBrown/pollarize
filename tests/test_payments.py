import pytest
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch, Mock

from apps.core.models import Category
from apps.polls.models import Poll
from apps.payments.models import Payment, Refund, ReferralReward
from apps.payments.services.payment_service import PaymentService
from apps.payments.services.paystack_client import PaystackClient

User = get_user_model()


class PaymentServiceTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.referrer = User.objects.create_user(
            username='referrer',
            email='referrer@example.com',
            password='testpass123'
        )
        
        self.category = Category.objects.create(
            name='Test Category',
            description='Test category description'
        )
        
        self.poll = Poll.objects.create(
            title='Test Poll',
            description='Test poll description',
            creator=self.user,
            category=self.category,
            is_paid=True,
            vote_price=Decimal('100.00')
        )
        
        self.service = PaymentService()
    
    @patch('apps.payments.services.payment_service.PaystackClient')
    def test_create_payment_success(self, mock_paystack_class):
        """Test successful payment creation"""
        # Mock Paystack response
        mock_paystack = Mock()
        mock_paystack.initialize_transaction.return_value = {
            'status': True,
            'data': {
                'reference': 'test_ref_123',
                'authorization_url': 'https://checkout.paystack.com/test_ref_123'
            }
        }
        mock_paystack_class.return_value = mock_paystack
        
        # Create payment
        payment, payment_url, error = self.service.create_payment(
            user=self.user,
            poll_id=self.poll.id,
            votes_count=2,
            referred_by=self.referrer
        )
        
        # Assertions
        self.assertIsNotNone(payment)
        self.assertIsNotNone(payment_url)
        self.assertIsNone(error)
        self.assertEqual(payment.amount, Decimal('200.00'))  # 100 * 2 votes
        self.assertEqual(payment.votes_purchased, 2)
        self.assertEqual(payment.referred_by, self.referrer)
        self.assertEqual(payment.provider_reference, 'test_ref_123')
    
    def test_create_payment_free_poll(self):
        """Test payment creation for free poll fails"""
        free_poll = Poll.objects.create(
            title='Free Poll',
            description='Free poll description',
            creator=self.user,
            category=self.category,
            is_paid=False,
            vote_price=Decimal('0.00')
        )
        
        payment, payment_url, error = self.service.create_payment(
            user=self.user,
            poll_id=free_poll.id,
            votes_count=1
        )
        
        self.assertIsNone(payment)
        self.assertIsNone(payment_url)
        self.assertIsNotNone(error)
        self.assertIn('does not require payment', error)
    
    @patch('apps.payments.services.payment_service.PaystackClient')
    def test_verify_payment_success(self, mock_paystack_class):
        """Test successful payment verification"""
        # Create a pending payment
        payment = Payment.objects.create(
            user=self.user,
            poll=self.poll,
            amount=Decimal('100.00'),
            votes_purchased=1,
            provider_reference='test_ref_123',
            referred_by=self.referrer
        )
        
        # Mock Paystack response
        mock_paystack = Mock()
        mock_paystack.verify_transaction.return_value = {
            'status': True,
            'data': {
                'status': 'success',
                'reference': 'test_ref_123'
            }
        }
        mock_paystack_class.return_value = mock_paystack
        
        # Verify payment
        success, message = self.service.verify_payment('test_ref_123')
        
        # Assertions
        self.assertTrue(success)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'completed')
        self.assertIsNotNone(payment.completed_at)
        
        # Check referral reward was created
        reward = ReferralReward.objects.filter(
            user=self.referrer,
            payment=payment
        ).first()
        self.assertIsNotNone(reward)
        self.assertEqual(reward.amount, Decimal('10.00'))  # 10% of 100
    
    def test_create_refund(self):
        """Test refund creation"""
        # Create a completed payment
        payment = Payment.objects.create(
            user=self.user,
            poll=self.poll,
            amount=Decimal('100.00'),
            votes_purchased=1,
            status='completed',
            provider_reference='test_ref_123'
        )
        
        # Create refund
        refund, error = self.service.create_refund(
            payment_id=payment.id,
            reason='user_request',
            reason_description='User requested refund',
            requested_by=self.user
        )
        
        # Assertions
        self.assertIsNotNone(refund)
        self.assertIsNone(error)
        self.assertEqual(refund.payment, payment)
        self.assertEqual(refund.amount, payment.amount)
        self.assertEqual(refund.reason, 'user_request')
        self.assertEqual(refund.requested_by, self.user)


class PaystackClientTestCase(TestCase):
    def setUp(self):
        self.client = PaystackClient()
    
    def test_verify_webhook_signature_valid(self):
        """Test webhook signature verification with valid signature"""
        # This would need actual Paystack webhook data and signature
        # For testing, we can mock the HMAC verification
        request_body = b'{"event": "charge.success", "data": {}}'
        
        with patch('hmac.compare_digest') as mock_compare:
            mock_compare.return_value = True
            result = self.client.verify_webhook_signature(request_body, 'valid_signature')
            self.assertTrue(result)
    
    def test_verify_webhook_signature_invalid(self):
        """Test webhook signature verification with invalid signature"""
        request_body = b'{"event": "charge.success", "data": {}}'
        
        with patch('hmac.compare_digest') as mock_compare:
            mock_compare.return_value = False
            result = self.client.verify_webhook_signature(request_body, 'invalid_signature')
            self.assertFalse(result)


class PaymentModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.category = Category.objects.create(
            name='Test Category',
            description='Test category description'
        )
        
        self.poll = Poll.objects.create(
            title='Test Poll',
            description='Test poll description',
            creator=self.user,
            category=self.category,
            is_paid=True,
            vote_price=Decimal('100.00')
        )
    
    def test_payment_creation(self):
        """Test payment model creation"""
        payment = Payment.objects.create(
            user=self.user,
            poll=self.poll,
            amount=Decimal('100.00'),
            votes_purchased=1
        )
        
        self.assertEqual(payment.user, self.user)
        self.assertEqual(payment.poll, self.poll)
        self.assertEqual(payment.amount, Decimal('100.00'))
        self.assertEqual(payment.currency, 'NGN')
        self.assertEqual(payment.status, 'pending')
        self.assertEqual(payment.votes_purchased, 1)
    
    def test_referral_reward_creation(self):
        """Test referral reward model creation"""
        payment = Payment.objects.create(
            user=self.user,
            poll=self.poll,
            amount=Decimal('100.00'),
            votes_purchased=1
        )
        
        referrer = User.objects.create_user(
            username='referrer',
            email='referrer@example.com',
            password='testpass123'
        )
        
        reward = ReferralReward.objects.create(
            user=referrer,
            payment=payment,
            amount=Decimal('10.00')
        )
        
        self.assertEqual(reward.user, referrer)
        self.assertEqual(reward.payment, payment)
        self.assertEqual(reward.amount, Decimal('10.00'))
        self.assertFalse(reward.is_paid)
