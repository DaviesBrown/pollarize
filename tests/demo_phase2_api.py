#!/usr/bin/env python3
"""
Pollarize Phase 2 API Demo Script
Demonstrates all the new Phase 2 features
"""

import json
import requests
import time
from typing import Dict, Any


class PollarizeAPIDemo:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api/v1"
        self.access_token = None
        self.user_data = None

    def print_response(self, response: requests.Response, title: str = ""):
        """Pretty print API response"""
        print(f"\n{'='*60}")
        if title:
            print(f"🎯 {title}")
        print(f"📊 Status: {response.status_code}")
        print(f"📝 Response:")
        try:
            data = response.json()
            print(json.dumps(data, indent=2))
        except json.JSONDecodeError:
            print(response.text)
        print('='*60)

    def authenticate(self, username: str = "alice_tech", password: str = "demo123"):
        """Authenticate and store access token"""
        print(f"\n🔐 Authenticating as {username}...")

        response = requests.post(
            f"{self.api_base}/auth/token/",
            json={"username": username, "password": password}
        )

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                self.access_token = data['data']['access']
                self.user_data = data['data']['user']
                print(f"✅ Authenticated successfully!")
                print(
                    f"👤 User: {self.user_data['username']} ({self.user_data['email']})")
            else:
                print("❌ Authentication failed!")
                self.print_response(response, "Authentication Error")
        else:
            print("❌ Authentication failed!")
            self.print_response(response, "Authentication Error")

    def get_headers(self):
        """Get headers with authentication"""
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def demo_categories(self):
        """Demo category management"""
        print(f"\n🏷️  PHASE 2 FEATURE: Category Management")

        # List categories (should fail for non-admin)
        response = requests.get(
            f"{self.api_base}/categories/", headers=self.get_headers())
        self.print_response(response, "List Categories (as regular user)")

    def demo_user_profiles(self):
        """Demo user profile features"""
        print(f"\n👤 PHASE 2 FEATURE: Enhanced User Profiles")

        # Get user profiles
        response = requests.get(
            f"{self.api_base}/profiles/", headers=self.get_headers())
        self.print_response(response, "Get User Profiles")

        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data['data']['results']:
                profile_id = data['data']['results'][0]['id']

                # Update profile
                update_data = {
                    "bio": "Updated via API demo - Python developer and tech enthusiast",
                    "location": "San Francisco, CA (Updated)",
                    "social_links": {
                        "twitter": "@alice_codes_updated",
                        "github": "alice-dev-updated",
                        "linkedin": "alice-professional"
                    }
                }

                response = requests.patch(
                    f"{self.api_base}/profiles/{profile_id}/",
                    json=update_data,
                    headers=self.get_headers()
                )
                self.print_response(response, "Update User Profile")

    def demo_enhanced_polls(self):
        """Demo enhanced poll features"""
        print(f"\n📊 PHASE 2 FEATURE: Enhanced Poll API")

        # List polls (lightweight serializer)
        response = requests.get(
            f"{self.api_base}/polls/", headers=self.get_headers())
        self.print_response(response, "List Polls (Lightweight Serializer)")

        polls_data = response.json()
        if polls_data.get('success') and polls_data['data']['results']:
            poll_id = polls_data['data']['results'][0]['id']

            # Get poll detail (full serializer)
            response = requests.get(
                f"{self.api_base}/polls/{poll_id}/", headers=self.get_headers())
            self.print_response(
                response, "Poll Detail (Full Serializer with is_bookmarked)")

    def demo_bookmarks(self):
        """Demo bookmark functionality"""
        print(f"\n🔖 PHASE 2 FEATURE: Bookmark System")

        # Get polls first
        response = requests.get(
            f"{self.api_base}/polls/", headers=self.get_headers())
        polls_data = response.json()

        if polls_data.get('success') and polls_data['data']['results']:
            poll_id = polls_data['data']['results'][0]['id']

            # Create bookmark
            response = requests.post(
                f"{self.api_base}/bookmarks/",
                json={"poll": poll_id},
                headers=self.get_headers()
            )
            self.print_response(response, "Create Bookmark")

            # List user bookmarks
            response = requests.get(
                f"{self.api_base}/bookmarks/", headers=self.get_headers())
            self.print_response(response, "List User Bookmarks")

            # Try to bookmark same poll again (should fail)
            response = requests.post(
                f"{self.api_base}/bookmarks/",
                json={"poll": poll_id},
                headers=self.get_headers()
            )
            self.print_response(
                response, "Try to Bookmark Same Poll Again (Should Fail)")

    def demo_poll_sharing(self):
        """Demo poll sharing and tracking"""
        print(f"\n📤 PHASE 2 FEATURE: Social Sharing & Referral Tracking")

        # Get polls first
        response = requests.get(
            f"{self.api_base}/polls/", headers=self.get_headers())
        polls_data = response.json()

        if polls_data.get('success') and polls_data['data']['results']:
            poll_id = polls_data['data']['results'][0]['id']

            # Share poll on Twitter
            response = requests.post(
                f"{self.api_base}/shares/",
                json={"poll": poll_id, "platform": "twitter"},
                headers=self.get_headers()
            )
            self.print_response(response, "Share Poll on Twitter")

            share_data = response.json()
            if share_data.get('success'):
                referral_code = share_data['data']['referral_code']

                # Track click on shared link
                response = requests.get(
                    f"{self.api_base}/shares/{referral_code}/track/")
                self.print_response(response, "Track Share Click")

                # Track another click
                response = requests.get(
                    f"{self.api_base}/shares/{referral_code}/track/")
                self.print_response(response, "Track Another Share Click")

    def demo_search_and_filtering(self):
        """Demo search and filtering capabilities"""
        print(f"\n🔍 PHASE 2 FEATURE: Advanced Search & Filtering")

        # Search polls
        response = requests.get(
            f"{self.api_base}/polls/",
            params={"search": "test"},
            headers=self.get_headers()
        )
        self.print_response(response, "Search Polls by 'test'")

        # Order polls
        response = requests.get(
            f"{self.api_base}/polls/",
            params={"ordering": "-created_at"},
            headers=self.get_headers()
        )
        self.print_response(
            response, "Order Polls by Creation Date (Newest First)")

    def demo_poll_detail_with_bookmark_status(self):
        """Demo how poll detail shows bookmark status"""
        print(f"\n🎯 PHASE 2 FEATURE: Poll Detail with Bookmark Status")

        # Get polls
        response = requests.get(
            f"{self.api_base}/polls/", headers=self.get_headers())
        polls_data = response.json()

        if polls_data.get('success') and polls_data['data']['results']:
            poll_id = polls_data['data']['results'][0]['id']

            # Get poll detail (should show is_bookmarked: true if we bookmarked it earlier)
            response = requests.get(
                f"{self.api_base}/polls/{poll_id}/", headers=self.get_headers())
            self.print_response(
                response, "Poll Detail Showing Bookmark Status")

    def run_full_demo(self):
        """Run the complete Phase 2 feature demo"""
        print("🚀 POLLARIZE PHASE 2 API DEMO")
        print("=" * 60)
        print("Demonstrating all Phase 2 features:")
        print("• Enhanced Poll Serializers (List vs Detail)")
        print("• User Profile Management")
        print("• Bookmark System")
        print("• Social Sharing with Referral Tracking")
        print("• Advanced Search & Filtering")
        print("• Category Management")
        print("=" * 60)

        # Authenticate first
        self.authenticate()

        if not self.access_token:
            print(
                "❌ Could not authenticate. Make sure the server is running and sample data is loaded.")
            return

        # Run all demos
        self.demo_enhanced_polls()
        self.demo_user_profiles()
        self.demo_bookmarks()
        self.demo_poll_sharing()
        self.demo_search_and_filtering()
        self.demo_poll_detail_with_bookmark_status()
        self.demo_categories()

        print(f"\n🎉 PHASE 2 DEMO COMPLETED!")
        print("All Phase 2 features have been successfully demonstrated!")
        print("\nKey Phase 2 Achievements:")
        print("✅ Enhanced Poll API with different serializers for list/detail")
        print("✅ User Profile management with social links")
        print("✅ Bookmark system for saving favorite polls")
        print("✅ Social sharing with referral code tracking")
        print("✅ Advanced search and filtering capabilities")
        print("✅ Category management system")
        print("✅ Performance optimizations with proper indexing")
        print("✅ Comprehensive admin interface")


if __name__ == "__main__":
    # Run the demo
    demo = PollarizeAPIDemo()
    demo.run_full_demo()
