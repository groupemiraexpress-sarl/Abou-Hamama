"""
Cloisonnement par agence et par employe pour l'admin Express Abou Hamama.

Philosophie generale : chaque agence est une unite autonome avec son propre
personnel complet (responsable, secretaire, guichetier, caissier, agent
colis, agent transfert, manutentionnaire, comptable, RH, responsable
maintenance, agent de securite...). Un employe ne voit et ne gere QUE les
donnees de sa propre agence, quel que soit son poste.

Deux exceptions seulement :
  - le PDG (et le superutilisateur) voient et gerent TOUTE la compagnie,
    toutes agences confondues. Un seul compte PDG existe dans le logiciel
    (contrainte appliquee dans EmployeAdminForm).
  - le Responsable planning (poste 'resp_planning') supervise une zone
    entiere (Nord ou Sud) regroupant plusieurs agences ; il n'a pas
    d'agence propre mais une zone.

Regle generale :
  - superutilisateur / poste 'pdg'      -> voit tout, toutes agences
  - poste 'resp_planning'               -> voit sa zone (Nord ou Sud),
                                            toutes les agences de cette zone
  - roles de terrain (guichetier,
    agent colis, agent transfert)       -> voient uniquement ce qu'ils
                                            ont personnellement cree,
                                            dans leur agence
  - tous les autres postes (responsable, secretaire, caissier,
    manutentionnaire, comptable, rh, resp_maintenance, securite, autre)
                                         -> voient tout ce qui se passe
                                            dans leur propre agence,
                                            et seulement leur agence
  - employe sans agence ni zone         -> ne voit rien

Ce fichier gere le perimetre des DONNEES (quelles lignes en base un
employe peut voir) via FiltreAgenceMixin, et les permissions FINES via
les has_*_permission personnalises sur chaque ModelAdmin dans admin.py.

IMPORTANT : un compte non-superuser doit d'abord avoir la permission
Django "view"/"change" sur un modele pour meme apparaitre dans le menu
de l'admin - sans elle, il ne voit RIEN, quel que soit son poste. Cette
permission de base est accordee via les 14 groupes Django deja crees
manuellement (un par poste : "Guichetier / billettiste", "Comptable",
"Responsable d'agence", etc. - voir Groupes dans l'admin). La fonction
assigner_groupe_selon_poste() plus bas met automatiquement chaque nouvel
employe dans le bon groupe selon son poste.
"""
from django.db.models import Q
from django.contrib import admin

# Postes qui ne voient que ce qu'ils ont eux-memes enregistre (dans leur agence)
POSTES_PERSONNEL = ('guichetier', 'agent_colis', 'agent_transfert')

# Postes autorises a recruter (creer/modifier des fiches Employe et Chauffeur),
# au sein de leur propre agence uniquement.
POSTES_RECRUTEURS = ('responsable', 'rh')

# Postes qu'un Responsable ou un RH d'agence peuvent attribuer a un nouvel
# employe. N'inclut pas 'pdg' (compte unique, reserve au PDG lui-meme),
# ni 'responsable' ni 'resp_planning' (nominations reservees au PDG).
POSTES_RECRUTABLES_PAR_AGENCE = (
    'secretaire', 'guichetier', 'caissier', 'agent_colis', 'agent_transfert',
    'manutentionnaire', 'comptable', 'resp_maintenance', 'securite', 'rh', 'autre',
)

# Correspondance exacte poste -> nom du groupe Django deja cree manuellement
# (Groupes > ...), avec les permissions precises pour ce metier. Les noms
# des groupes ne correspondent pas toujours mot pour mot au libelle du
# champ Poste (ex: "PDG / Direction" vs "PDG / Directeur general"), d'ou
# cette table de correspondance explicite plutot qu'une simple comparaison
# de texte.
POSTE_VERS_GROUPE = {
    'pdg': 'PDG / Direction',
    'responsable': "Responsable d'agence",
    'secretaire': "Secretaire d'agence",
    'resp_planning': 'Responsable planning',
    'guichetier': 'Guichetier / billettiste',
    'caissier': 'Caissier',
    'agent_colis': 'Agent colis',
    'agent_transfert': "Agent transfert d'argent",
    'manutentionnaire': 'Manutentionnaire / bagagiste',
    'comptable': 'Comptable',
    'rh': 'Responsable RH',
    'resp_maintenance': 'Responsable maintenance',
    'securite': 'Agent de securite',
    'autre': 'Autre (lecture seule)',
}


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
    """
    Vrai uniquement pour le PDG et le superutilisateur : ce sont les
    seuls a voir toutes les agences. Tous les autres postes, y compris
    comptable/RH/responsable maintenance, sont desormais cantonnes a
    leur propre agence (voir docstring du module).
    """
    if user.is_superuser:
        return True
    employe = getattr(user, 'employe', None)
    return employe is not None and employe.poste == 'pdg'


def est_recruteur(user):
    """Vrai si l'utilisateur peut creer/gerer des fiches employe ou chauffeur dans sa propre agence."""
    if voit_tout(user):
        return True
    employe = getattr(user, 'employe', None)
    return employe is not None and employe.poste in POSTES_RECRUTEURS


def assigner_groupe_selon_poste(user, poste):
    """
    Ajoute l'utilisateur au groupe Django deja configure pour son poste
    (avec les permissions precises adaptees a ce metier). Retire au passage
    tout autre groupe "poste" qu'il aurait pu avoir avant (utile en cas de
    changement de poste), pour eviter les cumuls de permissions.

    Ne fait rien (sans erreur) si aucun groupe Django n'existe pour ce
    poste - le compte reste alors sans acces tant que le groupe n'est pas
    cree manuellement dans Groupes > Ajouter un groupe.
    """
    from django.contrib.auth.models import Group

    noms_groupes_postes = set(POSTE_VERS_GROUPE.values())
    nom_groupe = POSTE_VERS_GROUPE.get(poste)

    # Retire les anciens groupes "poste" (utile si l'employe change de role)
    for groupe in user.groups.filter(name__in=noms_groupes_postes):
        user.groups.remove(groupe)

    if not nom_groupe:
        return
    try:
        groupe = Group.objects.get(name=nom_groupe)
        user.groups.add(groupe)
    except Group.DoesNotExist:
        pass


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


class FiltreAgenceMultiListFilter(admin.SimpleListFilter):
    """
    Variante de FiltreAgenceListFilter pour les modeles qui ont PLUSIEURS
    champs agence (ex: agence_depart + agence_arrivee, ou agence_depart +
    agence_retrait) au lieu d'un seul champ 'agence'.

    A utiliser via une sous-classe qui definit `champs_agence`, ex :

        class FiltreAgenceDepartArrivee(FiltreAgenceMultiListFilter):
            champs_agence = ['agence_depart', 'agence_arrivee']

    Le menu deroulant ne propose que l'agence (ou la zone, ou toutes)
    que l'utilisateur a le droit de voir - jamais la liste complete pour
    un responsable d'agence. Quand une agence est choisie, le filtre
    applique un OU logique sur tous les champs_agence (une ligne est
    incluse si CETTE agence est soit le depart, soit l'arrivee/retrait).
    """
    title = 'agence'
    parameter_name = 'agence_id'
    champs_agence = []

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
            condition = Q()
            for champ in self.champs_agence:
                condition |= Q(**{champ: self.value()})
            return queryset.filter(condition)
        return queryset


class FiltreAgenceDepartArrivee(FiltreAgenceMultiListFilter):
    """Pour les modeles avec agence_depart + agence_arrivee (Colis, DemandeColis)."""
    champs_agence = ['agence_depart', 'agence_arrivee']


class FiltreAgenceDepartRetrait(FiltreAgenceMultiListFilter):
    """Pour les modeles avec agence_depart + agence_retrait (DemandeTransfert, TransfertArgent)."""
    champs_agence = ['agence_depart', 'agence_retrait']


# ---------------------------------------------------------------------------
# Profil d'affichage du tableau de bord (page d'accueil de l'admin)
# ---------------------------------------------------------------------------
# Independant du perimetre des donnees ci-dessus : decide uniquement quelles
# cartes de stats, quel raccourci de vente et quels groupes de modeles
# apparaissent sur la page d'accueil, selon le poste de l'employe connecte.

DRAPEAUX_TABLEAU_BORD = [
    'voit_raccourci_vente', 'voit_historique_employe',
    'voit_voyages_aujourd_hui', 'voit_reservations_jour', 'voit_recette_jour', 'voit_voyages_a_venir',
    'voit_alertes_non_resolues', 'voit_demandes_colis_attente', 'voit_demandes_transfert_attente',
    'voit_reservations_attente', 'voit_transferts_attente', 'voit_permis_a_renouveler',
    'voit_colis_transit', 'voit_colis_arrives', 'voit_colis_livres_jour', 'voit_transferts_retires_jour',
    'voit_bus_service', 'voit_bus_maintenance',
    'voit_total_clients', 'voit_total_employes',
    'voit_groupe_exploitation', 'voit_groupe_securite', 'voit_groupe_colis_transferts',
    'voit_groupe_clients_personnel', 'voit_groupe_maintenance', 'voit_groupe_configuration',
]

# Pour chaque poste (hors PDG/superuser, qui voient tout automatiquement),
# l'ensemble des drapeaux actives sur le tableau de bord.
PROFILS_TABLEAU_BORD = {
    'responsable': {
        'voit_raccourci_vente', 'voit_historique_employe',
        'voit_voyages_aujourd_hui', 'voit_reservations_jour', 'voit_recette_jour', 'voit_voyages_a_venir',
        'voit_alertes_non_resolues', 'voit_demandes_colis_attente', 'voit_demandes_transfert_attente',
        'voit_reservations_attente', 'voit_transferts_attente', 'voit_permis_a_renouveler',
        'voit_colis_transit', 'voit_colis_arrives', 'voit_colis_livres_jour', 'voit_transferts_retires_jour',
        'voit_bus_service', 'voit_bus_maintenance', 'voit_total_clients',
        'voit_groupe_exploitation', 'voit_groupe_securite', 'voit_groupe_colis_transferts',
        'voit_groupe_clients_personnel', 'voit_groupe_maintenance',
    },
    'secretaire': {
        'voit_raccourci_vente', 'voit_historique_employe',
        'voit_voyages_aujourd_hui', 'voit_reservations_jour', 'voit_voyages_a_venir', 'voit_reservations_attente',
        'voit_demandes_colis_attente', 'voit_demandes_transfert_attente',
        'voit_colis_transit', 'voit_colis_arrives', 'voit_colis_livres_jour', 'voit_transferts_retires_jour',
        'voit_groupe_exploitation', 'voit_groupe_colis_transferts',
    },
    'resp_planning': {
        'voit_voyages_aujourd_hui', 'voit_voyages_a_venir', 'voit_reservations_jour', 'voit_reservations_attente',
        'voit_bus_service', 'voit_bus_maintenance', 'voit_permis_a_renouveler',
        'voit_groupe_exploitation',
    },
    'guichetier': {
        'voit_raccourci_vente', 'voit_historique_employe', 'voit_reservations_jour', 'voit_reservations_attente',
    },
    'caissier': {
        'voit_raccourci_vente', 'voit_historique_employe', 'voit_reservations_jour', 'voit_recette_jour', 'voit_reservations_attente',
    },
    'agent_colis': {
        'voit_historique_employe',
        'voit_demandes_colis_attente', 'voit_colis_transit', 'voit_colis_arrives', 'voit_colis_livres_jour', 'voit_groupe_colis_transferts',
    },
    'agent_transfert': {
        'voit_historique_employe',
        'voit_demandes_transfert_attente', 'voit_transferts_attente', 'voit_transferts_retires_jour', 'voit_groupe_colis_transferts',
    },
    'manutentionnaire': {
        'voit_historique_employe', 'voit_colis_transit', 'voit_colis_arrives',
    },
    'comptable': {
        'voit_historique_employe',
        'voit_recette_jour', 'voit_reservations_attente', 'voit_transferts_attente', 'voit_transferts_retires_jour',
    },
    'rh': {
        'voit_historique_employe',
        'voit_total_employes', 'voit_permis_a_renouveler', 'voit_groupe_clients_personnel',
    },
    'resp_maintenance': {
        'voit_historique_employe', 'voit_bus_service', 'voit_bus_maintenance', 'voit_groupe_maintenance',
    },
    'securite': {
        'voit_historique_employe', 'voit_alertes_non_resolues', 'voit_groupe_securite',
    },
    'autre': {'voit_historique_employe'},
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