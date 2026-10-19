"""
Operations de l'administrateur de la plateforme : creer une entreprise avec son PDG,
reinitialiser l'acces d'un PDG, suspendre ou reactiver une entreprise.
Utilise par la console plateforme (ecrans) et par la commande creer_compagnie.
"""
import secrets
import string

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction

from .admin_filtres import assigner_groupe_selon_poste
from datetime import timedelta

from django.db.models import Max
from django.utils import timezone

from .models import Agence, Bus, Compagnie, Employe, Reservation, Voyage
from .tenant import identifiant_employe


def mot_de_passe_temporaire(longueur=10):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(longueur))


@transaction.atomic
def creer_compagnie_avec_pdg(*, nom, code, siege, telephone, pdg_nom, pdg_prenom, pdg_telephone,
                             nom_affiche='', couleur='#261F64', domaine='', logo=None):
    """Cree la compagnie et son PDG. Renvoie (compagnie, identifiant, mot_de_passe_temporaire). Leve ValidationError."""
    erreurs = {}
    for champ, valeur in (('nom', nom), ('code', code), ('siege', siege), ('telephone', telephone),
                          ('pdg_nom', pdg_nom), ('pdg_prenom', pdg_prenom), ('pdg_telephone', pdg_telephone)):
        if not str(valeur or '').strip():
            erreurs[champ] = "Ce champ est obligatoire."
    if erreurs:
        raise ValidationError(erreurs)

    compagnie = Compagnie(
        nom=nom.strip(), code=code.strip().lower(), nom_affiche=nom_affiche.strip(), siege_social=siege.strip(),
        telephone=telephone.strip(), couleur_principale=couleur or '#261F64', domaine=domaine,
        pied_de_page=f"Agence {nom.strip()}",
    )
    if logo:
        compagnie.logo = logo
    try:
        compagnie.full_clean()
    except ValidationError as e:
        raise ValidationError({('siege' if k == 'siege_social' else k): v for k, v in e.message_dict.items()})

    identifiant = identifiant_employe(compagnie, pdg_telephone.strip())
    if User.objects.filter(username=identifiant).exists():
        raise ValidationError({'pdg_telephone': f"L'identifiant {identifiant} existe deja."})

    compagnie.save()
    mot_de_passe = mot_de_passe_temporaire()
    user = User.objects.create_user(username=identifiant, password=mot_de_passe, is_staff=True)
    Employe.objects.create(user=user, compagnie=compagnie, nom=pdg_nom.strip(), prenom=pdg_prenom.strip(),
                           telephone=pdg_telephone.strip(), poste='pdg')
    assigner_groupe_selon_poste(user, 'pdg')
    return compagnie, identifiant, mot_de_passe


def reinitialiser_acces_pdg(compagnie):
    """Nouveau mot de passe temporaire pour le PDG de la compagnie. Renvoie (identifiant, mot_de_passe) ou None si pas de PDG."""
    pdg = Employe.objects.filter(compagnie=compagnie, poste='pdg', user__isnull=False).select_related('user').first()
    if pdg is None:
        return None
    mot_de_passe = mot_de_passe_temporaire()
    pdg.user.set_password(mot_de_passe)
    pdg.user.save()
    return pdg.user.username, mot_de_passe


def basculer_compagnie(compagnie):
    """Suspend une compagnie active ou reactive une compagnie suspendue. Renvoie le nouvel etat (actif)."""
    compagnie.actif = not compagnie.actif
    compagnie.save(update_fields=['actif'])
    return compagnie.actif


def resume_entreprises():
    """Une ligne par entreprise (activite des 30 derniers jours, derniere connexion...) et des totaux pour toute la plateforme."""
    aujourd_hui = timezone.now().date()
    il_y_a_30_jours = timezone.now() - timedelta(days=30)
    lignes = []
    for c in Compagnie.objects.order_by('nom'):
        lignes.append({
            'c': c,
            'pdg': Employe.objects.filter(compagnie=c, poste='pdg').select_related('user').first(),
            'agences': Agence.objects.filter(compagnie=c).count(),
            'employes': Employe.objects.filter(compagnie=c, actif=True).count(),
            'bus': Bus.objects.filter(compagnie=c).count(),
            'voyages_a_venir': Voyage.objects.filter(bus__compagnie=c, date_depart__gte=aujourd_hui).count(),
            'reservations_30j': Reservation.objects.filter(voyage__bus__compagnie=c, date_reservation__gte=il_y_a_30_jours).count(),
            'derniere_connexion': User.objects.filter(employe__compagnie=c).aggregate(d=Max('last_login'))['d'],
        })
    totaux = {
        'actives': sum(1 for l in lignes if l['c'].actif),
        'suspendues': sum(1 for l in lignes if not l['c'].actif),
        'employes': sum(l['employes'] for l in lignes),
        'voyages_a_venir': sum(l['voyages_a_venir'] for l in lignes),
        'reservations_30j': sum(l['reservations_30j'] for l in lignes),
    }
    return lignes, totaux
