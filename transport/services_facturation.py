"""
Facturation SaaS : abonnement mensuel fixe de chaque entreprise a la plateforme.

  - generer_factures_du_mois : une facture par entreprise active ayant un abonnement (jamais deux pour le meme mois) ;
  - enregistrer_paiement : paiement total ou partiel d'une facture ;
  - resume_facturation : chiffres du superviseur (a encaisser, en retard, encaisse ce mois) ;
  - envoyer_rappel : e-mail de rappel a l'entreprise (la suspension reste une decision manuelle du superviseur).
"""
import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils.translation import gettext as _

from .models import Compagnie, FactureAbonnement, PaiementAbonnement

DELAI_PAIEMENT_JOURS = 15


def premier_du_mois(jour=None):
    jour = jour or datetime.date.today()
    return jour.replace(day=1)


@transaction.atomic
def generer_factures_du_mois(periode=None):
    """Cree les factures du mois (par defaut le mois en cours). Renvoie la liste des factures creees ; relancer ne cree rien de plus."""
    periode = premier_du_mois(periode)
    creees = []
    for compagnie in Compagnie.objects.filter(actif=True, abonnement_montant__gt=0).order_by('id'):
        if FactureAbonnement.objects.filter(compagnie=compagnie, periode=periode).exists():
            continue
        emission = datetime.date.today()
        creees.append(FactureAbonnement.objects.create(
            compagnie=compagnie, periode=periode, montant=compagnie.abonnement_montant,
            date_emission=emission, date_echeance=emission + datetime.timedelta(days=DELAI_PAIEMENT_JOURS),
        ))
    return creees


@transaction.atomic
def enregistrer_paiement(facture, montant, mode='especes', reference='', date_paiement=None):
    """Enregistre un paiement ; refuse un montant nul ou superieur a ce qu'il reste a payer. Leve ValidationError."""
    try:
        montant = int(montant)
    except (TypeError, ValueError):
        raise ValidationError(_("Montant invalide."))
    if montant <= 0:
        raise ValidationError(_("Le montant doit etre superieur a zero."))
    if mode not in dict(PaiementAbonnement.MODE_CHOICES):
        raise ValidationError(_("Mode de paiement invalide."))
    facture = FactureAbonnement.objects.select_for_update().get(pk=facture.pk)
    if montant > facture.reste:
        raise ValidationError(_("Ce montant depasse ce qu'il reste a payer (%(reste)s FCFA).") % {'reste': facture.reste})
    return PaiementAbonnement.objects.create(
        facture=facture, montant=montant, mode=mode, reference=(reference or '').strip(),
        date_paiement=date_paiement or datetime.date.today(),
    )


def factures_impayees(compagnie=None):
    """Factures qui ne sont pas entierement payees (liste, car le reste se calcule sur les paiements)."""
    qs = FactureAbonnement.objects.select_related('compagnie').prefetch_related('paiements')
    if compagnie is not None:
        qs = qs.filter(compagnie=compagnie)
    return [f for f in qs if f.reste > 0]


def resume_facturation():
    """Totaux pour le superviseur : montant a encaisser, factures en retard, encaisse depuis le debut du mois."""
    impayees = factures_impayees()
    en_retard = [f for f in impayees if f.statut == 'retard']
    debut_mois = premier_du_mois()
    encaisse = PaiementAbonnement.objects.filter(date_paiement__gte=debut_mois).aggregate(t=Sum('montant'))['t'] or 0
    return {
        'a_encaisser': sum(f.reste for f in impayees),
        'nb_impayees': len(impayees),
        'en_retard': sum(f.reste for f in en_retard),
        'nb_en_retard': len(en_retard),
        'encaisse_mois': encaisse,
        'compagnies_en_retard': {f.compagnie_id for f in en_retard},
    }


def envoyer_rappel(compagnie):
    """Envoie par e-mail le detail des factures impayees. Renvoie True/False (False : pas d'adresse, rien a payer ou envoi echoue)."""
    from .email_brevo import envoyer_email
    impayees = factures_impayees(compagnie)
    if not compagnie.email or not impayees:
        return False
    nom_plateforme = getattr(settings, 'PLATEFORME_NOM', "Gestion d'agence")
    lignes = [
        _("- %(numero)s : %(reste)s FCFA a payer avant le %(date)s") % {
            'numero': f.numero, 'reste': f.reste, 'date': f.date_echeance.strftime('%d/%m/%Y')}
        for f in impayees
    ]
    total = sum(f.reste for f in impayees)
    corps = "\n\n".join([
        _("Bonjour,"),
        _("Voici les factures d'abonnement de %(nom)s qui restent a payer :") % {'nom': compagnie.nom_affiche or compagnie.nom},
        "\n".join(lignes),
        _("Total : %(total)s FCFA.") % {'total': total},
        _("Merci de regulariser votre situation pour continuer a utiliser la plateforme."),
        nom_plateforme,
    ])
    return envoyer_email(compagnie.email, _("Rappel : facture d'abonnement a payer"), corps, nom_expediteur=nom_plateforme)
