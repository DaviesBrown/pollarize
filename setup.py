#!/usr/bin/env python
"""
Setup script for Pollarize API deployment
This script helps with initial setup and deployment tasks
"""

import os
import sys
import django
from django.core.management import execute_from_command_line


def setup_django():
    """Setup Django environment"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()


def run_command(command):
    """Run a Django management command"""
    print(f"Running: {' '.join(command)}")
    try:
        execute_from_command_line(command)
        print("✓ Success\n")
        return True
    except Exception as e:
        print(f"✗ Error: {e}\n")
        return False


def main():
    """Main setup function"""
    print("🚀 Setting up Pollarize API...\n")

    setup_django()

    commands = [
        # Create cache table for database caching
        ['manage.py', 'createcachetable'],

        # Make migrations for new apps
        ['manage.py', 'makemigrations', 'compliance'],
        ['manage.py', 'makemigrations', 'analytics'],
        ['manage.py', 'makemigrations', 'polls'],  # For new fields

        # Apply migrations
        ['manage.py', 'migrate'],

        # Collect static files
        ['manage.py', 'collectstatic', '--noinput'],
    ]

    success_count = 0
    for command in commands:
        if run_command(command):
            success_count += 1

    print(
        f"Setup completed: {success_count}/{len(commands)} commands successful")

    if success_count == len(commands):
        print("\n✅ Setup completed successfully!")
        print("\nNext steps:")
        print("1. Create a superuser: python manage.py createsuperuser")
        print("2. Test the API endpoints")
        print("3. Set up your web server configuration")
        print("4. Configure your domain and SSL")
    else:
        print("\n❌ Some commands failed. Please check the errors above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
