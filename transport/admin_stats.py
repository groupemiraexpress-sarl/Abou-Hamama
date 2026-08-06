"""Calcul des statistiques pour le tableau de bord de l'admin."""
from django.utils import timezone
from django.db.models import Q
from .models import (
    Voyage, Reservation, Colis, TransfertArgent,
    DemandeColis, DemandeTransfert, Client, Bus
)
from .admin_filtres import voit_tout, agence_de, POSTES_PERSONNEL


def statistiques_tableau_bord(user=None):
    from .models import AlerteVoyage
    aujourd_hui = timezone.now().date()

    employe = getattr(user, 'employe', None) if user else None
    poste = employe.poste if employe else None
    agence = agence_de(user) if user else None
    scope_global = user is None or voit_tout(user)

    reservations_qs = Reservation.objects.all()
    colis_qs = Colis.objects.all()
    transferts_qs = TransfertArgent.objects.all()
    demandes_colis_qs = DemandeColis.objects.all()
    demandes_transfert_qs = DemandeTransfert.objects.all()

    if not scope_global:
        if agence is None:
            reservations_qs = reservations_qs.none()
            colis_qs = colis_qs.none()
            transferts_qs = transferts_qs.none()
            demandes_colis_qs = demandes_colis_qs.none()
            demandes_transfert_qs = demandes_transfert_qs.none()
        else:
            if poste in POSTES_PERSONNEL:
                reservations_qs = reservations_qs.filter(cree_par=employe)
                colis_qs = colis_qs.filter(cree_par=employe)
                transferts_qs = transferts_qs.filter(cree_par=employe)
            else:
                reservations_qs = reservations_qs.filter(agence=agence)
                colis_qs = colis_qs.filter(Q(agence_depart=agence) | Q(agence_arrivee=agence))
                transferts_qs = transferts_qs.filter(Q(agence_depart=agence) | Q(agence_retrait=agence))

            demandes_colis_qs = demandes_colis_qs.filter(Q(agence_depart=agence) | Q(agence_arrivee=agence))
            demandes_transfert_qs = demandes_transfert_qs.filter(Q(agence_depart=agence) | Q(agence_retrait=agence))

    # Voyages et parc (pas de notion d'agence sur ces modeles, restent globaux)
    voyages_aujourd_hui = Voyage.objects.filter(date_depart=aujourd_hui).count()
    voyages_a_venir = Voyage.objects.filter(date_depart__gt=aujourd_hui).count()
    bus_service = Bus.objects.filter(statut='en_service').count()
    bus_maintenance = Bus.objects.filter(statut='maintenance').count()
    total_clients = Client.objects.filter(actif=True).count()

    # Reservations (filtrees)
    reservations_jour = reservations_qs.filter(date_reservation__date=aujourd_hui).count()
    reservations_attente = reservations_qs.filter(statut='en_attente').count()
    recette_jour = sum(
        r.montant_total for r in reservations_qs.filter(
            date_paiement__date=aujourd_hui, statut='payee'
        )
    )

    # Demandes en attente (filtrees)
    demandes_colis_attente = demandes_colis_qs.filter(statut='en_attente').count()
    demandes_transfert_attente = demandes_transfert_qs.filter(statut='en_attente').count()

    # Colis et transferts (filtres)
    colis_transit = colis_qs.filter(statut='en_transit').count()
    colis_arrives = colis_qs.filter(statut='arrive').count()
    transferts_attente = transferts_qs.filter(statut='en_attente').count()

    alertes_non_resolues = AlerteVoyage.objects.filter(resolue=False).count()

    return {
        'voyages_aujourd_hui': voyages_aujourd_hui,
        'voyages_a_venir': voyages_a_venir,
        'alertes_non_resolues': alertes_non_resolues,
        'reservations_jour': reservations_jour,
        'reservations_attente': reservations_attente,
        'recette_jour': recette_jour,
        'demandes_colis_attente': demandes_colis_attente,
        'demandes_transfert_attente': demandes_transfert_attente,
        'demandes_total_attente': demandes_colis_attente + demandes_transfert_attente,
        'colis_transit': colis_transit,
        'colis_arrives': colis_arrives,
        'transferts_attente': transferts_attente,
        'bus_service': bus_service,
        'bus_maintenance': bus_maintenance,
        'total_clients': total_clients,
    }