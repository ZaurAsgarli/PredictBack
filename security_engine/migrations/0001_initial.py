# Generated migration for SecurityLog model
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SecurityLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('ip', models.GenericIPAddressField(blank=True, db_index=True, null=True)),
                ('event_type', models.CharField(choices=[('RATE_LIMIT', 'Rate Limit Exceeded'), ('FAILED_LOGIN', 'Failed Login Attempt'), ('UNAUTHORIZED_ACCESS', 'Unauthorized Access'), ('SUSPICIOUS_ACTIVITY', 'Suspicious Activity')], db_index=True, max_length=50)),
                ('severity', models.CharField(choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High'), ('CRITICAL', 'Critical')], default='MEDIUM', max_length=20)),
                ('message', models.TextField(blank=True, null=True)),
                ('path', models.CharField(blank=True, max_length=255, null=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='security_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'security_logs',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='securitylog',
            index=models.Index(fields=['-timestamp'], name='security_lo_timesta_idx'),
        ),
        migrations.AddIndex(
            model_name='securitylog',
            index=models.Index(fields=['event_type', '-timestamp'], name='security_lo_event_t_idx'),
        ),
        migrations.AddIndex(
            model_name='securitylog',
            index=models.Index(fields=['ip', '-timestamp'], name='security_lo_ip_times_idx'),
        ),
    ]

