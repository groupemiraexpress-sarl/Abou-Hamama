import sqlite3
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Copie la base de donnees (SQLite) dans le dossier 'sauvegardes', sans arreter le site, et ne garde que les plus recentes."

    def add_arguments(self, parser):
        parser.add_argument('--garder', type=int, default=14, help="Nombre de sauvegardes conservees (14 par defaut)")

    def handle(self, *args, **options):
        base = settings.DATABASES['default']
        if not base['ENGINE'].endswith('sqlite3'):
            raise CommandError("Cette commande ne sauvegarde que SQLite. Utilisez la sauvegarde de votre base (PostgreSQL/MySQL).")
        dossier = Path(settings.BASE_DIR) / 'sauvegardes'
        dossier.mkdir(exist_ok=True)
        destination = dossier / f"db_{datetime.now():%Y-%m-%d_%H%M}.sqlite3"
        source = sqlite3.connect(str(base['NAME']))
        copie = sqlite3.connect(str(destination))
        try:
            source.backup(copie)    # copie coherente meme si le site ecrit en meme temps
        finally:
            copie.close()
            source.close()
        anciennes = sorted(dossier.glob('db_*.sqlite3'))[:-options['garder']]
        for ancienne in anciennes:
            ancienne.unlink()
        self.stdout.write(self.style.SUCCESS(f"Sauvegarde creee : {destination.name} ({destination.stat().st_size // 1024} Ko). {len(anciennes)} ancienne(s) supprimee(s)."))
