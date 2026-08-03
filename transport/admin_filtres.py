"""
Cloisonnement par agence et par employe pour l'admin Express Abou Hamama.

Regle generale :
  - superutilisateur / poste 'pdg'      -> voit tout
  - postes "siege" (comptable, rh,
    maintenance, planning)              -> voient tout, toutes agences
  - roles de terrain (guichetier,
    agent colis, agent transfert)       -> voient uniquement ce qu'ils
                                            ont personnellement cree
  - les autres employes avec une agence -> voient tout ce qui se passe
                                            dans leur agence
  - employe sans agence                 -> ne voit rien
"""
from django.db.models import Q
from django.contrib import admin

# Postes qui ne voient que ce qu'ils ont eux-memes enregistre
POSTES_PERSONNEL = ('guichetier', 'agent_colis', 'agent_transfert')

# Postes "siege" : un seul titulaire pour toute la compagnie, voient tout
POSTES_SIEGE = ('comptable', 'rh', 'resp_maintenance', 'resp_planning')


def agence_de(user):
    """Retourne l'agence de l'employe lie a ce compte, ou None."""
    employe = getattr(user, 'employe', None)
    if employe is None:
        return None
    return employe.agence


def voit_tout(user):
    """Vrai si l'utilisateur doit voir toutes les agences."""
    if user.is_superuser:
        return True
    employe = getattr(user, 'employe', None)
    if employe is not None and employe.poste in ('pdg',) + POSTES_SIEGE:
        return True
    return False


class FiltreAgenceMixin:
    """
    Mixin a ajouter aux ModelAdmin pour filtrer par agence et/ou par createur.

    champs_agence = ['agence']  ou  ['agence_depart', 'agence_arrivee']

    champ_createur : nom du champ FK vers Employe qui a cree l'objet
      (ex: 'cree_par'). Mettre None si le modele n'a pas cette notion
      -> dans ce cas le filtre par agence s'applique toujours,
      quel que soit le poste.
    """
    champs_agence = []
    champ_createur = 'cree_par'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user

        if voit_tout(user):
            return qs

        employe = getattr(user, 'employe', None)
        agence = agence_de(user)
        if agence is None:
            return qs.none()

        poste = employe.poste if employe else None

        if self.champ_createur and poste in POSTES_PERSONNEL:
            return qs.filter(**{self.champ_createur: employe})

        if not self.champs_agence:
            return qs
        condition = Q()
        for champ in self.champs_agence:
            condition |= Q(**{champ: agence})
        return qs.filter(condition)


class FiltreAgenceListFilter(admin.SimpleListFilter):
    """
    Filtre 'Agence' personnalise : ne propose que les agences
    que l'utilisateur a le droit de voir (au lieu de toutes les agences).
    A utiliser dans list_filter a la place du nom de champ brut 'agence'.
    """
    title = 'agence'
    parameter_name = 'agence_id'

    def lookups(self, request, model_admin):
        from .models import Agence
        if voit_tout(request.user):
            agences = Agence.objects.filter(actif=True).order_by('ville', 'nom')
        else:
            agence = agence_de(request.user)
            agences = Agence.objects.filter(id=agence.id) if agence else Agence.objects.none()
        return [(a.id, str(a)) for a in agences]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(agence_id=self.value())
        return queryset