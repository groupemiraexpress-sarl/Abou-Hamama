"""
Donnees de l'en-tete des listes de l'administration : petits chiffres en haut et onglets.

  - chiffres : total, actifs (si le modele a un champ "actif"), nombre d'agences (si le modele a une agence) ;
  - onglets : un par valeur du premier filtre a choix du modele (poste, statut, type...), avec le nombre d'elements.

Tout est calcule sur le queryset de l'administration, donc deja limite a l'entreprise de l'utilisateur.
"""
from django.db.models import BooleanField, Count
from django.utils.translation import gettext_lazy as _


def donnees_liste(modeladmin, request):
    modele = modeladmin.model
    champs = {f.name: f for f in modele._meta.concrete_fields}
    qs = modeladmin.get_queryset(request)
    total = qs.count()

    tuiles = [{'libelle': _("Total"), 'valeur': total}]
    if isinstance(champs.get('actif'), BooleanField):
        tuiles.append({'libelle': _("Actifs"), 'valeur': qs.filter(actif=True).count()})
    agence = champs.get('agence')
    if agence is not None and agence.is_relation:
        tuiles.append({'libelle': _("Agences"), 'valeur': qs.exclude(agence__isnull=True).values('agence').distinct().count()})

    onglets = []
    champ = None
    for filtre in modeladmin.list_filter:
        if isinstance(filtre, str) and filtre in champs and champs[filtre].choices:
            champ = champs[filtre]
            break
    if champ is not None:
        parametre = f"{champ.name}__exact"
        comptes = {ligne[champ.name]: ligne['n'] for ligne in qs.order_by().values(champ.name).annotate(n=Count('pk'))}
        courant = request.GET.get(parametre)
        base = request.GET.copy()
        for cle in (parametre, 'p', 'e'):
            base.pop(cle, None)
        onglets.append({'libelle': _("Tous"), 'n': total, 'url': '?' + base.urlencode(), 'actif': not courant})
        for valeur, libelle in champ.flatchoices:
            if comptes.get(valeur):
                avec = base.copy()
                avec[parametre] = valeur
                onglets.append({'libelle': libelle, 'n': comptes[valeur], 'url': '?' + avec.urlencode(), 'actif': courant == str(valeur)})
        if len(onglets) <= 2:
            onglets = []     # un seul choix : l'onglet n'apprend rien

    return {'total': total, 'tuiles': tuiles, 'onglets': onglets}
