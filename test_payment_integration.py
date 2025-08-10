"""
API Integration Test for Phase 3 Payment System

This script tests the complete payment workflow including:
1. User registration and authentication
2. Poll creation with payment requirements
3. Payment initialization
4. Webhook simulation
5. Referral system testing
"""

import requests
import json
import time
from decimal import Decimal

# API Configuration
BASE_URL = "http://localhost:8001/api/v1"
ADMIN_CREDENTIALS = {
    "username": "admin",
    "password": "admin123"
}


def create_test_user(username, email, password):
    """Create a test user"""
    response = requests.post(f"{BASE_URL}/auth/register/", json={
        "username": username,
        "email": email,
        "password": password
    })
    return response


def login_user(username, password):
    """Login user and get JWT token"""
    response = requests.post(f"{BASE_URL}/auth/token/", json={
        "username": username,
        "password": password
    })
    if response.status_code == 200:
        data = response.json()
        if 'data' in data and 'access' in data['data']:
            return data['data']['access']
        elif 'access' in data:
            return data['access']
        else:
            print(f"Unexpected response format: {data}")
            return None
    else:
        print(f"Login failed: {response.status_code} - {response.text}")
        return None


def create_test_poll(token, title, description, vote_price):
    """Create a test poll with payment requirement"""
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.post(f"{BASE_URL}/polls/",
                             headers=headers,
                             json={
        "title": title,
        "description": description,
        "is_paid": True,
        "vote_price": str(vote_price),
        "questions": [
            {
                "text": "What's your favorite color?",
                "question_type": "single",
                "choices": [
                        {"text": "Red", "order": 1},
                        {"text": "Blue", "order": 2},
                        {"text": "Green", "order": 3}
                ]
            }
        ]
    }
    )
    return response


def initialize_payment(token, poll_id, votes_count=1, referral_code=None):
    """Initialize a payment for a poll"""
    headers = {'Authorization': f'Bearer {token}'}
    data = {
        "poll_id": poll_id,
        "votes_count": votes_count
    }
    if referral_code:
        data["referral_code"] = referral_code

    response = requests.post(f"{BASE_URL}/payments/initialize/",
                             headers=headers,
                             json=data
                             )
    return response


def get_payments(token):
    """Get user's payments"""
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(f"{BASE_URL}/payments/", headers=headers)
    return response


def get_referral_summary(token):
    """Get user's referral summary"""
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(f"{BASE_URL}/rewards/summary/", headers=headers)
    return response


def simulate_webhook(payment_id, status="success"):
    """Simulate Paystack webhook (Note: This would need proper signature in production)"""
    webhook_data = {
        "event": "charge.success" if status == "success" else "charge.failed",
        "data": {
            "reference": payment_id,
            "status": status,
            "amount": 10000,  # Amount in kobo
            "customer": {
                "email": "test@example.com"
            }
        }
    }

    # In production, this would need proper Paystack signature
    response = requests.post(f"{BASE_URL}/webhook/paystack/",
                             json=webhook_data,
                             headers={'X-Paystack-Signature': 'mock_signature'}
                             )
    return response


def run_payment_integration_test():
    """Run complete payment system integration test"""
    print("🚀 Starting Payment System Integration Test")
    print("=" * 50)

    # Generate unique usernames with timestamp
    import time
    timestamp = str(int(time.time()))

    # Test 1: Create test users
    print("\n1. Creating test users...")

    # Create poll creator
    creator_response = create_test_user(
        f"creator_{timestamp}", f"creator_{timestamp}@test.com", "testpass123")
    print(f"   Creator registration: {creator_response.status_code}")

    # Create voter
    voter_response = create_test_user(
        f"voter_{timestamp}", f"voter_{timestamp}@test.com", "testpass123")
    print(f"   Voter registration: {voter_response.status_code}")

    # Create referrer
    referrer_response = create_test_user(
        f"referrer_{timestamp}", f"referrer_{timestamp}@test.com", "testpass123")
    print(f"   Referrer registration: {referrer_response.status_code}")

    # Test 2: Login users
    print("\n2. Logging in users...")
    creator_token = login_user(f"creator_{timestamp}", "testpass123")
    voter_token = login_user(f"voter_{timestamp}", "testpass123")
    referrer_token = login_user(f"referrer_{timestamp}", "testpass123")

    print(f"   Creator token: {'✓' if creator_token else '✗'}")
    print(f"   Voter token: {'✓' if voter_token else '✗'}")
    print(f"   Referrer token: {'✓' if referrer_token else '✗'}")

    if not all([creator_token, voter_token, referrer_token]):
        print("❌ Login failed for one or more users")
        return

    # Test 3: Create paid poll
    print("\n3. Creating paid poll...")
    poll_response = create_test_poll(
        creator_token,
        "Test Paid Poll",
        "This is a test poll that requires payment",
        Decimal('50.00')
    )
    print(f"   Poll creation: {poll_response.status_code}")

    if poll_response.status_code not in [200, 201]:
        print(f"❌ Poll creation failed: {poll_response.text}")
        return

    poll_data = poll_response.json()
    poll_id = poll_data.get('data', poll_data).get('id')
    print(f"   Poll ID: {poll_id}")

    # Test 4: Get referrer's referral code
    print("\n4. Getting referrer's referral code...")
    referrer_summary = get_referral_summary(referrer_token)
    if referrer_summary.status_code == 200:
        referral_data = referrer_summary.json()
        referral_code = referral_data.get(
            'data', referral_data).get('referral_code')
        print(f"   Referral code: {referral_code}")
    else:
        print("   ⚠️  Couldn't get referral code, proceeding without referral")
        referral_code = None

    # Test 5: Initialize payment with referral
    print("\n5. Initializing payment...")
    payment_response = initialize_payment(
        voter_token,
        poll_id,
        votes_count=2,
        referral_code=referral_code
    )
    print(f"   Payment initialization: {payment_response.status_code}")

    if payment_response.status_code not in [200, 201]:
        print(f"❌ Payment initialization failed: {payment_response.text}")
        return

    payment_data = payment_response.json()
    payment_info = payment_data.get('data', payment_data)
    payment_id = payment_info.get('payment_id')
    payment_url = payment_info.get('payment_url')

    print(f"   Payment ID: {payment_id}")
    print(f"   Payment URL: {payment_url}")
    print(
        f"   Amount: {payment_info.get('amount')} {payment_info.get('currency', 'NGN')}")

    # Test 6: Check payment status before webhook
    print("\n6. Checking initial payment status...")
    payments_response = get_payments(voter_token)
    if payments_response.status_code == 200:
        payments_data = payments_response.json()
        payments = payments_data.get('data', {}).get(
            'results', payments_data.get('results', []))
        if payments:
            latest_payment = payments[0]
            print(f"   Status: {latest_payment.get('status')}")
            print(f"   Amount: {latest_payment.get('amount')}")
        else:
            print("   No payments found")

    # Test 7: Simulate successful webhook
    print("\n7. Simulating Paystack webhook...")
    webhook_response = simulate_webhook(payment_id, "success")
    print(f"   Webhook response: {webhook_response.status_code}")

    # Give some time for webhook processing
    time.sleep(1)

    # Test 8: Check payment status after webhook
    print("\n8. Checking payment status after webhook...")
    payments_response = get_payments(voter_token)
    if payments_response.status_code == 200:
        payments_data = payments_response.json()
        payments = payments_data.get('data', {}).get(
            'results', payments_data.get('results', []))
        if payments:
            latest_payment = payments[0]
            print(f"   Status: {latest_payment.get('status')}")
            print(f"   Completed at: {latest_payment.get('completed_at')}")
        else:
            print("   No payments found")

    # Test 9: Check referral rewards
    if referral_code:
        print("\n9. Checking referral rewards...")
        referrer_summary = get_referral_summary(referrer_token)
        if referrer_summary.status_code == 200:
            summary_data = referrer_summary.json()
            summary = summary_data.get('data', summary_data)
            print(f"   Total rewards: {summary.get('total_rewards', 0)}")
            print(f"   Pending rewards: {summary.get('pending_rewards', 0)}")
            print(f"   Total referrals: {summary.get('total_referrals', 0)}")
        else:
            print(
                f"   ❌ Failed to get referral summary: {referrer_summary.status_code}")

    print("\n" + "=" * 50)
    print("✅ Payment System Integration Test Completed!")
    print("\nKey features tested:")
    print("  • User registration and authentication")
    print("  • Paid poll creation")
    print("  • Payment initialization with Paystack")
    print("  • Referral code system")
    print("  • Webhook processing simulation")
    print("  • Referral reward calculation")


if __name__ == "__main__":
    try:
        run_payment_integration_test()
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed. Make sure the Django server is running on port 8001")
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
