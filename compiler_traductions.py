import polib

po = polib.pofile('locale/ar/LC_MESSAGES/django.po')
po.save_as_mofile('locale/ar/LC_MESSAGES/django.mo')
print(f"Compilation OK : {len(po)} traductions arabes compilees.")
