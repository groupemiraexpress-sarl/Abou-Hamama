import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from transport.models import Voyage, Siege, Bus, Trajet, Chauffeur

print("=== TEST GENERATION DES SIEGES ===")

# Prendre un voyage existant et regarder ses sieges
voyage = Voyage.objects.first()
if not voyage:
    print("Aucun voyage en base.")
    raise SystemExit

nb_sieges = Siege.objects.filter(voyage=voyage).count()
print(f"Voyage existant : {voyage} (bus capacite {voyage.bus.capacite})")
print(f"Sieges pour ce voyage : {nb_sieges}")

if nb_sieges == 0:
    print("-> Ce voyage n'a pas de sieges (cree AVANT l'ajout de la generation).")
    print("-> On genere ses sieges maintenant pour le test...")
    capacite = voyage.bus.capacite
    sieges = [Siege(voyage=voyage, numero=n) for n in range(1, capacite + 1)]
    Siege.objects.bulk_create(sieges)
    nb = Siege.objects.filter(voyage=voyage).count()
    print(f"-> {nb} sieges crees pour ce voyage.")

# Afficher quelques sieges
print("\nApercu des 5 premiers sieges :")
for s in Siege.objects.filter(voyage=voyage).order_by('numero')[:5]:
    etat = "occupe" if s.occupe else "libre"
    print(f"  Siege {s.numero} : {etat}")

print("\n=== TEST TERMINE ===")
