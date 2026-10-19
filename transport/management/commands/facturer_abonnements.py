from django.core.management.base import BaseCommand

from transport.services_facturation import generer_factures_du_mois


class Command(BaseCommand):
    help = "Cree les factures d'abonnement du mois en cours pour chaque entreprise active (sans doublon). A planifier une fois par mois ; le meme travail se fait par l'ecran Facturation."

    def handle(self, *args, **options):
        creees = generer_factures_du_mois()
        for f in creees:
            self.stdout.write(f"{f.numero} : {f.compagnie.nom} - {f.montant} FCFA (a payer avant le {f.date_echeance:%d/%m/%Y})")
        self.stdout.write(self.style.SUCCESS(f"{len(creees)} facture(s) creee(s)."))
