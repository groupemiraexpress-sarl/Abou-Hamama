"""
Cloisonnement par agence pour l'admin Express Abou Hamama.

Regle generale :
  - superutilisateur      -> voit tout
  - poste 'pdg'           -> voit tout
  - employe avec agence   -> voit uniquement les operations de son agence
  - employe sans agence   -> ne voit rien
"""

from django.db.models import Q


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
    if employe is not None and employe.poste == 'pdg':
        return True
    return False


class FiltreAgenceMixin:
    """
    Mixin a ajouter aux ModelAdmin pour filtrer par agence.

    Definir 'champs_agence' dans la classe :
      champs_agence = ['agence']                        (un seul champ)
      champs_agence = ['agence_depart', 'agence_arrivee']  (plusieurs)
    """

    champs_agence = []

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if voit_tout(request.user):
            return qs

        agence = agence_de(request.user)
        if agence is None:
            return qs.none()

        if not self.champs_agence:
            return qs

        condition = Q()
        for champ in self.champs_agence:
            condition |= Q(**{champ: agence})
        return qs.filter(condition)
