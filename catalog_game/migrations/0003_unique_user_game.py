from django.db import migrations, models
from django.db.models import Count

CONSTRAINTS = {'Reviews': 'uq_reviews_user_game', 'Wishlist': 'uq_wishlist_user_game'}


def add_unique_keys(apps, schema_editor):
    connection = schema_editor.connection
    for model_name, name in CONSTRAINTS.items():
        Model = apps.get_model('catalog_game', model_name)
        with connection.cursor() as cursor:
            existing = connection.introspection.get_constraints(cursor, Model._meta.db_table)
        if name in existing or any(c['unique'] and c['columns'] == ['id_user', 'id_game'] for c in existing.values()):
            continue
        duplicates = (Model.objects.using(connection.alias).values('id_user', 'id_game')
                      .annotate(n=Count('pk')).filter(n__gt=1).exists())
        if duplicates:
            continue
        schema_editor.add_constraint(Model, models.UniqueConstraint(fields=['id_user', 'id_game'], name=name))


class Migration(migrations.Migration):

    dependencies = [
        ('catalog_game', '0002_single_player_genre'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='reviews',
            constraint=models.UniqueConstraint(fields=('id_user', 'id_game'), name='uq_reviews_user_game')),
        migrations.AddConstraint(
            model_name='wishlist',
            constraint=models.UniqueConstraint(fields=('id_user', 'id_game'), name='uq_wishlist_user_game')),
        migrations.RunPython(add_unique_keys, migrations.RunPython.noop),
    ]
