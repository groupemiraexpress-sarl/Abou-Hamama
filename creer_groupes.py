"""
Script de creation des groupes de permissions pour Express Abou Hamama.
A lancer une seule fois : python creer_groupes.py
Relancer ce script met a jour les permissions sans supprimer les groupes.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

# Modeles de l'application transport
MODELES = [
    'compagnie', 'agence', 'bus', 'chauffeur', 'trajet', 'voyage',
    'client', 'reservation', 'colis', 'employe', 'transfertargent',
    'entretien', 'pleincarburant', 'siege', 'promotion',
    'demandecolis', 'demandetransfert',
]


def perms(modele, actions):
    """Retourne les permissions demandees pour un modele.
    actions : liste parmi 'view', 'add', 'change', 'delete'
    """
    resultat = []
    try:
        ct = ContentType.objects.get(app_label='transport', model=modele)
    except ContentType.DoesNotExist:
        print(f"  ! Modele introuvable : {modele}")
        return resultat
    for action in actions:
        code = f"{action}_{modele}"
        p = Permission.objects.filter(content_type=ct, codename=code).first()
        if p:
            resultat.append(p)
    return resultat


TOUT = ['view', 'add', 'change', 'delete']
LIRE_ECRIRE = ['view', 'add', 'change']
LIRE = ['view']


# Definition des roles : nom du groupe -> {modele: actions}
ROLES = {

    "PDG / Direction": {
        m: TOUT for m in MODELES
    },

    "Responsable d'agence": {
        'voyage': LIRE_ECRIRE,
        'reservation': LIRE_ECRIRE,
        'colis': LIRE_ECRIRE,
        'transfertargent': LIRE_ECRIRE,
        'demandecolis': LIRE_ECRIRE,
        'demandetransfert': LIRE_ECRIRE,
        'client': LIRE_ECRIRE,
        'employe': LIRE,
        'bus': LIRE,
        'chauffeur': LIRE,
        'trajet': LIRE,
        'agence': LIRE,
        'siege': LIRE,
        'promotion': LIRE,
    },

    "Guichetier / billettiste": {
        'voyage': LIRE,
        'reservation': LIRE_ECRIRE,
        'client': LIRE_ECRIRE,
        'siege': LIRE_ECRIRE,
        'trajet': LIRE,
        'bus': LIRE,
        'agence': LIRE,
    },

    "Caissier": {
        'reservation': LIRE_ECRIRE,
        'colis': LIRE,
        'transfertargent': LIRE_ECRIRE,
        'client': LIRE,
        'voyage': LIRE,
        'agence': LIRE,
    },

    "Agent colis": {
        'colis': LIRE_ECRIRE,
        'demandecolis': LIRE_ECRIRE,
        'client': LIRE,
        'voyage': LIRE,
        'agence': LIRE,
    },

    "Agent transfert d'argent": {
        'transfertargent': LIRE_ECRIRE,
        'demandetransfert': LIRE_ECRIRE,
        'client': LIRE,
        'agence': LIRE,
    },

    "Manutentionnaire / bagagiste": {
        'colis': LIRE,
        'voyage': LIRE,
    },

    "Comptable": {
        'reservation': LIRE,
        'colis': LIRE,
        'transfertargent': LIRE,
        'entretien': LIRE,
        'pleincarburant': LIRE,
        'employe': LIRE,
        'voyage': LIRE,
        'agence': LIRE,
    },

    "Responsable RH": {
        'employe': TOUT,
        'chauffeur': LIRE_ECRIRE,
        'agence': LIRE,
    },

    "Responsable maintenance": {
        'entretien': LIRE_ECRIRE,
        'pleincarburant': LIRE_ECRIRE,
        'bus': LIRE_ECRIRE,
        'chauffeur': LIRE,
        'voyage': LIRE,
    },

    "Agent de securite": {
        'voyage': LIRE,
        'reservation': LIRE,
    },

    "Autre (lecture seule)": {
        'voyage': LIRE,
        'agence': LIRE,
    },
}


print("=== CREATION DES GROUPES DE PERMISSIONS ===\n")

for nom_groupe, definition in ROLES.items():
    groupe, cree = Group.objects.get_or_create(name=nom_groupe)
    groupe.permissions.clear()
    total = 0
    for modele, actions in definition.items():
        liste = perms(modele, actions)
        groupe.permissions.add(*liste)
        total += len(liste)
    etat = "cree" if cree else "mis a jour"
    print(f"{nom_groupe} : {etat} ({total} permissions)")

print("\n=== TERMINE ===")
print("\nRAPPEL : pour qu'un employe puisse se connecter a l'admin,")
print("il faut cocher 'Statut equipe' (is_staff) sur son compte utilisateur,")
print("puis lui attribuer le groupe correspondant a son poste.")
