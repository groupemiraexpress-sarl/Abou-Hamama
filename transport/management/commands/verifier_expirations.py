"""
Lance manuellement (ou via une tache planifiee sur le serveur) la
verification des expirations : reservations impayees, demandes de colis/
transfert non finalisees, colis/transferts non retires.

Usage :
    python manage.py verifier_expirations
"""
from django.core.management.base import BaseCommand

from transport.expiration import traiter_expirations


class Command(BaseCommand):
    help = "Annule automatiquement les reservations, demandes et retraits expires, et notifie les personnes concernees."

    def handle(self, *args, **options):
        resultat = traiter_expirations()
        self.stdout.write(self.style.SUCCESS(
            f"Reservations annulees : {resultat['reservations_annulees']} | "
            f"Demandes colis annulees : {resultat['demandes_colis_annulees']} | "
            f"Demandes transfert annulees : {resultat['demandes_transfert_annulees']} | "
            f"Colis retournes : {resultat['colis_retournes']} | "
            f"Transferts annules : {resultat['transferts_annules']}"
        ))
