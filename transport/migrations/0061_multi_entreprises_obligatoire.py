import django.db.models.deletion
from django.db import migrations, models


def champ_compagnie(related_name):
    return models.ForeignKey(
        on_delete=django.db.models.deletion.PROTECT, related_name=related_name,
        to='transport.compagnie', verbose_name='Compagnie',
    )


class Migration(migrations.Migration):
    """Apres le rattachement des donnees existantes (0060), la compagnie devient obligatoire."""

    dependencies = [
        ('transport', '0060_rattacher_donnees_compagnie'),
    ]

    operations = [
        migrations.AlterField(model_name='client', name='compagnie', field=champ_compagnie('clients')),
        migrations.AlterField(model_name='articlestock', name='compagnie', field=champ_compagnie('articles_stock')),
        migrations.AlterField(model_name='promotion', name='compagnie', field=champ_compagnie('promotions')),
        migrations.AlterField(model_name='questionfaq', name='compagnie', field=champ_compagnie('questions_faq')),
        migrations.AlterField(model_name='plainte', name='compagnie', field=champ_compagnie('plaintes')),
        migrations.AlterField(
            model_name='compagnie', name='code',
            field=models.SlugField(
                help_text="Code court en minuscules (ex : ah). Sert de prefixe aux identifiants des employes et d'adresse web.",
                max_length=20, unique=True, verbose_name='Code',
            ),
        ),
    ]
