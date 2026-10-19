from django.db import migrations


def reprendre_la_marque(apps, schema_editor):
    """Les textes de marque (avant : fichier branding.py) passent dans la fiche de chaque compagnie existante."""
    Compagnie = apps.get_model('transport', 'Compagnie')
    for c in Compagnie.objects.all():
        if not c.pied_de_page:
            c.pied_de_page = f"Agence {c.nom}"
        if not c.nom_affiche and c.nom.strip().lower() == 'abou hamama':
            c.nom_affiche = 'Express Abou Hamama'
        c.save(update_fields=['pied_de_page', 'nom_affiche'])


class Migration(migrations.Migration):

    dependencies = [
        ('transport', '0065_compagnie_marque'),
    ]

    operations = [
        migrations.RunPython(reprendre_la_marque, migrations.RunPython.noop),
    ]
