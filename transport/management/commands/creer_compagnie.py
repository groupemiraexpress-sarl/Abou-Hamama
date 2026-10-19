from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from transport.services_plateforme import creer_compagnie_avec_pdg


class Command(BaseCommand):
    help = "Cree une nouvelle compagnie avec son PDG (compte de connexion et mot de passe temporaire). Le meme travail se fait par l'ecran Plateforme."

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

    def handle(self, *args, **o):
        try:
            compagnie, identifiant, mot_de_passe = creer_compagnie_avec_pdg(
                nom=o['nom'], code=o['code'], siege=o['siege'], telephone=o['telephone'], pdg_nom=o['pdg_nom'],
                pdg_prenom=o['pdg_prenom'], pdg_telephone=o['pdg_telephone'], nom_affiche=o['nom_affiche'],
                couleur=o['couleur'], domaine=o['domaine'],
            )
        except ValidationError as e:
            raise CommandError(f"{e.message_dict if hasattr(e, 'error_dict') else e.messages}")
        self.stdout.write(self.style.SUCCESS(f"Compagnie '{compagnie.nom}' creee (code : {compagnie.code})."))
        self.stdout.write(f"Compte PDG : identifiant = {identifiant}   mot de passe temporaire = {mot_de_passe}")
        self.stdout.write("Le PDG doit changer ce mot de passe a sa premiere connexion.")
