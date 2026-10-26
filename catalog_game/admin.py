from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth import password_validation

from .models import Developers, Games, Genre, Platform, Reviews, Users, Wishlist


@admin.register(Developers)
class DevelopersAdmin(admin.ModelAdmin):
    list_display = ('name_dev', 'country_dev', 'city_dev', 'founded_year')
    search_fields = ('name_dev', 'country_dev', 'city_dev')
    list_filter = ('country_dev',)


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name_genre', 'descriptions')
    search_fields = ('name_genre',)


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ('name_platform', 'manufacturer')
    search_fields = ('name_platform', 'manufacturer')


class GamesAdminForm(forms.ModelForm):
    genres_selected = forms.ModelMultipleChoiceField(
        label='Жанри', queryset=Genre.objects.all(), required=False,
        widget=FilteredSelectMultiple('Жанри', False))
    platforms_selected = forms.ModelMultipleChoiceField(
        label='Платформи', queryset=Platform.objects.all(), required=False,
        widget=FilteredSelectMultiple('Платформи', False))

    class Meta:
        model = Games
        exclude = ('genres', 'platforms')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial['genres_selected'] = list(self.instance.genres.values_list('pk', flat=True))
            self.initial['platforms_selected'] = list(self.instance.platforms.values_list('pk', flat=True))


@admin.register(Games)
class GamesAdmin(admin.ModelAdmin):
    form = GamesAdminForm
    fields = ('title', 'id_dev', 'genres_selected', 'platforms_selected', 'release_date', 'age_rating',
              'file_size_gb', 'price', 'official_url', 'image_url', 'description')
    list_display = ('title', 'id_dev', 'price', 'release_date', 'age_rating', 'file_size_gb')
    search_fields = ('title', 'id_dev__name_dev')
    list_filter = ('age_rating', 'genres', 'platforms')
    list_select_related = ('id_dev',)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        game = form.instance
        game.genres.set(form.cleaned_data['genres_selected'])
        game.platforms.set(form.cleaned_data['platforms_selected'])


@admin.register(Reviews)
class ReviewsAdmin(admin.ModelAdmin):
    list_display = ('id_game', 'id_user', 'rating', 'review_date')
    list_filter = ('rating',)
    search_fields = ('id_game__title', 'id_user__email', 'comment')
    list_select_related = ('id_game', 'id_user')


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('id_user', 'id_game', 'note', 'added_date')
    search_fields = ('id_user__email', 'id_game__title', 'note')
    list_select_related = ('id_game', 'id_user')


class UsersAdminForm(forms.ModelForm):
    new_password = forms.CharField(
        label='Пароль', required=False, strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text='Для нового користувача обов’язковий; для наявного — залиште порожнім, щоб не змінювати.')

    class Meta:
        model = Users
        fields = ('email', 'firstname', 'last_name', 'date_of_birth', 'date_registration')

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()

    def clean_new_password(self):
        password = self.cleaned_data['new_password']
        if password:
            password_validation.validate_password(password, self.instance)
        elif not self.instance.pk:
            raise forms.ValidationError('Вкажіть пароль для нового користувача.')
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get('new_password'):
            user.set_password(self.cleaned_data['new_password'])
        if commit:
            user.save()
        return user


@admin.register(Users)
class UsersAdmin(admin.ModelAdmin):
    form = UsersAdminForm
    fields = ('email', 'new_password', 'firstname', 'last_name', 'date_of_birth', 'date_registration')
    list_display = ('email', 'firstname', 'last_name', 'date_of_birth', 'date_registration')
    search_fields = ('email', 'firstname', 'last_name')
    ordering = ('email',)