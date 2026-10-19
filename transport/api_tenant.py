"""
Entreprise (compagnie) d'un appel de l'API mobile.

L'application indique la compagnie choisie par le voyageur dans l'en-tete HTTP
`X-Compagnie: <code>` (ou le parametre `?compagnie=<code>`). Sans indication, on
prend la premiere compagnie active : cela garde les anciennes versions de
l'application, faites pour une seule compagnie, en etat de marche.

Un voyageur a UN compte (Django User) et UNE fiche Client par compagnie qu'il a
rejointe. Toutes les donnees (billets, colis, transferts, plaintes...) sont
rattachees a la fiche, donc a une seule compagnie : une compagnie ne voit jamais
ce que le voyageur fait chez une autre.
"""
from rest_framework.response import Response

from .models import Client, Compagnie


def compagnie_requete(request):
    """Compagnie demandee par l'appel (None si le code est inconnu ou la compagnie inactive)."""
    code = (request.META.get('HTTP_X_COMPAGNIE') or request.GET.get('compagnie') or '').strip().lower()
    if code:
        return Compagnie.objects.filter(code=code, actif=True).first()
    domaine = getattr(request, 'compagnie_domaine', None)
    if domaine is not None:
        return domaine
    return Compagnie.objects.filter(actif=True).order_by('id').first()


def reponse_compagnie_inconnue():
    return Response({'erreur': 'Compagnie introuvable.'}, status=404)


def fiche_client(request):
    """Fiche client du compte connecte dans la compagnie de l'appel (None s'il ne l'a pas rejointe)."""
    compagnie = compagnie_requete(request)
    if compagnie is None or not request.user.is_authenticated:
        return None
    return Client.objects.filter(user=request.user, compagnie=compagnie).first()


def fiche_client_ou_creer(request, nom=''):
    """
    Fiche du compte dans la compagnie de l'appel ; elle est creee (le voyageur "rejoint"
    la compagnie en y reservant) a partir des informations de son compte et de ses autres fiches.
    Renvoie None si la compagnie est inconnue.
    """
    compagnie = compagnie_requete(request)
    if compagnie is None:
        return None
    user = request.user
    fiche = Client.objects.filter(user=user, compagnie=compagnie).first()
    if fiche:
        return fiche
    modele = Client.objects.filter(user=user).exclude(telephone__startswith='compte-').order_by('id').first()
    telephone = modele.telephone if modele else ''
    # le numero est unique dans une compagnie : s'il est deja pris la-bas, on garde un identifiant provisoire
    if not telephone or Client.objects.filter(compagnie=compagnie, telephone=telephone).exists():
        telephone = 'compte-' + str(user.id)
    return Client.objects.create(
        compagnie=compagnie, user=user, telephone=telephone, email=user.email,
        nom=nom or (modele.nom if modele else '') or user.username,
        prenom=modele.prenom if modele else '',
    )


def compagnies_du_compte(user):
    """Compagnies que ce compte a rejointes : [{'code', 'nom'}]."""
    fiches = Client.objects.filter(user=user, compagnie__actif=True).select_related('compagnie').order_by('compagnie__nom')
    return [{'code': f.compagnie.code, 'nom': f.compagnie.nom} for f in fiches]
