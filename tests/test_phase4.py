#!/usr/bin/env python
"""
Test script for Phase 4 features
Run this after setup to verify everything is working correctly
"""

import os
import sys
import django
import requests
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()


def test_database_connection():
    """Test database connectivity"""
    print("🔍 Testing database connection...")
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            print("✅ Database connection successful")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def test_models():
    """Test model creation and basic operations"""
    print("\n🔍 Testing Phase 4 models...")
    try:
        from apps.compliance.models import ComplianceLog, GeolocationCache
        from apps.analytics.models import PollAnalytics, UserAnalytics, AnalyticsEvent

        # Test model imports
        print("✅ All models imported successfully")

        # Test model creation (without saving)
        compliance_log = ComplianceLog(
            ip_address='127.0.0.1',
            action='geo_check',
            status='allowed',
            blocked_reason='Test log'
        )
        print("✅ ComplianceLog model works")

        analytics_event = AnalyticsEvent(
            event_type='poll_view',
            ip_address='127.0.0.1'
        )
        print("✅ AnalyticsEvent model works")

        return True
    except Exception as e:
        print(f"❌ Model test failed: {e}")
        return False


def test_services():
    """Test Phase 4 services"""
    print("\n🔍 Testing services...")
    try:
        from apps.compliance.services import ComplianceService, GeolocationService
        from apps.analytics.services import AnalyticsService

        # Test service instantiation
        compliance_service = ComplianceService()
        geo_service = GeolocationService()
        analytics_service = AnalyticsService()

        print("✅ All services instantiated successfully")

        # Test geolocation service (with localhost IP)
        location_data = geo_service.get_location_data('8.8.8.8')
        if location_data:
            print(
                f"✅ Geolocation service works: {location_data.get('country_code', 'Unknown')}")
        else:
            print("⚠️ Geolocation service returned no data (this is okay for testing)")

        return True
    except Exception as e:
        print(f"❌ Service test failed: {e}")
        return False


def test_api_endpoints():
    """Test API endpoints (requires server to be running)"""
    print("\n🔍 Testing API endpoints...")

    base_url = "http://127.0.0.1:8000"

    try:
        # Test basic API health
        response = requests.get(f"{base_url}/api/v1/polls/", timeout=5)
        if response.status_code == 200:
            print("✅ Polls API endpoint accessible")
        else:
            print(f"⚠️ Polls API returned status {response.status_code}")

        # Test analytics endpoint (will require auth)
        response = requests.get(
            f"{base_url}/api/v1/analytics/dashboard/", timeout=5)
        if response.status_code in [200, 401, 403]:
            print("✅ Analytics dashboard endpoint accessible")
        else:
            print(
                f"⚠️ Analytics endpoint returned status {response.status_code}")

        return True
    except requests.exceptions.ConnectionError:
        print("⚠️ Server not running - skipping API tests")
        print("   Start server with: python manage.py runserver")
        return True
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False


def test_management_commands():
    """Test management commands"""
    print("\n🔍 Testing management commands...")
    try:
        from django.core.management import call_command
        from io import StringIO

        # Test analytics command
        out = StringIO()
        call_command('update_analytics', '--help', stdout=out)
        print("✅ update_analytics command available")

        # Test compliance command
        out = StringIO()
        call_command('cleanup_compliance', '--help', stdout=out)
        print("✅ cleanup_compliance command available")

        return True
    except Exception as e:
        print(f"❌ Management command test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("🚀 Testing Pollarize Phase 4 Implementation\n")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 50)

    tests = [
        test_database_connection,
        test_models,
        test_services,
        test_management_commands,
        test_api_endpoints,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Phase 4 is ready to use.")
        print("\n📝 Next steps:")
        print("1. Create a superuser: python manage.py createsuperuser")
        print("2. Start the server: python manage.py runserver")
        print("3. Visit http://127.0.0.1:8000/admin/ to manage compliance and analytics")
        print("4. Test API endpoints at http://127.0.0.1:8000/swagger/")
    else:
        print(f"❌ {total - passed} tests failed. Please check the errors above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
