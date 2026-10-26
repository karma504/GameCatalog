from django.conf import settings
from django.utils import timezone

ADULT_AGE = 18


def calculate_age(birth_date, today=None):

    if birth_date is None:
        return None
    today = today or timezone.localdate()
    years = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        years -= 1
    return max(years, 0)


def rating_to_int(code):
    if not isinstance(code, str):
        return None
    number = code.strip().rstrip('+')
    return int(number) if number.isdigit() else None


def guest_age():
    value = getattr(settings, 'GUEST_AGE_LIMIT', None)
    if value is None:
        return None
    return max(int(value), 0)


def user_age(user):
    if user is not None and getattr(user, 'is_authenticated', False):
        age = calculate_age(getattr(user, 'date_of_birth', None))
        if age is not None:
            return age
    return guest_age()


def allowed_ratings(age, choices):
    if age is None:
        return [code for code, _label in choices]
    result = []
    for code, _label in choices:
        number = rating_to_int(code)
        if number is not None and number <= age:
            result.append(code)
    return result


def can_see_unrated(age):
    return age is None or age >= ADULT_AGE
