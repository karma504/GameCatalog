import re
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

MAX_AGE_YEARS = 120     # відсікає явно вигадані дати


def min_age_years():
    return max(int(getattr(settings, 'MIN_REGISTRATION_AGE', 0)), 0)


class PasswordCharTypesValidator:

    def validate(self, password, user=None):
        if password.isdigit():
            raise ValidationError(
                'Пароль не може складатися лише з цифр.',
                code='only_digits'
            )

        if password.isalpha():
            raise ValidationError(
                'Пароль не може складатися лише з літер.',
                code='only_letters'
            )

        if not any(ch.isalnum() for ch in password):
            raise ValidationError(
                'Пароль не може складатися лише зі спеціальних символів.',
                code='only_symbols'
            )

    def get_help_text(self):
        return ''


class AmountValidator:

    _plain = re.compile(r'[0-9]+(?:[.,][0-9]+)?')
    _negative = re.compile(r'-\s*[0-9]+(?:[.,][0-9]+)?')

    def __init__(self, subject, example, max_value, max_label, too_big_text):
        self.subject = subject
        self.example = example
        self.max_value = Decimal(max_value)
        self.max_label = max_label
        self.too_big_text = too_big_text

    def __call__(self, value):
        raw = (value or '').strip()
        if not raw:
            return
        if self._negative.fullmatch(raw):
            raise ValidationError(
                f'{self.subject} не може бути від’ємним. Введіть 0 або більше.',
                code='negative')
        if not self._plain.fullmatch(raw):
            raise ValidationError(
                f'{self.subject} — це число, наприклад {self.example}. '
                'Літери, пробіли та зайві символи сюди не підійдуть.',
                code='not_a_number')
        number = raw.replace(',', '.')
        if len(number.partition('.')[2]) > 2:
            raise ValidationError(
                'Після коми потрібно не більше двох цифр, наприклад 19,99.',
                code='too_precise')
        if Decimal(number) > self.max_value:
            raise ValidationError(
                f'{self.too_big_text} Максимум — {self.max_label}.',
                code='too_big')

    def __eq__(self, other):
        return isinstance(other, AmountValidator) and self.__dict__ == other.__dict__

    def deconstruct(self):
        return ('catalog_game.validators.AmountValidator', (), {
            'subject': self.subject, 'example': self.example,
            'max_value': str(self.max_value), 'max_label': self.max_label,
            'too_big_text': self.too_big_text})


def validate_http_url(value):

    value = (value or '').strip()
    if value and not value.lower().startswith(('http://', 'https://')):
        raise ValidationError(
            'Посилання має починатися з http:// або https://.',
            code='bad_scheme')


def _years_ago(today, years):

    try:
        return today.replace(year=today.year - years)
    except ValueError:
        return today.replace(year=today.year - years, day=28)


def latest_birth_date(today=None):

    return _years_ago(today or timezone.localdate(), min_age_years())


def validate_birth_date(value):

    if value is None:
        return
    today = timezone.localdate()
    if value > today:
        raise ValidationError('Дата народження не може бути в майбутньому.', code='future')
    if value > latest_birth_date(today):
        minimum = min_age_years()
        raise ValidationError(
            f'Реєстрація доступна з {minimum} років: за вказаною датою вам ще немає {minimum}.',
            code='too_young')
    if value < _years_ago(today, MAX_AGE_YEARS):
        raise ValidationError('Вкажіть справжню дату народження.', code='too_old')
