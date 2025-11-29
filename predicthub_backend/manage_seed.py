#!/usr/bin/env python
"""
Standalone script to run seed data
Usage: python manage_seed.py
"""
import os
import sys
import django

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from seed import seed_data

if __name__ == '__main__':
    seed_data()

