# Phase 3: Payments & Referrals

## Architecture Overview

Phase 3 implements the monetization layer with Paystack payment processing, refund workflows, and a referral reward system. We'll create a secure transaction framework that processes payments, tracks referrals, and manages revenue streams.

## Technical Design Decisions

1. **Payment Processing Strategy**:
   - Paystack API integration with webhook-based confirmation
   - Transaction reconciliation and idempotency safeguards
   - Async handling for payment status updates

2. **Referral System Design**:
   - Unique referral codes tied to user accounts
   - Commission-based reward calculation (10% of referred payments)
   - Automatic tracking of referral source via session

3. **Security Measures**:
   - Webhook signature verification with HMAC
   - Secure API key storage in environment variables
   - IP logging and fraud detection patterns

## Implementation Tasks

### 1. Payment Models & Service Layer (3 days)

```python
# apps/payments/models.py
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

# apps/payments/services/paystack_client.py
class PaystackClient:
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.base_url = "https://api.paystack.co"
        self.headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json'
        }
    
    def initialize_transaction(self, email, amount, metadata=None, reference=None):
        """Initialize a payment transaction"""
        data = {
            'email': email,
            'amount': int(amount * 100),  # convert to kobo
            'metadata': metadata or {}
        }
        
        if reference:
            data['reference'] = reference
            
        return self._make_request('POST', '/transaction/initialize', data)
    
    def verify_transaction(self, reference):
        """Verify transaction status"""
        return self._make_request('GET', f'/transaction/verify/{reference}')
    
    def verify_webhook_signature(self, request_body, signature_header):
        """Verify webhook request came from Paystack"""
        if not signature_header:
            return False
            
        secret = settings.PAYSTACK_SECRET_KEY.encode('utf-8')
        computed_hash = hmac.new(
            secret, 
            msg=request_body,
            digestmod=hashlib.sha512
        ).hexdigest()
        
        return hmac.compare_digest(computed_hash, signature_header)
```

### 2. Refund Models & Processing (2 days)

```python
# apps/payments/models.py
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

# apps/payments/services/payment_service.py
class PaymentService:
    def __init__(self):
        self.paystack = PaystackClient()
        
    def create_payment(self, user, poll_id, votes_count=1, referred_by=None):
        """Create and initialize a payment"""
        try:
            poll = Poll.objects.get(id=poll_id)
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
                    'votes': votes_count
                }
            )
            
            if not response.get('status'):
                payment.status = 'failed'
                payment.save()
                return payment, None, response.get('message')
                
            payment.provider_reference = response['data']['reference']
            payment.save()
            
            return payment, response['data']['authorization_url'], None
        except Exception as e:
            return None, None, str(e)
    
    def process_refund(self, refund_id, reviewed_by):
        """Process an approved refund"""
        refund = Refund.objects.get(id=refund_id)
        
        if refund.status != 'pending':
            return False, "Refund already processed"
            
        refund.status = 'processing'
        refund.reviewed_by = reviewed_by
        refund.save()
        
        # Call Paystack refund API
        transaction_id = refund.payment.provider_metadata.get('id')
        response = self.paystack.refund_transaction(
            transaction_id, 
            int(refund.amount * 100)  # convert to kobo
        )
        
        if not response.get('status'):
            refund.status = 'failed'
            refund.save()
            return False, response.get('message')
            
        refund.provider_reference = response['data']['reference']
        refund.save()
        
        return True, "Refund initiated successfully"
```

### 3. Referral Reward System (2 days)

```python
# apps/payments/models.py
class ReferralReward(models.Model):
    """Track referral rewards earned by users"""
    user = models.ForeignKey('core.User', on_delete=models.CASCADE, related_name='rewards')
    payment = models.ForeignKey('Payment', on_delete=models.CASCADE, related_name='rewards')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Status tracking
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

# apps/payments/services/payment_service.py (addition to existing class)
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
    
    return reward

# Handle referral in webhook processing
def _handle_successful_payment(self, data):
    """Process a successful payment webhook"""
    reference = data.get('reference')
    
    with transaction.atomic():
        # Find payment by reference
        payment = Payment.objects.get(provider_reference=reference)
        
        if payment.status == 'completed':
            return True, "Payment already processed"
            
        # Update payment status
        payment.status = 'completed'
        payment.completed_at = timezone.now()
        payment.save()
        
        # Create vote session
        VoteSession.objects.get_or_create(
            user=payment.user,
            poll=payment.poll,
            defaults={'votes_available': payment.votes_purchased}
        )
        
        # Process referral reward if applicable
        if payment.referred_by:
            self._create_referral_reward(payment)
            
        return True, "Payment processed successfully"
```

### 4. Payment API Endpoints (2 days)

```python
# apps/payments/serializers.py
class PaymentSerializer(serializers.ModelSerializer):
    poll_title = serializers.CharField(source='poll.title', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'user', 'poll', 'poll_title', 'amount', 'currency',
            'votes_purchased', 'status', 'created_at', 'completed_at'
        ]
        read_only_fields = ['id', 'status', 'created_at', 'completed_at']

class PaymentInitializeSerializer(serializers.Serializer):
    poll_id = serializers.IntegerField()
    votes_count = serializers.IntegerField(default=1, min_value=1)
    referral_code = serializers.CharField(required=False, allow_blank=True)

# apps/payments/views.py
class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return Payment.objects.all()
        return Payment.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def initialize(self, request):
        """Initialize a payment"""
        serializer = PaymentInitializeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check for referral
        referred_by = None
        if serializer.validated_data.get('referral_code'):
            try:
                referred_by = User.objects.get(
                    referral_code=serializer.validated_data['referral_code']
                )
                if referred_by.id == request.user.id:
                    referred_by = None  # Prevent self-referrals
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
            return Response({'error': error}, status=400)
            
        return Response({
            'payment_id': payment.id,
            'payment_url': payment_url,
            'amount': payment.amount
        })
```

### 5. Webhook & Referral Endpoints (1 day)

```python
# apps/payments/views.py
class PaystackWebhookView(APIView):
    permission_classes = []  # Public endpoint
    
    def post(self, request):
        payload = request.body
        signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE')
        
        # Verify signature
        client = PaystackClient()
        if not client.verify_webhook_signature(payload, signature):
            return Response(status=401)
            
        # Parse event
        event_data = json.loads(payload)
        event_type = event_data.get('event')
        
        # Process webhook
        service = PaymentService()
        success, message = service.process_webhook(event_type, event_data.get('data', {}))
        
        # Always return 200 to acknowledge receipt
        return HttpResponse(status=200)

class ReferralRewardViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ReferralRewardSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return ReferralReward.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get referral reward summary"""
        rewards = self.get_queryset()
        total_rewards = sum(reward.amount for reward in rewards)
        pending_rewards = sum(reward.amount for reward in rewards.filter(is_paid=False))
        
        return Response({
            'total_rewards': total_rewards,
            'pending_rewards': pending_rewards,
            'referral_code': request.user.referral_code,
            'referral_count': rewards.count()
        })

# api/v1/urls.py
router.register(r'payments', PaymentViewSet)
router.register(r'rewards', ReferralRewardViewSet)

urlpatterns += [
    path('webhook/paystack/', PaystackWebhookView.as_view(), name='paystack-webhook'),
]
```

## Performance Considerations

1. **Transaction Handling**:
   - Use Django's `transaction.atomic()` for payment processing
   - Implement idempotency keys for webhook processing
   - Handle race conditions in payment/refund status updates

2. **Security Optimizations**:
   - Validate all webhook signatures cryptographically
   - Store sensitive provider data in encrypted fields
   - Implement rate limiting on payment initialization endpoints

3. **Database Optimization**:
   - Add indexes for payment queries:
     ```python
     class Payment(models.Model):
         # ... fields ...
         
         class Meta:
             indexes = [
                 models.Index(fields=['status', 'created_at']),
                 models.Index(fields=['user', 'status']),
                 models.Index(fields=['poll', 'status']),
                 models.Index(fields=['provider_reference']),
             ]
     ```

## Testing Requirements

1. **Unit Tests**:
   - Mock Paystack API responses for payment flows
   - Test webhook signature verification
   - Validate referral reward calculations

2. **Integration Tests**:
   - End-to-end payment and voting flow
   - Webhook processing with sample payloads
   - Refund request and approval workflow

3. **Security Tests**:
   - Test for webhook signature tampering
   - Verify permission boundaries for payment/refund operations
   - Validate fraud prevention measures

## Definition of Done

- Payment initialization and verification work end-to-end
- Webhook processing correctly updates payment status
- Referral rewards are accurately calculated and tracked
- Refund workflow functions for administrators
- All sensitive operations are properly secured
- Payment history is accessible to users and administrators

---
