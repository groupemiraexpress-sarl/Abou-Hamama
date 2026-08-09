"""
Cloisonnement par agence, par zone et par employe pour l'admin Express Abou Hamama.

Regle generale :
  - superutilisateur / poste 'pdg'      -> voit tout
  - postes "siege" (comptable, rh,
    maintenance)                        -> voient tout, toutes agences
  - poste 'resp_planning'               -> voit sa zone (Nord ou Sud),
                                            toutes les agences de cette zone
  - roles de terrain (guichetier,
    agent colis, agent transfert)       -> voient uniquement ce qu'ils
                                            ont personnellement cree
  - les autres employes avec une agence -> voient tout ce qui se passe
                                            dans leur agence
  - employe sans agence ni zone         -> ne voit rien

Ce fichier gere le perimetre des DONNEES (quelles lignes en base un
employe peut voir). Le perimetre de l'INTERFACE du tableau de bord
(quelles cartes/raccourcis/groupes de modeles s'affichent sur la page
d'accueil de l'admin) est gere plus bas par profil_tableau_bord(), qui
est une notion volontairement separee : un comptable voit TOUTES les
donnees financieres (voit_tout=True) mais ne voit QUE les cartes
financieres sur le tableau de bord.
"""
from django.db.models import Q
from django.contrib import admin

# Postes qui ne voient que ce qu'ils ont eux-memes enregistre
POSTES_PERSONNEL = ('guichetier', 'agent_colis', 'agent_transfert')

# Postes "siege" : un seul titulaire pour toute la compagnie, voient tout
POSTES_SIEGE = ('comptable', 'rh', 'resp_maintenance')


def agence_de(user):
    """Retourne l'agence de l'employe lie a ce compte, ou None."""
    employe = getattr(user, 'employe', None)
    if employe is None:
        return None
    return employe.agence


def zone_de(user):
    """Retourne la zone geree par l'employe (Responsable planning), ou None."""
    employe = getattr(user, 'employe', None)
    if employe is None:
        return None
    return employe.zone or None


def voit_tout(user):
    """Vrai si l'utilisateur doit voir toutes les agences (toutes zones)."""
    if user.is_superuser:
        return True
    employe = getattr(user, 'employe', None)
    if employe is not None and employe.poste in ('pdg',) + POSTES_SIEGE:
        return True
    return False


class FiltreAgenceMixin:
    """
    Mixin a ajouter aux ModelAdmin pour filtrer par agence, zone et/ou par createur.

    champs_agence = ['agence']  ou  ['agence_depart', 'agence_arrivee']

    champ_createur : nom du champ FK vers Employe qui a cree l'objet
      (ex: 'cree_par'). Mettre None si le modele n'a pas cette notion.
    """
    champs_agence = []
    champ_createur = 'cree_par'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user

        if voit_tout(user):
            return qs

        employe = getattr(user, 'employe', None)
        poste = employe.poste if employe else None

        # Responsable planning : voit toutes les agences de sa zone
        if poste == 'resp_planning':
            zone = zone_de(user)
            if not zone or not self.champs_agence:
                return qs.none()
            condition = Q()
            for champ in self.champs_agence:
                condition |= Q(**{f"{champ}__zone": zone})
            return qs.filter(condition)

        agence = agence_de(user)
        if agence is None:
            return qs.none()

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
    """
    title = 'agence'
    parameter_name = 'agence_id'

    def lookups(self, request, model_admin):
        from .models import Agence
        if voit_tout(request.user):
            agences = Agence.objects.filter(actif=True).order_by('ville', 'nom')
        else:
            employe = getattr(request.user, 'employe', None)
            poste = employe.poste if employe else None
            if poste == 'resp_planning':
                zone = zone_de(request.user)
                agences = Agence.objects.filter(actif=True, zone=zone).order_by('ville', 'nom') if zone else Agence.objects.none()
            else:
                agence = agence_de(request.user)
                agences = Agence.objects.filter(id=agence.id) if agence else Agence.objects.none()
        return [(a.id, str(a)) for a in agences]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(agence_id=self.value())
        return queryset


# ---------------------------------------------------------------------------
# Profil d'affichage du tableau de bord (page d'accueil de l'admin)
# ---------------------------------------------------------------------------
# Independant du perimetre des donnees ci-dessus : decide uniquement quelles
# cartes de stats, quel raccourci de vente et quels groupes de modeles
# apparaissent sur la page d'accueil, selon le poste de l'employe connecte.

# Tous les drapeaux possibles. Chaque cle correspond soit a une carte de
# stats (meme nom que dans statistiques_tableau_bord), soit a un groupe de
# modeles, soit au raccourci de vente rapide.
DRAPEAUX_TABLEAU_BORD = [
    'voit_raccourci_vente',
    'voit_voyages_aujourd_hui', 'voit_reservations_jour', 'voit_recette_jour', 'voit_voyages_a_venir',
    'voit_alertes_non_resolues', 'voit_demandes_colis_attente', 'voit_demandes_transfert_attente',
    'voit_reservations_attente', 'voit_transferts_attente',
    'voit_colis_transit', 'voit_colis_arrives', 'voit_bus_service', 'voit_bus_maintenance',
    'voit_total_clients', 'voit_total_employes',
    'voit_groupe_exploitation', 'voit_groupe_securite', 'voit_groupe_colis_transferts',
    'voit_groupe_clients_personnel', 'voit_groupe_maintenance', 'voit_groupe_configuration',
]

# Pour chaque poste (hors PDG/superuser, qui voient tout automatiquement),
# l'ensemble des drapeaux actives sur le tableau de bord.
PROFILS_TABLEAU_BORD = {
    'responsable': {
        'voit_raccourci_vente',
        'voit_voyages_aujourd_hui', 'voit_reservations_jour', 'voit_recette_jour', 'voit_voyages_a_venir',
        'voit_alertes_non_resolues', 'voit_demandes_colis_attente', 'voit_demandes_transfert_attente',
        'voit_reservations_attente', 'voit_transferts_attente',
        'voit_colis_transit', 'voit_colis_arrives', 'voit_bus_service', 'voit_bus_maintenance', 'voit_total_clients',
        'voit_groupe_exploitation', 'voit_groupe_securite', 'voit_groupe_colis_transferts',
        'voit_groupe_clients_personnel', 'voit_groupe_maintenance',
    },
    'secretaire': {
        'voit_raccourci_vente',
        'voit_voyages_aujourd_hui', 'voit_reservations_jour', 'voit_voyages_a_venir', 'voit_reservations_attente',
        'voit_demandes_colis_attente', 'voit_demandes_transfert_attente',
        'voit_colis_transit', 'voit_colis_arrives',
        'voit_groupe_exploitation', 'voit_groupe_colis_transferts',
    },
    'resp_planning': {
        'voit_voyages_aujourd_hui', 'voit_voyages_a_venir', 'voit_reservations_jour', 'voit_reservations_attente',
        'voit_bus_service', 'voit_bus_maintenance',
        'voit_groupe_exploitation',
    },
    'guichetier': {
        'voit_raccourci_vente', 'voit_reservations_jour', 'voit_reservations_attente',
    },
    'caissier': {
        'voit_raccourci_vente', 'voit_reservations_jour', 'voit_recette_jour', 'voit_reservations_attente',
    },
    'agent_colis': {
        'voit_demandes_colis_attente', 'voit_colis_transit', 'voit_colis_arrives', 'voit_groupe_colis_transferts',
    },
    'agent_transfert': {
        'voit_demandes_transfert_attente', 'voit_transferts_attente', 'voit_groupe_colis_transferts',
    },
    'manutentionnaire': {
        'voit_colis_transit', 'voit_colis_arrives',
    },
    'comptable': {
        'voit_recette_jour', 'voit_reservations_attente', 'voit_transferts_attente',
    },
    'rh': {
        'voit_total_employes', 'voit_groupe_clients_personnel',
    },
    'resp_maintenance': {
        'voit_bus_service', 'voit_bus_maintenance', 'voit_groupe_maintenance',
    },
    'securite': {
        'voit_alertes_non_resolues', 'voit_groupe_securite',
    },
    'autre': set(),
}


def _est_pdg_ou_superuser(user):
    """Vrai uniquement pour le PDG et le superutilisateur (acces complet a l'interface)."""
    if user is None or user.is_superuser:
        return True
    employe = getattr(user, 'employe', None)
    return employe is not None and employe.poste == 'pdg'


def profil_tableau_bord(user):
    """
    Determine quelles cartes de stats, raccourcis et groupes de modeles
    sont affiches sur la page d'accueil de l'admin, selon le poste.

    Renvoie un dict {drapeau: bool} a utiliser dans le template avec
    {% if stats_profil.voit_xxx %}.
    """
    if _est_pdg_ou_superuser(user):
        return {drapeau: True for drapeau in DRAPEAUX_TABLEAU_BORD}

    employe = getattr(user, 'employe', None)
    poste = employe.poste if employe else None
    actifs = PROFILS_TABLEAU_BORD.get(poste, set())

    return {drapeau: (drapeau in actifs) for drapeau in DRAPEAUX_TABLEAU_BORD}