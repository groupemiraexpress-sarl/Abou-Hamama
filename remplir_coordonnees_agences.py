"""
Remplit automatiquement les coordonnees GPS des agences connues.
A lancer : python remplir_coordonnees_agences.py
Relancer ce script ne modifie que les agences dont Latitude/Longitude sont vides.
"""

import os
import django
import unicodedata

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from transport.models import Agence

# Coordonnees connues, par ville (sans accents/apostrophes pour la comparaison)
COORDONNEES = {
    # --- Zone Nord ---
    "ndjamena": (12.1067, 15.0444),
    "massaguet": (12.4667, 15.4333),
    "massageut": (12.4667, 15.4333),
    "massa gueit": (12.4667, 15.4333),
    "massa guet": (12.4667, 15.4333),
    "ngoura": (12.7500, 16.7500),        # approximatif, a verifier
    "bokoro": (12.3833, 17.0500),
    "bitkine": (11.9803, 18.2144),
    "mongo": (12.1833, 18.6833),
    "mangalme": (12.4667, 19.9833),      # approximatif, a verifier
    "oum hadjer": (13.2967, 19.6975),
    "abeche": (13.8292, 20.8324),

    # --- Zone Sud ---
    "guelendeng": (10.9333, 15.5333),
    "bongor": (10.2833, 15.3667),
    "kelo": (9.3167, 15.8000),
    "moundou": (8.5667, 16.0833),
    "doba": (8.6667, 16.8500),
}


def normaliser(texte):
    texte = unicodedata.normalize('NFD', texte)
    texte = ''.join(c for c in texte if unicodedata.category(c) != 'Mn')
    texte = texte.replace("'", "").replace("-", " ")
    return texte.lower().strip()


print("=== REMPLISSAGE DES COORDONNEES GPS ===\n")

remplies = 0
deja_ok = 0
inconnues = []

for agence in Agence.objects.all():
    if agence.latitude is not None and agence.longitude is not None:
        deja_ok += 1
        continue

    ville_norm = normaliser(agence.ville)
    if ville_norm in COORDONNEES:
        lat, lng = COORDONNEES[ville_norm]
        agence.latitude = lat
        agence.longitude = lng
        agence.save()
        remplies += 1
        print(f"  {agence.nom} ({agence.ville}) : rempli ({lat}, {lng})")
    else:
        inconnues.append(agence)

print(f"\n{remplies} agence(s) remplie(s).")
print(f"{deja_ok} agence(s) deja renseignee(s).")

if inconnues:
    print(f"\n{len(inconnues)} agence(s) sans coordonnees connues, a remplir manuellement :")
    for a in inconnues:
        print(f"  - {a.nom} (ville : {a.ville})")

print("\n=== TERMINE ===")