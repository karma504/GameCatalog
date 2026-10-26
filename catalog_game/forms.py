from decimal import Decimal

from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm, UserCreationForm

from .models import Developers, Games, Reviews, Users
from .validators import AmountValidator, latest_birth_date, validate_birth_date, validate_http_url


class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(
        label='Email', max_length=255,
        widget=forms.EmailInput(attrs={'autofocus': True, 'autocomplete': 'email',
                                       'placeholder': 'name@example.com'}),
        error_messages={'required': 'Вкажіть email.', 'invalid': 'Введіть коректну адресу електронної пошти.'})
    password = forms.CharField(
        label='Пароль', strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
        error_messages={'required': 'Вкажіть пароль.'})
    error_messages = {
        'invalid_login': 'Невірний email або пароль. Перевірте дані й спробуйте ще раз.',
        'inactive': 'Цей акаунт вимкнено.',
    }

    def clean_username(self):
        return self.cleaned_data['username'].strip().lower()


class BirthDateField(forms.DateField):
    default_validators = [validate_birth_date]

    def __init__(self, **kwargs):
        kwargs.setdefault('label', 'Дата народження')
        kwargs.setdefault('input_formats', ['%Y-%m-%d', '%d.%m.%Y'])
        kwargs.setdefault('widget', forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}))
        kwargs.setdefault('error_messages', {'invalid': 'Введіть дату у форматі РРРР-ММ-ДД, наприклад 2012-05-21.',
                                             'required': 'Вкажіть дату народження.'})
        super().__init__(**kwargs)


def limit_birth_date_input(form):
    form.fields['date_of_birth'].widget.attrs['max'] = latest_birth_date().isoformat()


class RegisterForm(UserCreationForm):
    password1 = forms.CharField(
        label='Пароль', strip=False, widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))
    password2 = forms.CharField(
        label='Повторіть пароль', strip=False, widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))
    email = forms.EmailField(label='Email', max_length=255)
    date_of_birth = BirthDateField(required=True)

    class Meta:
        model = Users
        fields = ('firstname', 'last_name', 'email', 'date_of_birth')
        labels = {'firstname': 'Ім’я', 'last_name': 'Прізвище'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        limit_birth_date_input(self)

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if Users.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Цей email уже зареєстровано.')
        return email

    def clean_password2(self):
        p1, p2 = self.cleaned_data.get('password1'), self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Паролі не збігаються.')
        return p2




class ProfileForm(forms.ModelForm):
    email = forms.EmailField(label='Email', max_length=255)
    date_of_birth = BirthDateField(required=False)

    class Meta:
        model = Users
        fields = ('firstname', 'last_name', 'email', 'date_of_birth')
        labels = {'firstname': 'Ім’я', 'last_name': 'Прізвище'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        limit_birth_date_input(self)

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if Users.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Цей email уже зареєстровано.')
        return email


class EmailPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(label='Email', max_length=255,
                             widget=forms.EmailInput(attrs={'autocomplete': 'email', 'autofocus': True}))

    def get_users(self, email):
        return (user for user in Users.objects.filter(email__iexact=email.strip()) if user.has_usable_password())


class UkrainianPasswordChangeForm(SetPasswordForm):
    new_password1 = forms.CharField(label='Новий пароль', strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))
    new_password2 = forms.CharField(label='Повторіть новий пароль', strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.help_text = ''


class GameForm(forms.ModelForm):
    image_url = forms.URLField(
        label='Посилання на зображення', required=False, max_length=500, assume_scheme='https',
        validators=[validate_http_url],
        widget=forms.URLInput(attrs={'placeholder': 'https://example.com/game.jpg'}),
        error_messages={'invalid': 'Введіть коректне посилання, наприклад https://example.com/game.jpg.'})

    class Meta:
        model = Games
        fields = ('title', 'id_dev', 'genres', 'platforms', 'release_date', 'age_rating',
                  'file_size_gb', 'price', 'official_url', 'image_url', 'description')
        widgets = {
            'genres': forms.CheckboxSelectMultiple,
            'platforms': forms.CheckboxSelectMultiple,
            'release_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 5}),
            'official_url': forms.TextInput(attrs={'placeholder': 'https://example.com'}),
        }
        error_messages = {
            'title': {'required': 'Вкажіть назву гри.',
                      'max_length': 'Назва задовга: допустимо до 200 символів.'},
            'release_date': {'invalid': 'Введіть дату у форматі РРРР-ММ-ДД.'},
            'file_size_gb': {'invalid': 'Розмір — це число, наприклад 12,5.',
                             'max_digits': 'Забагато цифр: допустимо до 6 цифр разом.',
                             'max_whole_digits': 'Забагато цифр до коми: допустимо до 4.',
                             'max_decimal_places': 'Після коми потрібно не більше двох цифр.'},
            'price': {'invalid': 'Ціна — це число, наприклад 19,99.',
                      'max_whole_digits': 'Забагато цифр до коми: допустимо до 8.',
                      'max_decimal_places': 'Після коми потрібно не більше двох цифр.'},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['id_dev'].queryset = Developers.objects.order_by('name_dev')
        self.fields['id_dev'].empty_label = 'Не вказано'
        self.fields['age_rating'].choices = [('', 'Не вказано')] + list(Games.AGE_CHOICES)

    def clean_title(self):
        title = ' '.join(self.cleaned_data['title'].split())
        same = Games.objects.filter(title__iexact=title).exclude(pk=self.instance.pk)
        if same.exists():
            raise forms.ValidationError('Гра з такою назвою вже є в каталозі.')
        return title

    def clean_image_url(self):
        return self.cleaned_data.get('image_url') or None


class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(
        label='Оцінка', coerce=int, choices=[(i, f'{i} з 5') for i in range(5, 0, -1)],
        error_messages={'required': 'Поставте оцінку від 1 до 5.',
                        'invalid_choice': 'Оберіть оцінку зі списку: від 1 до 5.'})
    comment = forms.CharField(
        label='Коментар', required=False, max_length=3000,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Поділіться враженнями'}),
        error_messages={'max_length': 'Коментар задовгий: допустимо до 3000 символів.'})

    class Meta:
        model = Reviews
        fields = ('rating', 'comment')

    def __init__(self, *args, author=None, game=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.author, self.game = author, game

    def clean_comment(self):
        return (self.cleaned_data.get('comment') or '').strip() or None

    def clean(self):
        cleaned = super().clean()
        creating = self.instance.pk is None
        if creating and self.author is not None and self.game is not None \
                and Reviews.objects.filter(id_user=self.author, id_game=self.game).exists():
            raise forms.ValidationError(
                'Ви вже залишили відгук на цю гру. Його можна змінити або видалити, але другого не буде.',
                code='duplicate_review')
        return cleaned


class PickForm(forms.Form):
    max_price = forms.CharField(
        label='Бюджет до', required=False,
        validators=[AmountValidator('Бюджет', '500 або 19,99', '99999999.99', '99 999 999,99',
                                    'Такого бюджету ми не потягнемо.')],
        widget=forms.TextInput(attrs={'inputmode': 'decimal', 'autocomplete': 'off'}))
    max_size = forms.CharField(
        label='Розмір до, ГБ', required=False,
        validators=[AmountValidator('Розмір', '50 або 1,5', '9999.99', '9 999,99 ГБ',
                                    'Таких важких ігор не буває.')],
        widget=forms.TextInput(attrs={'inputmode': 'decimal', 'autocomplete': 'off'}))
    age = forms.ChoiceField(
        label='Вік', required=False,
        error_messages={'invalid_choice': 'Такого вікового рейтингу в каталозі немає — оберіть зі списку.'})
    min_rating = forms.IntegerField(
        label='Оцінка від', required=False, min_value=0, max_value=5,
        error_messages={'invalid': 'Оцінка — ціле число від 1 до 5.',
                        'min_value': 'Оцінка не може бути меншою за 0.',
                        'max_value': 'Максимальна оцінка — 5.'})

    def __init__(self, *args, ages=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['age'].choices = [('', 'Будь-який')] + [(a, a) for a in ages]

    @staticmethod
    def _to_decimal(raw):
        raw = (raw or '').strip()
        return Decimal(raw.replace(',', '.')) if raw else None

    def clean_max_price(self):
        return self._to_decimal(self.cleaned_data['max_price'])

    def clean_max_size(self):
        return self._to_decimal(self.cleaned_data['max_size'])


class CatalogFilterForm(forms.Form):
    price_min = forms.CharField(
        label='Ціна від', required=False,
        validators=[AmountValidator('Мінімальна ціна', '10 або 19,99', '99999999.99', '99 999 999,99',
                                    'Таких цін у каталозі немає.')],
        widget=forms.TextInput(attrs={'inputmode': 'decimal', 'autocomplete': 'off'}))
    price_max = forms.CharField(
        label='до', required=False,
        validators=[AmountValidator('Максимальна ціна', '60 або 59,99', '99999999.99', '99 999 999,99',
                                    'Таких цін у каталозі немає.')],
        widget=forms.TextInput(attrs={'inputmode': 'decimal', 'autocomplete': 'off'}))

    def clean_price_min(self):
        return PickForm._to_decimal(self.cleaned_data['price_min'])

    def clean_price_max(self):
        return PickForm._to_decimal(self.cleaned_data['price_max'])

    def clean(self):
        cleaned = super().clean()
        low, high = cleaned.get('price_min'), cleaned.get('price_max')
        if low is not None and high is not None and low > high:
            self.add_error('price_max', 'Максимальна ціна не може бути меншою за мінімальну — поміняйте їх місцями.')
        return cleaned