"""
Script de creation de comptes de test pour verifier les permissions.
A lancer : python creer_comptes_test.py
Mot de passe pour tous les comptes crees : Test1234!
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User, Group
from transport.models import Employe, Agence, Compagnie

MOT_DE_PASSE = "Test1234!"

# Villes des 3 agences utilisees pour le test (adapte si besoin)
VILLES_TEST = ["N'Djamena", "Abeche", "Mongo"]

# poste (code du modele Employe) -> nom du groupe de permissions
# Tous ces postes ont un compte par agence
POSTES_PAR_AGENCE = {
    'responsable': "Responsable d'agence",
    'secretaire': "Secretaire d'agence",
    'guichetier': "Guichetier / billettiste",
    'caissier': "Caissier",
    'agent_colis': "Agent colis",
    'agent_transfert': "Agent transfert d'argent",
    'manutentionnaire': "Manutentionnaire / bagagiste",
    'comptable': "Comptable",
    'rh': "Responsable RH",
    'resp_maintenance': "Responsable maintenance",
    'securite': "Agent de securite",
    'autre': "Autre (lecture seule)",
}

SLUGS = {
    'responsable': 'responsable',
    'secretaire': 'secretaire',
    'guichetier': 'guichet',
    'caissier': 'caissier',
    'agent_colis': 'agentcolis',
    'agent_transfert': 'agenttransfert',
    'manutentionnaire': 'bagagiste',
    'comptable': 'comptable',
    'rh': 'rh',
    'resp_maintenance': 'maintenance',
    'securite': 'securite',
    'autre': 'autre',
}


def trouver_agences():
    agences = []
    for ville in VILLES_TEST:
        a = Agence.objects.filter(ville__icontains=ville, actif=True).first()
        if a:
            agences.append(a)
        else:
            print(f"  ! Agence introuvable pour la ville : {ville}")
    if len(agences) < 3:
        manquant = 3 - len(agences)
        secours = Agence.objects.filter(actif=True).exclude(
            id__in=[a.id for a in agences]
        )[:manquant]
        agences.extend(secours)
    return agences


def creer_compte(username, poste_code, groupe_nom, agence=None, compagnie=None):
    user, cree_user = User.objects.get_or_create(
        username=username,
        defaults={'is_staff': True},
    )
    user.is_staff = True
    user.set_password(MOT_DE_PASSE)
    user.save()

    groupe = Group.objects.filter(name=groupe_nom).first()
    if groupe:
        user.groups.set([groupe])
    else:
        print(f"  ! Groupe introuvable : {groupe_nom}")

    employe, cree_emp = Employe.objects.get_or_create(
        user=user,
        defaults={
            'nom': username,
            'prenom': 'Test',
            'telephone': '60000000',
            'poste': poste_code,
            'agence': agence,
            'compagnie': compagnie,
        },
    )
    if not cree_emp:
        employe.poste = poste_code
        employe.agence = agence
        employe.compagnie = compagnie
        employe.nom = username
        employe.save()

    etat = "cree" if cree_user else "mis a jour"
    lieu = agence.nom if agence else "(siege, toutes agences)"
    print(f"  {username} : {etat} — {groupe_nom} — {lieu}")


print("=== CREATION DES COMPTES DE TEST ===\n")

agences = trouver_agences()
if len(agences) < 3:
    print("Attention : moins de 3 agences disponibles, le test sera partiel.\n")

print("Agences utilisees :", ", ".join(a.nom for a in agences), "\n")

# On recupere la compagnie a partir de la premiere agence trouvee
compagnie = agences[0].compagnie if agences else None
if not compagnie:
    compagnie = Compagnie.objects.first()

if not compagnie:
    print("ERREUR : aucune compagnie trouvee en base. Impossible de continuer.")
else:
    print("--- Compte PDG (unique, sans agence, voit tout) ---")
    creer_compte("test_pdg", 'pdg', "PDG / Direction", agence=None, compagnie=compagnie)

    print("\n--- Postes lies a une agence (un compte par agence) ---")
    for poste_code, groupe_nom in POSTES_PAR_AGENCE.items():
        slug = SLUGS[poste_code]
        for i, agence in enumerate(agences, start=1):
            username = f"test_{slug}_a{i}"
            creer_compte(username, poste_code, groupe_nom, agence=agence, compagnie=agence.compagnie)

    print("\n=== TERMINE ===")
    print(f"Mot de passe pour tous les comptes : {MOT_DE_PASSE}")