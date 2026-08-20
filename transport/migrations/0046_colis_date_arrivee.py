# Generated manually (pas d'environnement Django local pour lancer makemigrations)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transport', '0045_pushtoken'),
    ]

    operations = [
        migrations.AddField(
            model_name='colis',
            name='date_arrivee',
            field=models.DateTimeField(blank=True, help_text="Renseignee automatiquement quand le colis passe au statut 'Arrive a destination'. Sert de point de depart au delai de 5 jours pour le retrait.", null=True, verbose_name="Date d'arrivee a l'agence"),
        ),
    ]
