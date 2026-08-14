import random

from django.db import migrations


def generer_codes_retrait(apps, schema_editor):
    Colis = apps.get_model('transport', 'Colis')
    for colis in Colis.objects.filter(code_retrait=''):
        colis.code_retrait = str(random.randint(10000, 99999))
        colis.save(update_fields=['code_retrait'])


def revenir_en_arriere(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('transport', '0043_colis_code_retrait'),
    ]

    operations = [
        migrations.RunPython(generer_codes_retrait, revenir_en_arriere),
    ]
