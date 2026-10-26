from django.db import migrations

from catalog_game.management.commands.seed_data import MULTIPLAYER_ONLY, SINGLE

DESCRIPTION = 'Гра має режим для одного гравця: сюжетна кампанія або проходження наодинці.'


def add_single_player(apps, schema_editor):
    Games = apps.get_model('catalog_game', 'Games')
    Genre = apps.get_model('catalog_game', 'Genre')
    alias = schema_editor.connection.alias

    genre = Genre.objects.using(alias).filter(name_genre=SINGLE).first()
    if genre is None:
        genre = Genre.objects.using(alias).create(name_genre=SINGLE, descriptions=DESCRIPTION)

    for game in Games.objects.using(alias).exclude(title__in=MULTIPLAYER_ONLY):
        if not game.genres.filter(pk=genre.pk).exists():
            game.genres.add(genre)


class Migration(migrations.Migration):

    dependencies = [
        ('catalog_game', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_single_player, migrations.RunPython.noop),
    ]
