"""
Remplit automatiquement les traductions arabes des nouvelles chaines
ajoutees dans admin.py aujourd'hui. A executer UNE FOIS, APRES avoir
lance : python manage.py makemessages -l ar

Installation prealable (une seule fois) :
    pip install polib --break-system-packages

Usage (depuis C:\\projets\\transtchad) :
    python remplir_traductions_ar.py
"""
import polib

FICHIER = "locale/ar/LC_MESSAGES/django.po"

TRADUCTIONS = {
    "Nom d'utilisateur app (optionnel)": "اسم المستخدم للتطبيق (اختياري)",
    "A remplir uniquement si ce client doit avoir un acces a l'application "
    "mobile. Laisser vide pour un client comptoir classique (aucun compte cree).":
        "يُملأ فقط إذا كان هذا العميل بحاجة إلى الوصول إلى التطبيق. اتركه فارغًا لعميل الشباك العادي (لن يُنشأ أي حساب).",
    "Requis uniquement si un nom d'utilisateur est renseigne ci-dessus.":
        "مطلوب فقط إذا تم إدخال اسم مستخدم أعلاه.",
    "Ce nom d'utilisateur est deja pris.": "اسم المستخدم هذا مستخدم بالفعل.",
    "Mot de passe requis pour creer le compte.": "كلمة المرور مطلوبة لإنشاء الحساب.",
    "Nom d'utilisateur (connexion)": "اسم المستخدم (تسجيل الدخول)",
    "Laisser vide pour utiliser le telephone comme identifiant. "
    "En modification, laisser vide pour ne pas toucher au compte existant.":
        "اتركه فارغًا لاستخدام رقم الهاتف كمعرف. عند التعديل، اتركه فارغًا لعدم تغيير الحساب الحالي.",
    "Laisser vide : a la creation, un mot de passe temporaire sera genere et affiche.":
        "اتركه فارغًا: عند الإنشاء، سيتم توليد كلمة مرور مؤقتة وعرضها.",
    "Un seul compte PDG est autorise dans le logiciel. Un PDG existe deja.":
        "لا يُسمح إلا بحساب مدير عام واحد في النظام. يوجد مدير عام بالفعل.",
    "Ce nom d'utilisateur est deja pris par un autre compte.":
        "اسم المستخدم هذا مستخدم بالفعل من قبل حساب آخر.",
    "Renseignez un telephone ou un nom d'utilisateur pour creer le compte.":
        "أدخل رقم هاتف أو اسم مستخدم لإنشاء الحساب.",
    "Cet identifiant (nom d'utilisateur ou telephone) est deja pris. "
    "Renseignez un nom d'utilisateur different.":
        "هذا المعرف (اسم المستخدم أو الهاتف) مستخدم بالفعل. أدخل اسم مستخدم مختلف.",
    'Compte cree : identifiant "%(identifiant)s" / mot de passe temporaire "%(motdepasse)s". '
    'Communiquez-le a l\'employe puis demandez-lui de le changer.':
        'تم إنشاء الحساب: المعرف "%(identifiant)s" / كلمة المرور المؤقتة "%(motdepasse)s". أرسلها إلى الموظف واطلب منه تغييرها.',
    'Compte cree : identifiant "%(identifiant)s" / mot de passe temporaire "%(motdepasse)s".':
        'تم إنشاء الحساب: المعرف "%(identifiant)s" / كلمة المرور المؤقتة "%(motdepasse)s".',
    "Places dispo (reel)": "الأماكن المتاحة (فعلي)",
    "Origine": "المصدر",
    "App mobile": "تطبيق الجوال",
}

po = polib.pofile(FICHIER)
maj = 0
manquants = []

for francais, arabe in TRADUCTIONS.items():
    entree = po.find(francais)
    if entree:
        entree.msgstr = arabe
        maj += 1
    else:
        manquants.append(francais)

po.save(FICHIER)

print(f"{maj} traduction(s) mise(s) a jour dans {FICHIER}")
if manquants:
    print("Introuvables dans le fichier .po (verifie que makemessages a bien tourne avant) :")
    for m in manquants:
        print(f"  - {m}")
