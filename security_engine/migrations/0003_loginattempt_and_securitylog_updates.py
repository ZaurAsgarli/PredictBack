# Generated migration for LoginAttempt model and SecurityLog updates
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('security_engine', '0002_rename_security_lo_timesta_idx_security_lo_timesta_4c7ded_idx_and_more'),
    ]

    operations = [
        # Add new fields to SecurityLog
        migrations.AddField(
            model_name='securitylog',
            name='user_agent',
            field=models.TextField(blank=True, help_text='User agent string from request', null=True),
        ),
        migrations.AddField(
            model_name='securitylog',
            name='metadata',
            field=models.JSONField(blank=True, default=dict, help_text='Additional metadata in JSON format'),
        ),
        # Create LoginAttempt model
        migrations.CreateModel(
            name='LoginAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('email', models.EmailField(db_index=True, help_text='Email address used in login attempt')),
                ('success', models.BooleanField(db_index=True, default=False)),
                ('status', models.CharField(choices=[('SUCCESS', 'Successful'), ('FAILED', 'Failed'), ('BLOCKED', 'Blocked')], db_index=True, default='FAILED', max_length=20)),
                ('failure_reason', models.CharField(blank=True, choices=[('INVALID_CREDENTIALS', 'Invalid email or password'), ('ACCOUNT_DISABLED', 'Account is disabled'), ('ACCOUNT_LOCKED', 'Account is locked'), ('TOO_MANY_ATTEMPTS', 'Too many failed attempts'), ('SUSPICIOUS_IP', 'Suspicious IP address'), ('MISSING_CREDENTIALS', 'Missing email or password')], help_text='Reason for failure if login was unsuccessful', max_length=50, null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, db_index=True, null=True)),
                ('user_agent', models.TextField(blank=True, help_text='User agent string from request', null=True)),
                ('request_path', models.CharField(blank=True, max_length=255, null=True)),
                ('country', models.CharField(blank=True, help_text='Country code from IP', max_length=2, null=True)),
                ('city', models.CharField(blank=True, max_length=100, null=True)),
                ('device_type', models.CharField(blank=True, help_text='Mobile, Desktop, Tablet, etc.', max_length=50, null=True)),
                ('browser', models.CharField(blank=True, max_length=100, null=True)),
                ('os', models.CharField(blank=True, help_text='Operating system', max_length=100, null=True)),
                ('is_suspicious', models.BooleanField(db_index=True, default=False)),
                ('is_bot', models.BooleanField(db_index=True, default=False)),
                ('risk_score', models.DecimalField(decimal_places=2, default=0.0, help_text='Risk score from 0-100', max_digits=5)),
                ('metadata', models.JSONField(blank=True, default=dict, help_text='Additional metadata in JSON format')),
                ('user', models.ForeignKey(blank=True, help_text='User if login was successful', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='login_attempts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Login Attempt',
                'verbose_name_plural': 'Login Attempts',
                'db_table': 'login_attempts',
                'ordering': ['-timestamp'],
            },
        ),
        # Add indexes for LoginAttempt
        migrations.AddIndex(
            model_name='loginattempt',
            index=models.Index(fields=['-timestamp'], name='login_att_timesta_idx'),
        ),
        migrations.AddIndex(
            model_name='loginattempt',
            index=models.Index(fields=['email', '-timestamp'], name='login_att_email_t_idx'),
        ),
        migrations.AddIndex(
            model_name='loginattempt',
            index=models.Index(fields=['ip_address', '-timestamp'], name='login_att_ip_add_idx'),
        ),
        migrations.AddIndex(
            model_name='loginattempt',
            index=models.Index(fields=['success', '-timestamp'], name='login_att_success_idx'),
        ),
        migrations.AddIndex(
            model_name='loginattempt',
            index=models.Index(fields=['status', '-timestamp'], name='login_att_status_idx'),
        ),
        migrations.AddIndex(
            model_name='loginattempt',
            index=models.Index(fields=['is_suspicious', '-timestamp'], name='login_att_is_susp_idx'),
        ),
    ]

