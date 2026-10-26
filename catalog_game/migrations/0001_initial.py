import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models

import catalog_game.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Users',
            fields=[
                ('id_user', models.AutoField(primary_key=True, serialize=False)),
                ('password', models.CharField(db_column='password_hash', max_length=255, verbose_name='Хеш пароля')),
                ('email', models.EmailField(max_length=255, unique=True, verbose_name='Email')),
                ('firstname', models.CharField(blank=True, max_length=100, null=True, verbose_name='Ім’я')),
                ('last_name', models.CharField(blank=True, max_length=100, null=True, verbose_name='Прізвище')),
                ('date_of_birth', models.DateField(blank=True, null=True, validators=[catalog_game.validators.validate_birth_date], verbose_name='Дата народження')),
                ('date_registration', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Дата реєстрації')),
            ],
            options={
                'verbose_name': 'Користувач',
                'verbose_name_plural': 'Користувачі',
                'db_table': 'users',
                'ordering': ['email'],
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Developers',
            fields=[
                ('id_dev', models.AutoField(primary_key=True, serialize=False)),
                ('name_dev', models.CharField(max_length=255, verbose_name='Назва')),
                ('founded_year', models.IntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1950), django.core.validators.MaxValueValidator(2100)], verbose_name='Рік заснування')),
                ('city_dev', models.CharField(blank=True, max_length=100, null=True, verbose_name='Місто')),
                ('country_dev', models.CharField(blank=True, max_length=100, null=True, verbose_name='Країна')),
                ('email', models.EmailField(blank=True, max_length=255, null=True, verbose_name='Email')),
                ('website', models.CharField(blank=True, max_length=255, null=True, verbose_name='Сайт')),
            ],
            options={
                'verbose_name': 'Розробник',
                'verbose_name_plural': 'Розробники',
                'db_table': 'developers',
                'ordering': ['name_dev'],
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Genre',
            fields=[
                ('id_genre', models.AutoField(primary_key=True, serialize=False)),
                ('name_genre', models.CharField(max_length=100, verbose_name='Жанр')),
                ('descriptions', models.TextField(blank=True, null=True, verbose_name='Опис')),
            ],
            options={
                'verbose_name': 'Жанр',
                'verbose_name_plural': 'Жанри',
                'db_table': 'genre',
                'ordering': ['name_genre'],
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Platform',
            fields=[
                ('id_platform', models.AutoField(primary_key=True, serialize=False)),
                ('name_platform', models.CharField(max_length=100, verbose_name='Платформа')),
                ('manufacturer', models.CharField(blank=True, max_length=100, null=True, verbose_name='Виробник')),
            ],
            options={
                'verbose_name': 'Платформа',
                'verbose_name_plural': 'Платформи',
                'db_table': 'platform',
                'ordering': ['name_platform'],
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Games',
            fields=[
                ('id_game', models.AutoField(primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=200, verbose_name='Назва')),
                ('file_size_gb', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Розмір, ГБ')),
                ('release_date', models.DateField(blank=True, null=True, verbose_name='Дата виходу')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Опис')),
                ('age_rating', models.CharField(blank=True, choices=[('3+', '3+'), ('7+', '7+'), ('12+', '12+'), ('16+', '16+'), ('18+', '18+')], max_length=10, null=True, verbose_name='Віковий рейтинг')),
                ('price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Ціна')),
                ('official_url', models.CharField(blank=True, max_length=500, null=True, validators=[catalog_game.validators.validate_http_url], verbose_name='Офіційний сайт')),
                ('image_url', models.CharField(blank=True, max_length=500, null=True, validators=[catalog_game.validators.validate_http_url], verbose_name='Посилання на зображення')),
                ('id_dev', models.ForeignKey(blank=True, db_column='id_dev', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='games', to='catalog_game.developers', verbose_name='Розробник')),
            ],
            options={
                'verbose_name': 'Гра',
                'verbose_name_plural': 'Ігри',
                'db_table': 'games',
                'ordering': ['title'],
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Gamegenre',
            fields=[
                ('id_game', models.ForeignKey(db_column='id_game', on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='+', serialize=False, to='catalog_game.games')),
                ('id_genre', models.ForeignKey(db_column='id_genre', on_delete=django.db.models.deletion.CASCADE, related_name='+', to='catalog_game.genre')),
            ],
            options={
                'db_table': 'gamegenre',
                'managed': False,
                'unique_together': {('id_game', 'id_genre')},
            },
        ),
        migrations.CreateModel(
            name='Gameplatform',
            fields=[
                ('id_game', models.ForeignKey(db_column='id_game', on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='+', serialize=False, to='catalog_game.games')),
                ('id_platform', models.ForeignKey(db_column='id_platform', on_delete=django.db.models.deletion.CASCADE, related_name='+', to='catalog_game.platform')),
            ],
            options={
                'db_table': 'gameplatform',
                'managed': False,
                'unique_together': {('id_game', 'id_platform')},
            },
        ),
        migrations.AddField(
            model_name='games',
            name='genres',
            field=models.ManyToManyField(blank=True, related_name='games', through='catalog_game.Gamegenre', to='catalog_game.genre', verbose_name='Жанри'),
        ),
        migrations.AddField(
            model_name='games',
            name='platforms',
            field=models.ManyToManyField(blank=True, related_name='games', through='catalog_game.Gameplatform', to='catalog_game.platform', verbose_name='Платформи'),
        ),
        migrations.CreateModel(
            name='Reviews',
            fields=[
                ('id_review', models.AutoField(primary_key=True, serialize=False)),
                ('rating', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)], verbose_name='Оцінка')),
                ('review_date', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Дата')),
                ('comment', models.TextField(blank=True, null=True, verbose_name='Коментар')),
                ('id_game', models.ForeignKey(db_column='id_game', on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='catalog_game.games', verbose_name='Гра')),
                ('id_user', models.ForeignKey(db_column='id_user', on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='catalog_game.users', verbose_name='Автор')),
            ],
            options={
                'verbose_name': 'Відгук',
                'verbose_name_plural': 'Відгуки',
                'db_table': 'reviews',
                'ordering': ['-review_date'],
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Wishlist',
            fields=[
                ('id_wishlist', models.AutoField(primary_key=True, serialize=False)),
                ('note', models.CharField(blank=True, max_length=255, null=True, verbose_name='Нотатка')),
                ('added_date', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Додано')),
                ('id_game', models.ForeignKey(db_column='id_game', on_delete=django.db.models.deletion.CASCADE, related_name='wishes', to='catalog_game.games', verbose_name='Гра')),
                ('id_user', models.ForeignKey(db_column='id_user', on_delete=django.db.models.deletion.CASCADE, related_name='wishes', to='catalog_game.users', verbose_name='Користувач')),
            ],
            options={
                'verbose_name': 'Обране',
                'verbose_name_plural': 'Обране',
                'db_table': 'wishlist',
                'ordering': ['-added_date'],
                'managed': False,
            },
        ),
    ]
