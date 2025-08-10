import pytest
import json
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.models import Category, UserProfile
from apps.polls.models import Poll, Bookmark, PollShare

User = get_user_model()


def get_response_data(response):
    """Helper to extract data from envelope middleware response"""
    if hasattr(response, 'data'):
        return response.data
    try:
        json_data = response.json()
        if json_data.get('success'):
            return json_data.get('data')
        else:
            return json_data.get('error', {}).get('details', {})
    except (ValueError, AttributeError):
        return response.content


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def category():
    return Category.objects.create(
        name='Technology',
        description='Tech-related polls'
    )


@pytest.fixture
def poll(user, category):
    return Poll.objects.create(
        title='Test Poll',
        description='A test poll',
        creator=user,
        category=category,
        is_public=True
    )


@pytest.mark.django_db
class TestCategoryAPI:
    def test_list_categories_as_anonymous(self, api_client):
        """Anonymous users should not be able to list categories (admin only)"""
        Category.objects.create(name='Tech', description='Technology')
        url = reverse('category-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_category_as_admin(self, api_client):
        """Admin users should be able to create categories"""
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass'
        )
        api_client.force_authenticate(user=admin_user)
        
        url = reverse('category-list')
        data = {
            'name': 'Sports',
            'description': 'Sports-related polls'
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        response_data = get_response_data(response)
        assert response_data['name'] == 'Sports'
        assert response_data['slug'] == 'sports'


@pytest.mark.django_db
class TestUserProfileAPI:
    def test_create_profile_automatically_on_registration(self, api_client):
        """User profile should be created automatically when user registers"""
        url = reverse('register')
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'newpass123'
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        
        user = User.objects.get(username='newuser')
        assert hasattr(user, 'profile')
        assert user.profile.total_referrals == 0

    def test_update_own_profile(self, authenticated_client, user):
        """Users should be able to update their own profile"""
        profile = UserProfile.objects.create(user=user)
        url = reverse('userprofile-detail', kwargs={'pk': profile.pk})
        
        data = {
            'bio': 'Updated bio',
            'location': 'New York'
        }
        response = authenticated_client.patch(url, data)
        assert response.status_code == status.HTTP_200_OK
        response_data = get_response_data(response)
        assert response_data['bio'] == 'Updated bio'

    def test_cannot_update_others_profile(self, api_client):
        """Users should not be able to update other users' profiles"""
        user1 = User.objects.create_user(username='user1', password='pass')
        user2 = User.objects.create_user(username='user2', password='pass')
        profile1 = UserProfile.objects.create(user=user1)
        
        api_client.force_authenticate(user=user2)
        url = reverse('userprofile-detail', kwargs={'pk': profile1.pk})
        
        data = {'bio': 'Hacked bio'}
        response = api_client.patch(url, data)
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db  
class TestBookmarkAPI:
    def test_bookmark_poll(self, authenticated_client, user, poll):
        """Users should be able to bookmark polls"""
        url = reverse('bookmark-list')
        data = {'poll': poll.id}
        
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Bookmark.objects.filter(user=user, poll=poll).exists()

    def test_cannot_bookmark_same_poll_twice(self, authenticated_client, user, poll):
        """Users should not be able to bookmark the same poll twice"""
        Bookmark.objects.create(user=user, poll=poll)
        
        url = reverse('bookmark-list')
        data = {'poll': poll.id}
        
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = get_response_data(response)
        assert 'already bookmarked' in str(response_data)

    def test_list_user_bookmarks(self, authenticated_client, user, poll):
        """Users should see only their own bookmarks"""
        other_user = User.objects.create_user(username='other', password='pass')
        
        # User's bookmark
        Bookmark.objects.create(user=user, poll=poll)
        # Other user's bookmark  
        other_poll = Poll.objects.create(
            title='Other Poll',
            creator=other_user,
            is_public=True
        )
        Bookmark.objects.create(user=other_user, poll=other_poll)
        
        url = reverse('bookmark-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        response_data = get_response_data(response)
        assert len(response_data['results']) == 1
        assert response_data['results'][0]['poll'] == poll.id

    def test_delete_bookmark(self, authenticated_client, user, poll):
        """Users should be able to delete their bookmarks"""
        bookmark = Bookmark.objects.create(user=user, poll=poll)
        
        url = reverse('bookmark-detail', kwargs={'pk': bookmark.id})
        response = authenticated_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Bookmark.objects.filter(user=user, poll=poll).exists()


@pytest.mark.django_db
class TestPollShareAPI:
    def test_share_poll(self, authenticated_client, user, poll):
        """Users should be able to share polls"""
        url = reverse('poll-share')
        data = {
            'poll': poll.id,
            'platform': 'twitter'
        }
        
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        response_data = get_response_data(response)
        assert response_data['platform'] == 'twitter'
        assert 'referral_code' in response_data
        assert len(response_data['referral_code']) == 10

    def test_track_share_click(self, api_client, user, poll):
        """Share clicks should be tracked properly"""
        share = PollShare.objects.create(
            user=user,
            poll=poll,
            platform='twitter',
            referral_code='testcode123'
        )
        
        url = reverse('track-share', kwargs={'referral_code': 'testcode123'})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        response_data = get_response_data(response)
        assert response_data['poll_id'] == poll.id
        assert response_data['success'] is True
        
        share.refresh_from_db()
        assert share.clicks == 1

    def test_track_invalid_referral_code(self, api_client):
        """Invalid referral codes should return 404"""
        url = reverse('track-share', kwargs={'referral_code': 'invalid123'})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        response_data = get_response_data(response)
        assert response_data['success'] is False


@pytest.mark.django_db
class TestEnhancedPollAPI:
    def test_poll_list_serializer_fields(self, api_client, user, category):
        """Poll list should include lightweight fields"""
        poll = Poll.objects.create(
            title='Test Poll',
            description='Description',
            creator=user,
            category=category
        )
        
        url = reverse('poll-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        poll_data = response.data['results'][0]
        
        # Check lightweight fields are present
        assert 'question_count' in poll_data
        assert 'vote_count' in poll_data
        assert 'creator_username' in poll_data
        assert 'category_name' in poll_data
        # Check heavy fields are not present
        assert 'questions' not in poll_data
        assert 'creator' not in poll_data

    def test_poll_detail_serializer_fields(self, authenticated_client, user, category):
        """Poll detail should include full fields"""
        poll = Poll.objects.create(
            title='Test Poll',
            description='Description', 
            creator=user,
            category=category
        )
        
        url = reverse('poll-detail', kwargs={'pk': poll.id})
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        poll_data = response.data
        
        # Check full fields are present
        assert 'questions' in poll_data
        assert 'creator' in poll_data
        assert 'is_bookmarked' in poll_data
        assert poll_data['is_bookmarked'] is False

    def test_is_bookmarked_field(self, authenticated_client, user, category):
        """is_bookmarked should reflect actual bookmark status"""
        poll = Poll.objects.create(
            title='Test Poll',
            creator=user,
            category=category
        )
        
        # Without bookmark
        url = reverse('poll-detail', kwargs={'pk': poll.id})
        response = authenticated_client.get(url)
        assert response.data['is_bookmarked'] is False
        
        # With bookmark
        Bookmark.objects.create(user=user, poll=poll)
        response = authenticated_client.get(url)
        assert response.data['is_bookmarked'] is True

    def test_poll_search_functionality(self, api_client, user, category):
        """Search should work across title, description, and category"""
        Poll.objects.create(
            title='Python Programming',
            description='About Django',
            creator=user,
            category=category
        )
        Poll.objects.create(
            title='JavaScript Tutorial',
            description='React basics',
            creator=user,
            category=category
        )
        
        # Search by title
        url = reverse('poll-list')
        response = api_client.get(url, {'search': 'Python'})
        assert len(response.data['results']) == 1
        
        # Search by description
        response = api_client.get(url, {'search': 'Django'})
        assert len(response.data['results']) == 1
        
        # Search by category
        response = api_client.get(url, {'search': 'Technology'})
        assert len(response.data['results']) == 2

    def test_poll_ordering(self, api_client, user, category):
        """Polls should be ordered by creation date by default"""
        import time
        
        poll1 = Poll.objects.create(
            title='First Poll',
            creator=user,
            category=category
        )
        time.sleep(0.1)  # Ensure different timestamps
        poll2 = Poll.objects.create(
            title='Second Poll', 
            creator=user,
            category=category
        )
        
        url = reverse('poll-list')
        response = api_client.get(url)
        
        # Should be ordered by -created_at (newest first)
        assert response.data['results'][0]['id'] == poll2.id
        assert response.data['results'][1]['id'] == poll1.id
