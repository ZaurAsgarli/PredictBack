# Generated migration for KnowledgeTag model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('markets', '0002_create_market_activity_view'),
    ]

    operations = [
        migrations.CreateModel(
            name='KnowledgeTag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(unique=True)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name_plural': 'Knowledge Tags',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='MarketKnowledgeTag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('market', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='knowledge_tags', to='markets.market')),
                ('tag', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='markets', to='markets.knowledgetag')),
            ],
            options={
                'unique_together': {('market', 'tag')},
            },
        ),
    ]

