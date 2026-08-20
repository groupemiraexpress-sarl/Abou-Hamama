"""
Verification periodique des expirations / annulations automatiques.

Ce module regroupe toute la logique qui doit tourner regulierement (toutes
les 15-30 minutes, via un service externe qui appelle l'URL
/api/tache/verifier-expirations/ ou via la commande de gestion
`verifier_expirations`) :

1. Reservations de billets non payees : delai normal de 24h apres la
   reservation. Si le voyage part le meme jour et que "24h apres la
   reservation" tombe apres "3h avant le depart", c'est la limite la plus
   proche (3h avant le depart) qui s'applique. Passe ce delai : alerte +
   annulation automatique, la place est reliberee.

2. Demandes de colis / demandes de transfert (avant qu'un agent ne les
   finalise a l'agence) : 24h apres la demande. Passe ce delai : alerte +
   demande annulee.

3. Colis enregistres et arrives a l'agence de destination, non retires :
   5 jours a partir de la date d'arrivee (et non de l'enregistrement).
   Passe ce delai : alerte + colis marque "retourne".

4. Transferts d'argent enregistres, non retires : 5 jours a partir de
   l'enregistrement (l'argent est disponible des l'envoi, il n'y a pas de
   trajet a attendre). Passe ce delai : alerte + transfert marque "annule".

Chaque annulation automatique envoie une notification push (si les
personnes concernees ont un compte client lie a leur numero de telephone),
en reutilisant le mecanisme existant `notifier_telephone`.
"""
from datetime import datetime, timedelta

from django.utils import timezone

from .models import Colis, DemandeColis, DemandeTransfert, Reservation, TransfertArgent
from .notifications import notifier_telephone

DELAI_DEMANDE = timedelta(hours=24)
DELAI_RETRAIT = timedelta(days=5)
DELAI_BILLET_NORMAL = timedelta(hours=24)
DELAI_BILLET_AVANT_DEPART = timedelta(hours=3)


def _echeance_reservation(reservation):
    """Renvoie la date/heure a partir de laquelle une reservation impayee
    doit etre annulee : 24h apres la reservation, ou 3h avant le depart du
    voyage si c'est plus tot (cas d'une reservation faite le jour meme)."""
    echeance = reservation.date_reservation + DELAI_BILLET_NORMAL
    voyage = reservation.voyage
    if voyage and voyage.date_depart and voyage.heure_depart:
        depart_naif = datetime.combine(voyage.date_depart, voyage.heure_depart)
        depart_dt = timezone.make_aware(depart_naif) if timezone.is_naive(depart_naif) else depart_naif
        echeance_avant_depart = depart_dt - DELAI_BILLET_AVANT_DEPART
        if echeance_avant_depart < echeance:
            echeance = echeance_avant_depart
    return echeance


def _traiter_reservations_impayees(maintenant):
    nb_annulees = 0
    reservations = Reservation.objects.filter(statut='en_attente').select_related('voyage', 'client')
    for reservation in reservations:
        if maintenant < _echeance_reservation(reservation):
            continue

        voyage = reservation.voyage
        if voyage and not voyage.ligne_id:
            voyage.places_disponibles += reservation.nombre_places
            voyage.save(update_fields=['places_disponibles'])

        reservation.statut = 'annulee'
        reservation.save(update_fields=['statut'])

        titre = "Reservation annulee"
        corps = (
            f"Votre reservation {reservation.numero_reservation} a expire "
            f"(paiement non effectue a temps) et a ete annulee automatiquement."
        )
        donnees = {"type": "reservation_expiree", "numero_reservation": reservation.numero_reservation}
        if reservation.client_id and reservation.client.telephone:
            notifier_telephone(reservation.client.telephone, titre, corps, donnees)
        if reservation.voyageur_telephone and reservation.voyageur_telephone != getattr(reservation.client, 'telephone', None):
            notifier_telephone(reservation.voyageur_telephone, titre, corps, donnees)
        nb_annulees += 1
    return nb_annulees


def _traiter_demandes_colis(maintenant):
    nb_annulees = 0
    seuil = maintenant - DELAI_DEMANDE
    for demande in DemandeColis.objects.filter(statut='en_attente', date_demande__lte=seuil):
        demande.statut = 'annulee'
        demande.save(update_fields=['statut'])
        notifier_telephone(
            demande.expediteur_telephone, "Demande de colis annulee",
            f"Votre demande de colis {demande.numero_demande} n'a pas ete finalisee a l'agence "
            f"dans les 24h et a ete annulee automatiquement.",
            {"type": "demande_colis_expiree", "numero_demande": demande.numero_demande},
        )
        nb_annulees += 1
    return nb_annulees


def _traiter_demandes_transfert(maintenant):
    nb_annulees = 0
    seuil = maintenant - DELAI_DEMANDE
    for demande in DemandeTransfert.objects.filter(statut='en_attente', date_demande__lte=seuil):
        demande.statut = 'annulee'
        demande.save(update_fields=['statut'])
        notifier_telephone(
            demande.expediteur_telephone, "Demande de transfert annulee",
            f"Votre demande de transfert {demande.numero_demande} n'a pas ete finalisee a l'agence "
            f"dans les 24h et a ete annulee automatiquement.",
            {"type": "demande_transfert_expiree", "numero_demande": demande.numero_demande},
        )
        nb_annulees += 1
    return nb_annulees


def _traiter_colis_non_retires(maintenant):
    nb_retournes = 0
    seuil = maintenant - DELAI_RETRAIT
    colis_en_retard = Colis.objects.filter(statut='arrive', date_arrivee__isnull=False, date_arrivee__lte=seuil)
    for colis in colis_en_retard:
        colis.statut = 'retourne'
        colis.save(update_fields=['statut'])
        notifier_telephone(
            colis.expediteur_telephone, "Colis non retire",
            f"Le colis {colis.code_suivi} n'a pas ete retire dans le delai de 5 jours "
            f"apres son arrivee a l'agence. Il est marque comme retourne.",
            {"type": "colis_non_retire", "code_suivi": colis.code_suivi},
        )
        notifier_telephone(
            colis.destinataire_telephone, "Colis non retire",
            f"Le delai de 5 jours pour retirer le colis {colis.code_suivi} est depasse. "
            f"Contactez l'agence {colis.agence_arrivee}.",
            {"type": "colis_non_retire", "code_suivi": colis.code_suivi},
        )
        nb_retournes += 1
    return nb_retournes


def _traiter_transferts_non_retires(maintenant):
    nb_annules = 0
    seuil = maintenant - DELAI_RETRAIT
    transferts_en_retard = TransfertArgent.objects.filter(statut='en_attente', date_envoi__lte=seuil)
    for transfert in transferts_en_retard:
        transfert.statut = 'annule'
        transfert.save(update_fields=['statut'])
        notifier_telephone(
            transfert.expediteur_telephone, "Transfert non retire",
            f"Le transfert {transfert.code_transfert} n'a pas ete retire dans le delai de 5 jours "
            f"et a ete annule automatiquement.",
            {"type": "transfert_non_retire", "code_transfert": transfert.code_transfert},
        )
        notifier_telephone(
            transfert.beneficiaire_telephone, "Transfert non retire",
            f"Le delai de 5 jours pour retirer le transfert {transfert.code_transfert} est depasse. "
            f"Contactez l'agence {transfert.agence_retrait}.",
            {"type": "transfert_non_retire", "code_transfert": transfert.code_transfert},
        )
        nb_annules += 1
    return nb_annules


def traiter_expirations():
    """Lance toutes les verifications d'expiration et renvoie un resume."""
    maintenant = timezone.now()
    return {
        'reservations_annulees': _traiter_reservations_impayees(maintenant),
        'demandes_colis_annulees': _traiter_demandes_colis(maintenant),
        'demandes_transfert_annulees': _traiter_demandes_transfert(maintenant),
        'colis_retournes': _traiter_colis_non_retires(maintenant),
        'transferts_annules': _traiter_transferts_non_retires(maintenant),
    }
