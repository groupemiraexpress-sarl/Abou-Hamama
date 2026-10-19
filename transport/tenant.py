"""
Cloisonnement par ENTREPRISE (compagnie).

Une seule installation sert plusieurs entreprises. Chaque employe appartient a
une compagnie (Employe.compagnie) et ne voit JAMAIS les donnees d'une autre.

  - superutilisateur : administrateur de la plateforme, voit toutes les compagnies ;
  - tout autre compte : limite a la compagnie de sa fiche Employe (aucune fiche
    Employe = aucune donnee) ; le PDG voit toutes les AGENCES de SA compagnie.

CHEMINS_COMPAGNIE donne, pour chaque modele, le chemin de relation qui mene a
sa compagnie. Un modele absent de cette liste n'est visible que du
superutilisateur (c'est voulu : cela ferme l'acces par defaut).
"""
from django.db.models import Q

# modele (label en minuscules) -> chemin(s) de relation vers la compagnie
CHEMINS_COMPAGNIE = {
    'transport.compagnie': ['pk'],
    'transport.agence': ['compagnie'],
    'transport.bus': ['compagnie'],
    'transport.chauffeur': ['compagnie'],
    'transport.trajet': ['compagnie'],
    'transport.employe': ['compagnie'],
    'transport.colis': ['compagnie'],
    'transport.transfertargent': ['compagnie'],
    'transport.ligne': ['compagnie'],
    'transport.arretligne': ['ligne__compagnie'],
    'transport.voyage': ['bus__compagnie'],
    'transport.siege': ['voyage__bus__compagnie'],
    'transport.reservation': ['voyage__bus__compagnie'],
    'transport.client': ['compagnie'],
    'transport.articlestock': ['compagnie'],
    'transport.promotion': ['compagnie'],
    'transport.questionfaq': ['compagnie'],
    'transport.plainte': ['compagnie'],
    'transport.entretien': ['bus__compagnie'],
    'transport.pleincarburant': ['bus__compagnie'],
    'transport.demandemateriel': ['bus__compagnie'],
    'transport.alertevoyage': ['voyage__bus__compagnie'],
    'transport.positionbus': ['voyage__bus__compagnie'],
    'transport.avisvoyage': ['voyage__bus__compagnie'],
    'transport.demandecolis': ['agence_depart__compagnie'],
    'transport.demandetransfert': ['agence_depart__compagnie'],
    'transport.commissionnaire': ['agence__compagnie'],
    'transport.depense': ['voyage__bus__compagnie'],
    'transport.sessioncaisse': ['agence__compagnie'],
    'transport.mouvementcaisse': ['session__agence__compagnie'],
    'transport.factureabonnement': ['compagnie'],
    'transport.paiementabonnement': ['facture__compagnie'],
    # Comptes de connexion : rattaches a une compagnie par leur fiche employe ou client
    'auth.user': ['employe__compagnie', 'fiches_client__compagnie'],
    'transport.pushtoken': ['user__employe__compagnie', 'user__fiches_client__compagnie'],
    'transport.appareilconfirme': ['user__employe__compagnie', 'user__fiches_client__compagnie'],
    'transport.demandeconfirmationappareil': ['user__employe__compagnie', 'user__fiches_client__compagnie'],
}


def compagnie_de(user):
    """Compagnie de l'employe lie a ce compte, ou None (superutilisateur, compte sans fiche employe)."""
    if user is None or not getattr(user, 'is_authenticated', False):
        return None
    if hasattr(user, '_compagnie_cache'):
        return user._compagnie_cache
    employe = getattr(user, 'employe', None)
    user._compagnie_cache = employe.compagnie if employe is not None else None
    return user._compagnie_cache


def limiter_a_compagnie(qs, user, compagnie=None):
    """
    Restreint un queryset a la compagnie de l'utilisateur.
    `compagnie` impose une compagnie precise (pages publiques, API mobile).
    """
    if compagnie is None:
        if user is not None and getattr(user, 'is_superuser', False):
            return qs
        compagnie = compagnie_de(user)
    if compagnie is None:
        return qs.none()
    chemins = CHEMINS_COMPAGNIE.get(qs.model._meta.label_lower)
    if chemins is None:
        return qs.none()
    condition = Q()
    for chemin in chemins:
        condition |= Q(**{chemin: compagnie.pk if chemin == 'pk' else compagnie})
    resultat = qs.filter(condition)
    return resultat.distinct() if len(chemins) > 1 else resultat


def appartient_a_compagnie(obj, user):
    """Vrai si l'objet est dans la compagnie de l'utilisateur (superutilisateur : toujours vrai)."""
    if user.is_superuser:
        return True
    return limiter_a_compagnie(type(obj)._default_manager.filter(pk=obj.pk), user).exists()


def identifiant_employe(compagnie, telephone):
    """Identifiant de connexion par defaut d'un nouvel employe : code de la compagnie + telephone (unique dans tout le logiciel)."""
    return f"{compagnie.code}.{telephone}" if compagnie is not None and compagnie.code else str(telephone)


def portee(user, modele):
    """Tous les objets du modele qui appartiennent a la compagnie de l'utilisateur (superutilisateur : tous)."""
    return limiter_a_compagnie(modele._default_manager.all(), user)


def compagnie_du_domaine(hote):
    """Compagnie reconnue d'apres l'adresse web : domaine propre, ou sous-domaine <code>.<PLATEFORME_DOMAINE>."""
    from django.conf import settings
    from .models import Compagnie
    hote = (hote or '').split(':')[0].strip().lower()
    if not hote:
        return None
    compagnie = Compagnie.objects.filter(domaine=hote, actif=True).first()
    if compagnie is not None:
        return compagnie
    base = (getattr(settings, 'PLATEFORME_DOMAINE', '') or '').strip().lower().strip('.')
    if base and hote.endswith('.' + base):
        etiquette = hote[:-(len(base) + 1)].split('.')[-1]
        return Compagnie.objects.filter(code=etiquette, actif=True).first()
    return None


def compagnie_courante(request):
    """
    Compagnie "affichee" pour cette requete (marque, telephones des recus) :
    celle de l'employe connecte ; sinon celle de l'adresse web ; sinon la premiere compagnie active.
    """
    from .models import Compagnie
    user = getattr(request, 'user', None)
    if user is not None and getattr(user, 'is_authenticated', False) and not user.is_superuser:
        compagnie = compagnie_de(user)
        if compagnie is not None:
            return compagnie
    compagnie = getattr(request, 'compagnie_domaine', None)
    if compagnie is not None:
        return compagnie
    actives = list(Compagnie.objects.filter(actif=True).order_by('id')[:2])
    # Adresse non reconnue alors que plusieurs compagnies existent : marque neutre (None), pour ne
    # montrer le nom ni le logo d'une compagnie a l'employe d'une autre (ex : ecran de connexion).
    return actives[0] if len(actives) == 1 else None
