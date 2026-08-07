import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from transport.models import QuestionFAQ

QUESTIONS = [
    ("Comment reserver un voyage ?", "Depuis l'accueil, appuyez sur \"Voyager\", choisissez votre voyage, puis \"Choisir une place\". Selectionnez votre siege sur le plan, remplissez vos informations et confirmez."),
    ("Comment choisir ma place ?", "Sur le plan du bus, les sieges verts sont libres, les rouges sont occupes. Appuyez sur un siege vert pour le choisir (il devient blanc). Vous pouvez choisir plusieurs places."),
    ("Puis-je reserver pour plusieurs personnes ?", "Oui. Selectionnez plusieurs sieges, puis remplissez les informations de chaque voyageur, un par un. Tous les billets apparaitront dans \"Mes billets\"."),
    ("Comment envoyer un colis ?", "Dans le menu, appuyez sur \"Envoyer un colis\". Remplissez le formulaire (destinataire, agences, contenu, poids estime). Presentez-vous ensuite a l'agence avec votre colis : l'agent pesera le colis et fixera le prix definitif."),
    ("Comment envoyer de l'argent ?", "Dans le menu, appuyez sur \"Envoyer de l'argent\". Remplissez le formulaire (beneficiaire, agences, montant). Presentez-vous ensuite a l'agence avec l'argent et une piece d'identite."),
    ("Ou trouver mon code de suivi ?", "Dans le menu, ouvrez \"Mes demandes\". Une fois votre demande validee par l'agence, le code de suivi (COL- ou TRF-) s'affiche sur la demande."),
    ("Comment suivre un colis ou un transfert ?", "Depuis l'accueil, appuyez sur \"Suivre un colis\" ou \"Suivre un transfert\", entrez votre code de suivi et appuyez sur Rechercher."),
    ("Quelle piece d'identite faut-il ?", "Vous pouvez utiliser une carte nationale d'identite, un passeport, un acte de naissance, une carte professionnelle ou un permis de conduire. Une piece est demandee pour chaque voyageur."),
    ("Comment retrouver mes billets ?", "Connectez-vous a votre compte, puis ouvrez \"Mes billets\" dans le menu. Vous y verrez toutes vos reservations avec le numero de siege et le voyageur."),
    ("Comment noter mon voyage ?", "Une fois votre voyage termine, ouvrez \"Mes billets\" : un bouton \"Noter ce voyage\" apparait sur votre billet. Donnez une note de 1 a 5 etoiles et repondez aux questions sur la qualite du service."),
    ("Comment fonctionne le parrainage ?", "Partagez votre code de parrainage depuis votre profil. Quand un ami s'inscrit avec votre code et paie son premier billet, il gagne 25 points et vous en gagnez 50."),
    ("Comment contacter l'agence ?", "Dans le menu, appuyez sur \"Nous contacter\". Vous pourrez appeler directement chaque agence ou ecrire sur WhatsApp."),
]

crees = 0
for i, (q, r) in enumerate(QUESTIONS, start=1):
    _, cree = QuestionFAQ.objects.get_or_create(question=q, defaults={'reponse': r, 'ordre': i * 10})
    if cree:
        crees += 1

print(f"{crees} question(s) FAQ creee(s). Total : {QuestionFAQ.objects.count()}")