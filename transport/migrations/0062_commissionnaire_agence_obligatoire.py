import django.db.models.deletion
from django.db import migrations, models


def supprimer_sans_agence(apps, schema_editor):
    """Un commissionnaire sans agence n'a pas de compagnie : il serait invisible de tous. (Fonction jamais utilisee en production avant ce changement.)"""
    apps.get_model('transport', 'Commissionnaire').objects.filter(agence__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('transport', '0061_multi_entreprises_obligatoire'),
    ]

    operations = [
        migrations.RunPython(supprimer_sans_agence, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='commissionnaire', name='agence',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, related_name='commissionnaires',
                to='transport.agence', verbose_name='Agence',
            ),
        ),
    ]
