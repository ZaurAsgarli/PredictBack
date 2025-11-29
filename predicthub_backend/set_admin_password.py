"""
Script to set admin password
Run: python set_admin_password.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import User

# Set password for admin user
try:
    admin = User.objects.get(username='admin')
    admin.set_password('admin123')  # Change this to a secure password
    admin.save()
    print("SUCCESS: Admin password set successfully!")
    print("Username: admin")
    print("Password: admin123")
    print("\nIMPORTANT: Change this password after first login!")
except User.DoesNotExist:
    print("Admin user not found. Creating...")
    admin = User.objects.create_superuser(
        username='admin',
        email='admin@predicthub.local',
        password='admin123'
    )
    print("SUCCESS: Admin user created successfully!")
    print("Username: admin")
    print("Password: admin123")
    print("\nIMPORTANT: Change this password after first login!")

