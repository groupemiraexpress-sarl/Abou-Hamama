from django.db import migrations
from django.utils.text import slugify


def rattacher(apps, schema_editor):
    """Toutes les donnees existantes appartiennent a la compagnie actuelle (la premiere)."""
    Compagnie = apps.get_model('transport', 'Compagnie')
    # Code court unique pour chaque compagnie (prefixe des identifiants, sous-domaine)
    utilises = set(Compagnie.objects.exclude(code__isnull=True).values_list('code', flat=True))
    for c in Compagnie.objects.filter(code__isnull=True).order_by('id'):
        mots = [m for m in slugify(c.nom).split('-') if m]
        base = (''.join(m[0] for m in mots) if len(mots) >= 2 else (mots[0][:8] if mots else '')) or 'compagnie'
        code, n = base, 1
        while code in utilises:
            n += 1
            code = f"{base}{n}"
        c.code = code
        c.save(update_fields=['code'])
        utilises.add(code)

    principale = Compagnie.objects.order_by('id').first()
    if principale is None:
        return
    for nom in ('Client', 'ArticleStock', 'Promotion', 'QuestionFAQ', 'Plainte'):
        apps.get_model('transport', nom).objects.filter(compagnie__isnull=True).update(compagnie=principale)


class Migration(migrations.Migration):

    dependencies = [
        ('transport', '0059_multi_entreprises_champs'),
    ]

    operations = [
        migrations.RunPython(rattacher, migrations.RunPython.noop),
    ]
