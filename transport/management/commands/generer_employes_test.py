"""
Commande de gestion Django pour generer des employes de test sur toutes
les agences actives, avec un compte de connexion et un mot de passe
unique chacun. Exporte tout dans un fichier CSV.

Emplacement a respecter : transport/management/commands/generer_employes_test.py

Usage :
    python manage.py generer_employes_test
    python manage.py generer_employes_test --nettoyer

--nettoyer supprime d'abord tous les employes de test generes precedemment
(reconnus par leur prenom qui commence par "Test") avant de regenerer.
Utile si le script a ete interrompu ou relance plusieurs fois.

ATTENTION : ce script cree ~500 comptes, chacun avec un mot de passe
hache (volontairement lent, pour la securite). Ca peut prendre 1 a 2
minutes selon la machine. C'est normal, ne pas interrompre (Ctrl+C) :
une interruption en cours de route laisse des donnees partielles, il
faudra relancer avec --nettoyer pour repartir propre.
"""
import csv
import secrets
import string

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from transport.models import Agence, Compagnie, Employe


# Postes crees automatiquement pour CHAQUE agence, avec le nombre d'employes
# par poste. PDG (unique, deja existant) et Responsable planning (poste par
# zone, pas par agence) sont volontairement exclus.
POSTES_A_CREER = {
    'responsable': 1,
    'secretaire': 3,
    'guichetier': 3,
    'caissier': 3,
    'agent_colis': 3,
    'agent_transfert': 3,
    'manutentionnaire': 3,
    'comptable': 3,
    'rh': 3,
    'resp_maintenance': 3,
    'securite': 3,
    'autre': 3,
}

FICHIER_SORTIE = 'employes_test_identifiants.csv'


def generer_mot_de_passe(longueur=10):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(longueur))


class Command(BaseCommand):
    help = "Genere des employes de test (avec compte de connexion) pour toutes les agences actives, tous postes confondus."

    def add_arguments(self, parser):
        parser.add_argument(
            '--nettoyer', action='store_true',
            help="Supprime d'abord tous les employes de test generes precedemment (prenom commencant par 'Test')."
        )

    def handle(self, *args, **options):
        if options['nettoyer']:
            anciens = Employe.objects.filter(prenom__startswith='Test')
            anciens_users = [e.user for e in anciens if e.user_id]
            nb = anciens.count()
            anciens.delete()
            for u in anciens_users:
                u.delete()
            self.stdout.write(self.style.WARNING(f"{nb} ancien(s) employe(s) de test supprime(s)."))

        # Filet de securite supplementaire : meme sans --nettoyer, si des
        # comptes de test partiels trainent (interruption precedente), on
        # les detecte et on previent au lieu de planter plus loin.
        orphelins = User.objects.filter(username__regex=r'^6000000[0-9]+$').count()
        if orphelins and not options['nettoyer']:
            self.stderr.write(self.style.ERROR(
                f"{orphelins} compte(s) de test semblent deja exister (execution precedente interrompue ?). "
                f"Relance avec : python manage.py generer_employes_test --nettoyer"
            ))
            return

        compagnie = Compagnie.objects.first()
        if compagnie is None:
            self.stderr.write(self.style.ERROR("Aucune Compagnie trouvee en base. Cree-la d'abord dans l'admin."))
            return

        agences = Agence.objects.filter(actif=True).order_by('ville', 'nom')
        if not agences.exists():
            self.stderr.write(self.style.ERROR("Aucune Agence active trouvee en base."))
            return

        total_a_creer = agences.count() * sum(POSTES_A_CREER.values())
        self.stdout.write(f"Generation de {total_a_creer} employes sur {agences.count()} agences en cours...")
        self.stdout.write("(peut prendre 1 a 2 minutes, ne pas interrompre)")

        resultats = []
        compteur_telephone = 1
        cree = 0

        for agence in agences:
            for poste, nombre in POSTES_A_CREER.items():
                for i in range(1, nombre + 1):
                    prenom = f"Test{i}"
                    nom = poste.replace('_', ' ').capitalize()
                    # Numero au format tchadien (8 chiffres, commence par 6)
                    telephone = f"6{compteur_telephone:07d}"
                    compteur_telephone += 1
                    mot_de_passe = generer_mot_de_passe()

                    user = User.objects.create_user(
                        username=telephone,
                        password=mot_de_passe,
                        first_name=prenom,
                        last_name=nom,
                        is_staff=True,
                    )
                    employe = Employe.objects.create(
                        user=user,
                        compagnie=compagnie,
                        agence=agence,
                        nom=nom,
                        prenom=prenom,
                        telephone=telephone,
                        poste=poste,
                        actif=True,
                    )
                    resultats.append({
                        'agence': agence.nom,
                        'ville': agence.ville,
                        'poste': employe.get_poste_display(),
                        'nom_complet': f"{prenom} {nom}",
                        'identifiant': telephone,
                        'mot_de_passe': mot_de_passe,
                    })

                    cree += 1
                    if cree % 25 == 0:
                        self.stdout.write(f"  ... {cree}/{total_a_creer} crees")

        with open(FICHIER_SORTIE, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(
                f, fieldnames=['agence', 'ville', 'poste', 'nom_complet', 'identifiant', 'mot_de_passe']
            )
            writer.writeheader()
            writer.writerows(resultats)

        self.stdout.write(self.style.SUCCESS(
            f"Termine : {len(resultats)} employes de test crees sur {agences.count()} agences. "
            f"Identifiants et mots de passe enregistres dans {FICHIER_SORTIE}"
        ))
