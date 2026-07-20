"""Calcul des statistiques pour le tableau de bord de l'admin."""

from django.utils import timezone
from .models import (
    Voyage, Reservation, Colis, TransfertArgent,
    DemandeColis, DemandeTransfert, Client, Bus
)


def statistiques_tableau_bord():
    aujourd_hui = timezone.now().date()

    # Voyages
    voyages_aujourd_hui = Voyage.objects.filter(date_depart=aujourd_hui).count()
    voyages_a_venir = Voyage.objects.filter(date_depart__gt=aujourd_hui).count()

    # Reservations
    reservations_jour = Reservation.objects.filter(date_reservation__date=aujourd_hui).count()
    reservations_attente = Reservation.objects.filter(statut='en_attente').count()
    recette_jour = sum(
        r.montant_total for r in Reservation.objects.filter(
            date_paiement__date=aujourd_hui, statut='payee'
        )
    )

    # Demandes en attente
    demandes_colis_attente = DemandeColis.objects.filter(statut='en_attente').count()
    demandes_transfert_attente = DemandeTransfert.objects.filter(statut='en_attente').count()

    # Colis et transferts
    colis_transit = Colis.objects.filter(statut='en_transit').count()
    colis_arrives = Colis.objects.filter(statut='arrive').count()
    transferts_attente = TransfertArgent.objects.filter(statut='en_attente').count()

    # Parc
    bus_service = Bus.objects.filter(statut='en_service').count()
    bus_maintenance = Bus.objects.filter(statut='maintenance').count()

    # Clients
    total_clients = Client.objects.filter(actif=True).count()

    return {
        'voyages_aujourd_hui': voyages_aujourd_hui,
        'voyages_a_venir': voyages_a_venir,
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
