# Generated manually (pas d'environnement Django local pour lancer makemigrations)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transport', '0046_colis_date_arrivee'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='alerte_expiration_envoyee',
            field=models.BooleanField(default=False, help_text="Vrai si l'avertissement (2h avant l'annulation automatique) a deja ete envoye", verbose_name="Alerte d'expiration envoyee"),
        ),
        migrations.AddField(
            model_name='demandecolis',
            name='alerte_expiration_envoyee',
            field=models.BooleanField(default=False, help_text="Vrai si l'avertissement (2h avant l'annulation automatique) a deja ete envoye", verbose_name="Alerte d'expiration envoyee"),
        ),
        migrations.AddField(
            model_name='demandetransfert',
            name='alerte_expiration_envoyee',
            field=models.BooleanField(default=False, help_text="Vrai si l'avertissement (2h avant l'annulation automatique) a deja ete envoye", verbose_name="Alerte d'expiration envoyee"),
        ),
        migrations.AddField(
            model_name='colis',
            name='alerte_retrait_envoyee',
            field=models.BooleanField(default=False, help_text="Vrai si l'avertissement (2h avant le retour automatique) a deja ete envoye", verbose_name="Alerte de retrait envoyee"),
        ),
        migrations.AddField(
            model_name='transfertargent',
            name='alerte_retrait_envoyee',
            field=models.BooleanField(default=False, help_text="Vrai si l'avertissement (2h avant l'annulation automatique) a deja ete envoye", verbose_name="Alerte de retrait envoyee"),
        ),
    ]
