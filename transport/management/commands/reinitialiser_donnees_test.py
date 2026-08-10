"""
Reinitialise les donnees de test : supprime TOUTES les reservations et
TOUS les employes (+ leurs comptes de connexion associes), pour repartir
de zero et creer les employes reels manuellement.

Emplacement : transport/management/commands/reinitialiser_donnees_test.py
(meme dossier que generer_employes_test.py)

ATTENTION : action IRREVERSIBLE. Par securite, cette commande ne supprime
RIEN sans le flag --confirmer : sans ce flag, elle affiche seulement un
apercu de ce qui serait supprime.

Ton compte superuser (celui avec lequel tu te connectes en tant qu'ADMIN)
n'est jamais supprime, meme s'il est lie a un Employe qui l'est.

Usage :
    python manage.py reinitialiser_donnees_test              (apercu seulement)
    python manage.py reinitialiser_donnees_test --confirmer  (supprime pour de vrai)
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from transport.models import Reservation, Employe


class Command(BaseCommand):
    help = "Supprime toutes les reservations et tous les employes (+ comptes lies). Irreversible."

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirmer', action='store_true',
            help="Sans ce flag, la commande affiche seulement un apercu sans rien supprimer."
        )

    def handle(self, *args, **options):
        nb_reservations = Reservation.objects.count()
        nb_employes = Employe.objects.count()
        ids_users_lies = list(
            Employe.objects.exclude(user__isnull=True)
            .exclude(user__is_superuser=True)
            .values_list('user_id', flat=True)
        )
        nb_users = len(ids_users_lies)

        self.stdout.write("A supprimer si tu confirmes :")
        self.stdout.write(f"  - {nb_reservations} reservation(s)")
        self.stdout.write(f"  - {nb_employes} employe(s)")
        self.stdout.write(f"  - {nb_users} compte(s) utilisateur lie(s) (les superusers sont proteges, jamais supprimes)")

        if not options['confirmer']:
            self.stdout.write(self.style.WARNING(
                "\nAucune suppression effectuee (mode apercu). "
                "Relance avec --confirmer pour supprimer pour de vrai."
            ))
            return

        Reservation.objects.all().delete()
        Employe.objects.all().delete()
        User.objects.filter(pk__in=ids_users_lies).delete()

        self.stdout.write(self.style.SUCCESS(
            f"\nTermine : {nb_reservations} reservation(s), {nb_employes} employe(s) et "
            f"{nb_users} compte(s) utilisateur supprimes. Ton compte superuser est intact."
        ))
