import json
from django.urls import reverse
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class Phase1SmokeTests(APITestCase):
    def setUp(self):
        self.username = 'alice'
        self.password = 'Str0ng@Pass'
        self.email = 'alice@example.com'

    def test_register_and_login_and_profile(self):
        # Register
        r = self.client.post(
            reverse('register'),
            {'username': self.username, 'email': self.email,
                'password': self.password},
            format='json',
        )
        self.assertEqual(r.status_code, 201, r.content)

        # Login
        r = self.client.post(
            reverse('token_obtain_pair'),
            {'username': self.username, 'password': self.password},
            format='json',
        )
        self.assertEqual(r.status_code, 200, r.content)
        access = r.json()['data']['access'] if 'data' in r.json() else r.json()[
            'access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        # Profile
        r = self.client.get(reverse('user-profile'))
        self.assertEqual(r.status_code, 200, r.content)

    def test_poll_crud_and_vote(self):
        # Create user and login
        User.objects.create_user(username='bob', password='12345678')
        r = self.client.post(
            reverse('token_obtain_pair'),
            {'username': 'bob', 'password': '12345678'},
            format='json',
        )
        self.assertEqual(r.status_code, 200)
        access = r.json()['data']['access'] if 'data' in r.json() else r.json()[
            'access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        # Create poll with nested question/choices
        payload = {
            'title': 'Best language',
            'description': 'Vote now',
            'is_public': True,
            'questions': [
                {
                    'text': 'Favorite?',
                    'question_type': 'single',
                    'is_required': True,
                    'order': 1,
                    'choices': [
                        {'text': 'Python', 'order': 1},
                        {'text': 'JavaScript', 'order': 2},
                    ],
                }
            ],
        }
        r = self.client.post('/api/v1/polls/', payload, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        poll_id = r.json()['data']['id'] if 'data' in r.json() else r.json()[
            'id']

        # Get poll detail anonymously (cached)
        self.client.credentials()  # remove auth
        r = self.client.get(f'/api/v1/polls/{poll_id}/')
        self.assertEqual(r.status_code, 200)

        # Vote anonymously
        choice_id = r.json()['data']['questions'][0]['choices'][0]['id'] if 'data' in r.json(
        ) else r.json()['questions'][0]['choices'][0]['id']
        r = self.client.post(
            '/api/v1/votes/', {'choice': choice_id}, format='json')
        self.assertEqual(r.status_code, 201, r.content)

        # Double vote should fail
        r = self.client.post(
            '/api/v1/votes/', {'choice': choice_id}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_logout_revokes_token(self):
        u = User.objects.create_user(username='eve', password='passw0rd!')
        r = self.client.post(reverse('token_obtain_pair'), {
                             'username': 'eve', 'password': 'passw0rd!'}, format='json')
        self.assertEqual(r.status_code, 200)
        access = r.json().get('data', r.json()).get('access')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        r = self.client.post(reverse('logout'))
        self.assertEqual(r.status_code, 200)
        # Token should now be rejected
        r = self.client.get(reverse('user-profile'))
        self.assertIn(r.status_code, (401, 403))
