import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from transport.models import Client

compteur = 0
for client in Client.objects.filter(code_parrainage__isnull=True):
    client.save()  # le save() genere le code automatiquement
    compteur += 1

print(f"{compteur} code(s) de parrainage genere(s).")
print(f"Total clients avec code : {Client.objects.exclude(code_parrainage__isnull=True).count()}")