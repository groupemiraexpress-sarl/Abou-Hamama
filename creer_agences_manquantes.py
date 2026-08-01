"""
Cree les agences manquantes avec juste nom/ville/coordonnees GPS.
Les autres champs (telephone, adresse, responsable) restent vides,
a completer manuellement dans l'admin.
A lancer : python creer_agences_manquantes.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from transport.models import Agence, Compagnie

AGENCES_A_CREER = [
    # (nom, ville, latitude, longitude)
    ("Agence Ngoura", "Ngoura", 12.7500, 16.7500),
    ("Agence Mangalme", "Mangalme", 12.4667, 19.9833),
    ("Agence Guelendeng", "Guelendeng", 10.9333, 15.5333),
    ("Agence Bongor", "Bongor", 10.2833, 15.3667),
    ("Agence Kelo", "Kelo", 9.3167, 15.8000),
    ("Agence Moundou", "Moundou", 8.5667, 16.0833),
    ("Agence Doba", "Doba", 8.6667, 16.8500),
]

print("=== CREATION DES AGENCES MANQUANTES ===\n")

compagnie = Compagnie.objects.first()
if not compagnie:
    print("ERREUR : aucune compagnie trouvee en base. Impossible de continuer.")
else:
    creees = 0
    deja_existantes = 0

    for nom, ville, lat, lng in AGENCES_A_CREER:
        agence, cree = Agence.objects.get_or_create(
            ville__iexact=ville,
            defaults={
                'nom': nom,
                'ville': ville,
                'compagnie': compagnie,
                'adresse': '',
                'telephone': '',
                'latitude': lat,
                'longitude': lng,
                'actif': True,
            },
        )
        if cree:
            creees += 1
            print(f"  {nom} ({ville}) : creee avec coordonnees ({lat}, {lng})")
        else:
            deja_existantes += 1
            print(f"  {agence.nom} ({ville}) : deja existante, ignoree")

    print(f"\n{creees} agence(s) creee(s).")
    print(f"{deja_existantes} agence(s) deja existante(s).")
    print("\nRAPPEL : complete manuellement le telephone, l'adresse et le responsable")
    print("de chaque nouvelle agence dans l'admin.")

print("\n=== TERMINE ===")