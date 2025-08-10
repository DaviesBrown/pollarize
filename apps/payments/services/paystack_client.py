import requests
import hmac
import hashlib
import logging
from decimal import Decimal
from django.conf import settings

logger = logging.getLogger(__name__)


class PaystackClient:
    """Paystack API client for payment processing"""
    
    def __init__(self):
        self.secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
        self.public_key = getattr(settings, 'PAYSTACK_PUBLIC_KEY', '')
        self.base_url = "https://api.paystack.co"
        self.headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, method, endpoint, data=None):
        """Make HTTP request to Paystack API"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=self.headers, params=data)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack API request failed: {e}")
            return {'status': False, 'message': str(e)}
    
    def initialize_transaction(self, email, amount, metadata=None, reference=None):
        """Initialize a payment transaction"""
        data = {
            'email': email,
            'amount': int(amount * 100),  # convert to kobo
            'metadata': metadata or {},
            'currency': 'NGN'
        }
        
        if reference:
            data['reference'] = reference
            
        return self._make_request('POST', '/transaction/initialize', data)
    
    def verify_transaction(self, reference):
        """Verify transaction status"""
        return self._make_request('GET', f'/transaction/verify/{reference}')
    
    def refund_transaction(self, transaction_id, amount=None):
        """Initiate a refund for a transaction"""
        data = {}
        if amount:
            data['amount'] = amount  # amount in kobo
            
        return self._make_request('POST', f'/refund', {
            'transaction': transaction_id,
            **data
        })
    
    def verify_webhook_signature(self, request_body, signature_header):
        """Verify webhook request came from Paystack"""
        if not signature_header or not self.secret_key:
            return False
            
        secret = self.secret_key.encode('utf-8')
        computed_hash = hmac.new(
            secret, 
            msg=request_body,
            digestmod=hashlib.sha512
        ).hexdigest()
        
        return hmac.compare_digest(computed_hash, signature_header)
    
    def get_transaction(self, transaction_id):
        """Get transaction details by ID"""
        return self._make_request('GET', f'/transaction/{transaction_id}')
    
    def list_transactions(self, page=1, per_page=50):
        """List transactions"""
        params = {
            'page': page,
            'perPage': per_page
        }
        return self._make_request('GET', '/transaction', params)
