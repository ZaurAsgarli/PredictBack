from django.db import migrations

def fix_user_roles(apps, schema_editor):
    User = apps.get_model('users', 'User')
    
    # Update 'admin' -> 'ADMIN'
    User.objects.filter(role='admin').update(role='ADMIN')
    
    # Update 'user' -> 'TRADER'
    User.objects.filter(role='user').update(role='TRADER')

def reverse_fix(apps, schema_editor):
    User = apps.get_model('users', 'User')
    
    # Revert 'ADMIN' -> 'admin'
    User.objects.filter(role='ADMIN').update(role='admin')
    
    # Revert 'TRADER' -> 'user'
    User.objects.filter(role='TRADER').update(role='user')

class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_alter_user_role'),
    ]

    operations = [
        migrations.RunPython(fix_user_roles, reverse_fix),
    ]
