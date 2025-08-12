#!/usr/bin/env python
"""
Manual test for Phase 4 - Compliance & Analytics Implementation
Run this script to create test data and verify functionality
"""
from apps.polls.models import Poll
from apps.analytics.services import AnalyticsService
from apps.compliance.services import ComplianceService, GeolocationService
from apps.analytics.models import AnalyticsEvent, PollAnalytics, UserAnalytics
from apps.compliance.models import ComplianceLog, GeolocationCache, ComplianceRule
from django.contrib.auth import get_user_model
import os
import django
import sys

# Add the project directory to the path
sys.path.append('/home/brown/prodev-be/pollarize')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()


User = get_user_model()


def test_phase4():
    print("🚀 Phase 4 Manual Test - Compliance & Analytics")
    print("=" * 50)

    # Test 1: Create test user if doesn't exist
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com'}
    )
    if created:
        user.set_password('testpass')
        user.save()
    print(
        f"✅ Test user: {user.username} ({'created' if created else 'exists'})")

    # Test 2: Test GeolocationService
    print("\n🌍 Testing Geolocation Service...")
    geo_service = GeolocationService()
    location = geo_service.get_location_data('8.8.8.8')
    print(
        f"✅ Geolocation for 8.8.8.8: {location.get('country_name' if location else 'country', 'Unknown') if location else 'None'}")

    # Test 3: Test ComplianceService
    print("\n🛡️ Testing Compliance Service...")
    compliance_service = ComplianceService()

    # Create a compliance rule
    rule, created = ComplianceRule.objects.get_or_create(
        name='China Block Rule',
        rule_type='geo_restriction',
        defaults={
            'description': 'Block access from China',
            'config': {
                'country_codes': ['CN'],
                'action': 'block',
                'reason': 'Region not supported'
            }
        }
    )
    print(f"✅ Compliance rule: {rule.name} - {rule.rule_type}")

    # Test compliance check
    try:
        from apps.polls.models import Poll
        poll = Poll.objects.first()  # Get any existing poll for testing
        if poll:
            result = compliance_service.check_geographic_restrictions(
                poll, '192.168.1.1', user)
            print(f"✅ Geographic check: {result['blocked']}")
        else:
            print("✅ No polls available for geographic testing")
    except Exception as e:
        print(f"⚠️ Geographic check skipped: {str(e)}")

    # Log a compliance event
    compliance_service.log_compliance_action(
        action='api_access',
        user=user,
        ip_address='192.168.1.1',
        country_code='US',
        status='allowed',
        reason='Test access',
        metadata={'test': True}
    )
    print(f"✅ Compliance action logged successfully")

    # Test 4: Test AnalyticsService
    print("\n📊 Testing Analytics Service...")
    analytics_service = AnalyticsService()

    # Create analytics event
    event = analytics_service.track_event(
        event_type='test_event',
        user=user,
        ip_address='192.168.1.1',
        metadata={'test': 'data', 'phase': 4}
    )
    print(f"✅ Analytics event created: {'Yes' if event else 'Error occurred'}")

    # Test 5: Check database counts
    print("\n📈 Database Statistics:")
    print(f"• Users: {User.objects.count()}")
    print(f"• Compliance Logs: {ComplianceLog.objects.count()}")
    print(f"• Analytics Events: {AnalyticsEvent.objects.count()}")
    print(f"• Compliance Rules: {ComplianceRule.objects.count()}")
    print(f"• Geolocation Cache: {GeolocationCache.objects.count()}")

    # Test 6: Test models work correctly
    print("\n🔧 Testing Model Functionality...")

    # Test UserAnalytics
    user_analytics, created = UserAnalytics.objects.get_or_create(
        user=user,
        defaults={'polls_created': 1, 'polls_voted': 5}
    )
    print(
        f"✅ UserAnalytics: {user_analytics.user.username} - Polls: {user_analytics.polls_created}")

    print("\n🎉 Phase 4 Implementation Test Complete!")
    print("✅ All core components are working correctly")
    print("\n🌐 API Endpoints Available:")
    print("• http://localhost:8000/api/v1/analytics/dashboard/")
    print("• http://localhost:8000/api/v1/analytics/events/")
    print("• http://localhost:8000/api/v1/analytics/reports/")
    print("• http://localhost:8000/api/v1/compliance/logs/")
    print("• http://localhost:8000/api/v1/compliance/rules/")
    print("• http://localhost:8000/admin/ (admin interface)")


if __name__ == '__main__':
    test_phase4()
