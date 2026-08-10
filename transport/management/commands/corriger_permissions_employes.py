"""
Corrige retroactivement les comptes employes deja crees en les mettant
dans le BON groupe Django selon leur poste (au lieu du groupe generique
"Personnel Abou Hamama" cree par erreur au tout debut).

Emplacement : transport/management/commands/corriger_permissions_employes.py
(remplace le fichier du meme nom deja en place)

Usage :
    python manage.py corriger_permissions_employes
"""
from django.core.management.base import BaseCommand
from transport.admin_filtres import assigner_groupe_selon_poste
from transport.models import Employe


class Command(BaseCommand):
    help = "Met chaque employe existant dans le bon groupe Django selon son poste."

    def handle(self, *args, **options):
        employes = Employe.objects.exclude(user__isnull=True)
        compte = 0
        sans_groupe = []
        for employe in employes:
            assigner_groupe_selon_poste(employe.user, employe.poste)
            employe.user.is_staff = True
            employe.user.save()
            compte += 1
            if not employe.user.groups.exists():
                sans_groupe.append(f"{employe.prenom} {employe.nom} ({employe.get_poste_display()})")

        self.stdout.write(self.style.SUCCESS(f"Termine : {compte} compte(s) employe(s) traite(s)."))
        if sans_groupe:
            self.stdout.write(self.style.WARNING(
                "Attention, aucun groupe Django ne correspond a ces employes "
                "(verifie POSTE_VERS_GROUPE dans admin_filtres.py) :"
            ))
            for nom in sans_groupe:
                self.stdout.write(f"  - {nom}")
