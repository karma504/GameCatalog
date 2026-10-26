from django import template

register = template.Library()


@register.simple_tag
def display_name(user):
    return (getattr(user, 'firstname', '') or '').strip() or 'Користувач'


@register.inclusion_tag('catalog_game/_stars.html')
def rating_stars(value):
    try:
        value = int(round(float(value)))
    except (TypeError, ValueError):
        value = 0
    return {'stars': ['★' if i < value else '☆' for i in range(5)]}


@register.inclusion_tag('catalog_game/_wish_button.html', takes_context=True)
def wish_button(context, game):
    from catalog_game.models import Wishlist

    request = context['request']
    user = request.user
    on = False
    if user.is_authenticated:
        ids = getattr(request, '_wish_ids', None)
        if ids is None:
            ids = request._wish_ids = set(Wishlist.objects.filter(id_user=user).values_list('id_game_id', flat=True))
        on = game.pk in ids
    return {'game': game, 'on': on, 'user': user, 'next': request.get_full_path(),
            'csrf_token': context.get('csrf_token')}
