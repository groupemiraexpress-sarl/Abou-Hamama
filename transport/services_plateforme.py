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
from .models import Compagnie, Employe
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
