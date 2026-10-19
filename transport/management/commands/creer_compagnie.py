import secrets
import string

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from transport.admin_filtres import assigner_groupe_selon_poste
from transport.models import Compagnie, Employe
from transport.tenant import identifiant_employe


class Command(BaseCommand):
    help = "Cree une nouvelle compagnie avec son PDG (compte de connexion et mot de passe temporaire)."

    def add_arguments(self, parser):
        parser.add_argument('--nom', required=True, help="Nom de la compagnie (ex : Ben Siam)")
        parser.add_argument('--code', required=True, help="Code court en minuscules, unique (ex : bs)")
        parser.add_argument('--siege', required=True, help="Siege social")
        parser.add_argument('--telephone', required=True, help="Telephone de la compagnie")
        parser.add_argument('--pdg-nom', required=True)
        parser.add_argument('--pdg-prenom', required=True)
        parser.add_argument('--pdg-telephone', required=True)
        parser.add_argument('--nom-affiche', default='')
        parser.add_argument('--couleur', default='#261F64', help="Couleur principale #RRGGBB")
        parser.add_argument('--domaine', default='', help="Adresse web propre (facultatif)")

    @transaction.atomic
    def handle(self, *args, **o):
        code = o['code'].strip().lower()
        if Compagnie.objects.filter(code=code).exists():
            raise CommandError(f"Le code '{code}' existe deja.")
        compagnie = Compagnie(
            nom=o['nom'], code=code, nom_affiche=o['nom_affiche'], siege_social=o['siege'], telephone=o['telephone'],
            couleur_principale=o['couleur'], domaine=o['domaine'], pied_de_page=f"Agence {o['nom']}",
        )
        compagnie.full_clean()
        compagnie.save()

        identifiant = identifiant_employe(compagnie, o['pdg_telephone'])
        if User.objects.filter(username=identifiant).exists():
            raise CommandError(f"L'identifiant '{identifiant}' existe deja.")
        alphabet = string.ascii_letters + string.digits
        mot_de_passe = ''.join(secrets.choice(alphabet) for _ in range(10))
        user = User.objects.create_user(username=identifiant, password=mot_de_passe, is_staff=True)
        Employe.objects.create(
            user=user, compagnie=compagnie, nom=o['pdg_nom'], prenom=o['pdg_prenom'],
            telephone=o['pdg_telephone'], poste='pdg',
        )
        assigner_groupe_selon_poste(user, 'pdg')

        self.stdout.write(self.style.SUCCESS(f"Compagnie '{compagnie.nom}' creee (code : {code})."))
        self.stdout.write(f"Compte PDG : identifiant = {identifiant}   mot de passe temporaire = {mot_de_passe}")
        self.stdout.write("Le PDG doit changer ce mot de passe a sa premiere connexion.")
