from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from apps.core.models import Category, UserProfile

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate database with sample data for Phase 2 testing'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating sample data...'))

        # Create categories
        categories_data = [
            {'name': 'Technology', 'description': 'Tech-related polls and discussions'},
            {'name': 'Sports', 'description': 'Sports polls and predictions'},
            {'name': 'Entertainment', 'description': 'Movies, TV, music polls'},
            {'name': 'Politics', 'description': 'Political opinions and polls'},
            {'name': 'Education', 'description': 'Educational surveys and feedback'},
            {'name': 'Food & Drink', 'description': 'Culinary preferences and reviews'},
            {'name': 'Travel', 'description': 'Travel recommendations and experiences'},
            {'name': 'Health & Fitness', 'description': 'Health and wellness polls'},
        ]

        created_categories = []
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
            if created:
                created_categories.append(category.name)

        if created_categories:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Created categories: {", ".join(created_categories)}'
                )
            )

        # Create sample users with profiles
        users_data = [
            {
                'username': 'alice_tech',
                'email': 'alice@example.com',
                'password': 'demo123',
                'profile': {
                    'bio': 'Tech enthusiast and software developer',
                    'location': 'San Francisco, CA',
                    'social_links': {
                        'twitter': '@alice_codes',
                        'github': 'alice-dev'
                    }
                }
            },
            {
                'username': 'bob_sports',
                'email': 'bob@example.com',
                'password': 'demo123',
                'profile': {
                    'bio': 'Sports analyst and fantasy league expert',
                    'location': 'Chicago, IL',
                    'social_links': {
                        'twitter': '@bob_sports',
                        'instagram': 'bob_athletics'
                    }
                }
            },
            {
                'username': 'charlie_creative',
                'email': 'charlie@example.com',
                'password': 'demo123',
                'profile': {
                    'bio': 'Creative director and film enthusiast',
                    'location': 'Los Angeles, CA',
                    'social_links': {
                        'instagram': '@charlie_creates',
                        'linkedin': 'charlie-creative'
                    }
                }
            }
        ]

        created_users = []
        for user_data in users_data:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                }
            )
            if created:
                user.set_password(user_data['password'])
                user.save()
                created_users.append(user.username)

                # Create profile
                UserProfile.objects.update_or_create(
                    user=user,
                    defaults=user_data['profile']
                )

        if created_users:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Created users: {", ".join(created_users)}'
                )
            )

        # Create admin user if not exists
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            UserProfile.objects.create(
                user=admin_user,
                bio='System administrator',
                location='Server Room'
            )
            self.stdout.write(
                self.style.SUCCESS(
                    'Created admin user (username: admin, password: admin123)')
            )

        self.stdout.write(
            self.style.SUCCESS('Sample data population completed!')
        )
