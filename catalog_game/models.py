import re

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from .age import allowed_ratings, calculate_age, can_see_unrated, user_age
from .validators import validate_birth_date, validate_http_url


def safe_http_link(value):
    value = (value or '').strip()
    if not value:
        return ''
    if value.lower().startswith(('http://', 'https://')):
        return value
    if re.match(r'^[a-z][a-z0-9+.\-]*:', value, re.IGNORECASE):
        return ''
    return 'https://' + value

class UsersManager(BaseUserManager):
    def _create(self, email, password, **extra):
        if not email:
            raise ValueError('Потрібно вказати email.')
        user = self.model(email=self.normalize_email(email).strip().lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        return self._create(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        return self._create(email, password, **extra)


class Users(AbstractBaseUser):
    id_user = models.AutoField(primary_key=True)
    email = models.EmailField('Email', max_length=255, unique=True)
    password = models.CharField('Хеш пароля', max_length=255, db_column='password_hash')
    firstname = models.CharField('Ім’я', max_length=100, blank=True, null=True)
    last_name = models.CharField('Прізвище', max_length=100, blank=True, null=True)
    date_of_birth = models.DateField(
        'Дата народження', blank=True, null=True, validators=[validate_birth_date])
    date_registration = models.DateTimeField('Дата реєстрації', default=timezone.now)

    last_login = None

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = UsersManager()

    class Meta:
        db_table = 'users'
        managed = False
        ordering = ['email']
        verbose_name = 'Користувач'
        verbose_name_plural = 'Користувачі'

    def __str__(self):
        return self.email

    @property
    def is_superuser(self):
        return self.email.lower() in settings.ADMIN_EMAILS

    @property
    def is_staff(self):
        return self.is_superuser

    def has_perm(self, perm, obj=None):
        return self.is_active and self.is_superuser

    def has_perms(self, perm_list, obj=None):
        return all(self.has_perm(p, obj) for p in perm_list)

    def has_module_perms(self, app_label):
        return self.is_active and self.is_superuser

    @property
    def age(self):
        return calculate_age(self.date_of_birth)

    def get_full_name(self):
        return f'{self.firstname or ""} {self.last_name or ""}'.strip() or self.email

    def get_short_name(self):
        return self.firstname or self.email


class Developers(models.Model):
    id_dev = models.AutoField(primary_key=True)
    name_dev = models.CharField('Назва', max_length=255)
    founded_year = models.IntegerField(
        'Рік заснування', blank=True, null=True,
        validators=[MinValueValidator(1950), MaxValueValidator(2100)])
    city_dev = models.CharField('Місто', max_length=100, blank=True, null=True)
    country_dev = models.CharField('Країна', max_length=100, blank=True, null=True)
    email = models.EmailField('Email', max_length=255, blank=True, null=True)
    website = models.CharField('Сайт', max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'developers'
        managed = False
        ordering = ['name_dev']
        verbose_name = 'Розробник'
        verbose_name_plural = 'Розробники'

    def __str__(self):
        return self.name_dev

    def get_absolute_url(self):
        return reverse('catalog_game:developer_detail', args=[self.pk])

    @property
    def website_link(self):
        return safe_http_link(self.website)


class Genre(models.Model):
    id_genre = models.AutoField(primary_key=True)
    name_genre = models.CharField('Жанр', max_length=100)
    descriptions = models.TextField('Опис', blank=True, null=True)

    class Meta:
        db_table = 'genre'
        managed = False
        ordering = ['name_genre']
        verbose_name = 'Жанр'
        verbose_name_plural = 'Жанри'

    def __str__(self):
        return self.name_genre

    def get_absolute_url(self):
        return reverse('catalog_game:genre_detail', args=[self.pk])


class Platform(models.Model):
    id_platform = models.AutoField(primary_key=True)
    name_platform = models.CharField('Платформа', max_length=100)
    manufacturer = models.CharField('Виробник', max_length=100, blank=True, null=True)

    class Meta:
        db_table = 'platform'
        managed = False
        ordering = ['name_platform']
        verbose_name = 'Платформа'
        verbose_name_plural = 'Платформи'

    def __str__(self):
        return self.name_platform

    def get_absolute_url(self):
        return reverse('catalog_game:platform_detail', args=[self.pk])


class GamesQuerySet(models.QuerySet):

    def for_age(self, age):
        if age is None:
            return self.all()
        ratings = allowed_ratings(age, Games.AGE_CHOICES)
        condition = Q(age_rating__in=ratings)
        if can_see_unrated(age):

            condition |= Q(age_rating__isnull=True) | Q(age_rating='')
        return self.filter(condition)

    def visible_to(self, user):
        return self.for_age(user_age(user))


class Games(models.Model):

    AGE_CHOICES = [('0+', '0+'), ('3+', '3+'), ('6+', '6+'), ('7+', '7+'),
                   ('12+', '12+'), ('16+', '16+'), ('18+', '18+')]

    id_game = models.AutoField(primary_key=True)
    title = models.CharField('Назва', max_length=200)
    id_dev = models.ForeignKey(
        Developers, on_delete=models.SET_NULL, db_column='id_dev', blank=True, null=True,
        related_name='games', verbose_name='Розробник')

    genres = models.ManyToManyField(
        Genre, through='Gamegenre', blank=True, related_name='games', verbose_name='Жанри')
    platforms = models.ManyToManyField(
        Platform, through='Gameplatform', blank=True, related_name='games', verbose_name='Платформи')
    file_size_gb = models.DecimalField(
        'Розмір, ГБ', max_digits=6, decimal_places=2, blank=True, null=True,
        validators=[MinValueValidator(0)])
    release_date = models.DateField('Дата виходу', blank=True, null=True)
    description = models.TextField('Опис', blank=True, null=True)
    age_rating = models.CharField(
        'Віковий рейтинг', max_length=10, choices=AGE_CHOICES, blank=True, null=True)
    price = models.DecimalField(
        'Ціна', max_digits=10, decimal_places=2, blank=True, null=True,
        validators=[MinValueValidator(0)])
    official_url = models.CharField(
        'Офіційний сайт', max_length=500, blank=True, null=True, validators=[validate_http_url])
    image_url = models.CharField(
        'Посилання на зображення', max_length=500, blank=True, null=True, validators=[validate_http_url])

    objects = GamesQuerySet.as_manager()

    class Meta:
        db_table = 'games'
        managed = False
        ordering = ['title']
        verbose_name = 'Гра'
        verbose_name_plural = 'Ігри'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('catalog_game:game_detail', args=[self.pk])

    @property
    def hue(self):
        return 185 + sum(map(ord, self.title)) % 50

    @property
    def price_label(self):
        if self.price is None:
            return 'Ціну не вказано'
        if self.price == 0:
            return 'Безкоштовно'
        return f'{self.price:.2f} {getattr(settings, "CURRENCY", "$")}'

    @property
    def official_link(self):
        return safe_http_link(self.official_url)

    @property
    def image_link(self):
        return safe_http_link(self.image_url)


class Gamegenre(models.Model):
    id_game = models.ForeignKey(Games, on_delete=models.CASCADE, db_column='id_game',
                                primary_key=True, related_name='+')
    id_genre = models.ForeignKey(Genre, on_delete=models.CASCADE, db_column='id_genre',
                                 related_name='+')

    class Meta:
        db_table = 'gamegenre'
        managed = False
        unique_together = (('id_game', 'id_genre'),)


class Gameplatform(models.Model):
    id_game = models.ForeignKey(Games, on_delete=models.CASCADE, db_column='id_game',
                                primary_key=True, related_name='+')
    id_platform = models.ForeignKey(Platform, on_delete=models.CASCADE, db_column='id_platform',
                                    related_name='+')

    class Meta:
        db_table = 'gameplatform'
        managed = False
        unique_together = (('id_game', 'id_platform'),)


class Reviews(models.Model):
    id_review = models.AutoField(primary_key=True)
    id_user = models.ForeignKey(
        Users, on_delete=models.CASCADE, db_column='id_user',
        related_name='reviews', verbose_name='Автор')
    id_game = models.ForeignKey(
        Games, on_delete=models.CASCADE, db_column='id_game',
        related_name='reviews', verbose_name='Гра')
    rating = models.PositiveSmallIntegerField(
        'Оцінка', validators=[MinValueValidator(1), MaxValueValidator(5)])
    review_date = models.DateTimeField('Дата', default=timezone.now)
    comment = models.TextField('Коментар', blank=True, null=True)

    class Meta:
        db_table = 'reviews'
        managed = False
        ordering = ['-review_date']
        constraints = [models.UniqueConstraint(fields=['id_user', 'id_game'], name='uq_reviews_user_game')]
        verbose_name = 'Відгук'
        verbose_name_plural = 'Відгуки'

    def __str__(self):
        return f'{self.id_game} — {self.rating}/5 ({self.id_user})'

    def get_absolute_url(self):
        return reverse('catalog_game:review_detail', args=[self.pk])


class Wishlist(models.Model):
    id_wishlist = models.AutoField(primary_key=True)
    id_user = models.ForeignKey(
        Users, on_delete=models.CASCADE, db_column='id_user',
        related_name='wishes', verbose_name='Користувач')
    id_game = models.ForeignKey(
        Games, on_delete=models.CASCADE, db_column='id_game',
        related_name='wishes', verbose_name='Гра')
    note = models.CharField('Нотатка', max_length=255, blank=True, null=True)
    added_date = models.DateTimeField('Додано', default=timezone.now)

    class Meta:
        db_table = 'wishlist'
        managed = False
        ordering = ['-added_date']
        constraints = [models.UniqueConstraint(fields=['id_user', 'id_game'], name='uq_wishlist_user_game')]
        verbose_name = 'Обране'
        verbose_name_plural = 'Обране'

    def __str__(self):
        return f'{self.id_user}: {self.id_game}'

