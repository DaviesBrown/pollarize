import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from apps.core.models import User
from apps.polls.models import Poll, VoteSession
from ..models import Payment, Refund, ReferralReward
from .paystack_client import PaystackClient

logger = logging.getLogger(__name__)


class PaymentService:
    """Service class for handling payment operations"""
    
    def __init__(self):
        self.paystack = PaystackClient()
        
    def create_payment(self, user, poll_id, votes_count=1, referred_by=None):
        """Create and initialize a payment"""
        try:
            poll = Poll.objects.get(id=poll_id, is_active=True)
            
            # Validate paid poll
            if not poll.is_paid or poll.vote_price <= 0:
                return None, None, "This poll does not require payment"
                
            amount = poll.vote_price * votes_count
            
            payment = Payment.objects.create(
                user=user,
                poll=poll,
                amount=amount,
                votes_purchased=votes_count,
                referred_by=referred_by
            )
            
            # Initialize Paystack transaction
            response = self.paystack.initialize_transaction(
                email=user.email,
                amount=amount,
                reference=str(payment.id),
                metadata={
                    'payment_id': str(payment.id),
                    'poll_id': poll.id,
                    'votes': votes_count,
                    'user_id': user.id
                }
            )
            
            if not response.get('status'):
                payment.status = 'failed'
                payment.save()
                return payment, None, response.get('message', 'Payment initialization failed')
                
            payment.provider_reference = response['data']['reference']
            payment.provider_metadata = response.get('data', {})
            payment.save()
            
            return payment, response['data']['authorization_url'], None
            
        except Poll.DoesNotExist:
            return None, None, "Poll not found or inactive"
        except Exception as e:
            logger.error(f"Payment creation failed: {str(e)}")
            return None, None, str(e)
    
    def verify_payment(self, reference):
        """Verify payment with Paystack and update local status"""
        try:
            response = self.paystack.verify_transaction(reference)
            
            if not response.get('status'):
                return False, response.get('message', 'Verification failed')
                
            data = response.get('data', {})
            
            with transaction.atomic():
                payment = Payment.objects.get(provider_reference=reference)
                
                if payment.status == 'completed':
                    return True, "Payment already processed"
                    
                if data.get('status') == 'success':
                    payment.status = 'completed'
                    payment.completed_at = timezone.now()
                    payment.provider_metadata.update(data)
                    payment.save()
                    
                    # Create vote session
                    VoteSession.objects.get_or_create(
                        user=payment.user,
                        poll=payment.poll,
                        defaults={
                            'votes_available': payment.votes_purchased,
                            'ip_address': '0.0.0.0'  # Will be updated when user votes
                        }
                    )
                    
                    # Process referral reward
                    if payment.referred_by:
                        self._create_referral_reward(payment)
                    
                    return True, "Payment verified successfully"
                else:
                    payment.status = 'failed'
                    payment.save()
                    return False, "Payment was not successful"
                    
        except Payment.DoesNotExist:
            return False, "Payment not found"
        except Exception as e:
            logger.error(f"Payment verification failed: {str(e)}")
            return False, str(e)
    
    def process_webhook(self, event_type, data):
        """Process Paystack webhook events"""
        try:
            if event_type == 'charge.success':
                return self._handle_successful_payment(data)
            elif event_type == 'charge.failed':
                return self._handle_failed_payment(data)
            elif event_type == 'refund.processed':
                return self._handle_refund_processed(data)
            else:
                logger.info(f"Unhandled webhook event: {event_type}")
                return True, f"Event {event_type} acknowledged"
                
        except Exception as e:
            logger.error(f"Webhook processing failed: {str(e)}")
            return False, str(e)
    
    def _handle_successful_payment(self, data):
        """Process a successful payment webhook"""
        reference = data.get('reference')
        
        try:
            with transaction.atomic():
                payment = Payment.objects.get(provider_reference=reference)
                
                if payment.status == 'completed':
                    return True, "Payment already processed"
                    
                payment.status = 'completed'
                payment.completed_at = timezone.now()
                payment.provider_metadata.update(data)
                payment.save()
                
                # Create or update vote session
                VoteSession.objects.get_or_create(
                    user=payment.user,
                    poll=payment.poll,
                    defaults={
                        'votes_available': payment.votes_purchased,
                        'ip_address': '0.0.0.0'
                    }
                )
                
                # Process referral reward
                if payment.referred_by:
                    self._create_referral_reward(payment)
                    
                return True, "Payment processed successfully"
                
        except Payment.DoesNotExist:
            logger.warning(f"Payment not found for reference: {reference}")
            return True, "Payment not found, but webhook acknowledged"
    
    def _handle_failed_payment(self, data):
        """Process a failed payment webhook"""
        reference = data.get('reference')
        
        try:
            payment = Payment.objects.get(provider_reference=reference)
            payment.status = 'failed'
            payment.provider_metadata.update(data)
            payment.save()
            
            return True, "Failed payment processed"
            
        except Payment.DoesNotExist:
            return True, "Payment not found, but webhook acknowledged"
    
    def _handle_refund_processed(self, data):
        """Process a refund webhook"""
        # Implementation for refund webhook processing
        return True, "Refund webhook processed"
    
    def _create_referral_reward(self, payment):
        """Create referral reward for a successful payment"""
        if not payment.referred_by:
            return None
            
        # Calculate 10% commission
        reward_amount = payment.amount * Decimal('0.10')
        
        # Create reward record
        reward = ReferralReward.objects.create(
            user=payment.referred_by,
            payment=payment,
            amount=reward_amount
        )
        
        # Update user profile earnings
        profile = payment.referred_by.profile
        profile.referral_earnings += reward_amount
        profile.total_referrals += 1
        profile.save()
        
        return reward
    
    def create_refund(self, payment_id, reason, reason_description="", requested_by=None, amount=None):
        """Create a refund request"""
        try:
            payment = Payment.objects.get(id=payment_id, status='completed')
            
            if amount is None:
                amount = payment.amount
            elif amount > payment.amount:
                return None, "Refund amount cannot exceed payment amount"
                
            refund = Refund.objects.create(
                payment=payment,
                amount=amount,
                reason=reason,
                reason_description=reason_description,
                requested_by=requested_by
            )
            
            return refund, "Refund request created successfully"
            
        except Payment.DoesNotExist:
            return None, "Payment not found or not completed"
        except Exception as e:
            logger.error(f"Refund creation failed: {str(e)}")
            return None, str(e)
    
    def process_refund(self, refund_id, reviewed_by):
        """Process an approved refund"""
        try:
            refund = Refund.objects.get(id=refund_id, status='pending')
            
            refund.status = 'processing'
            refund.reviewed_by = reviewed_by
            refund.save()
            
            # Call Paystack refund API
            transaction_id = refund.payment.provider_metadata.get('id')
            if not transaction_id:
                refund.status = 'failed'
                refund.save()
                return False, "Transaction ID not found in payment metadata"
                
            response = self.paystack.refund_transaction(
                transaction_id, 
                int(refund.amount * 100)  # convert to kobo
            )
            
            if not response.get('status'):
                refund.status = 'failed'
                refund.save()
                return False, response.get('message', 'Refund processing failed')
                
            refund.provider_reference = response['data']['reference']
            refund.status = 'completed'
            refund.completed_at = timezone.now()
            refund.save()
            
            # Update payment status if fully refunded
            if refund.amount >= refund.payment.amount:
                refund.payment.status = 'refunded'
                refund.payment.save()
            
            return True, "Refund processed successfully"
            
        except Refund.DoesNotExist:
            return False, "Refund not found or already processed"
        except Exception as e:
            logger.error(f"Refund processing failed: {str(e)}")
            return False, str(e)
