"""Facturation SaaS : ecrans du superviseur (factures, paiements, rappels) et ecran de l'abonnement du PDG."""
from functools import wraps

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .models import Compagnie, FactureAbonnement, PaiementAbonnement
from .services_facturation import enregistrer_paiement, envoyer_rappel, generer_factures_du_mois, resume_facturation
from .tenant import compagnie_de, portee
from .views_plateforme import superutilisateur_requis

FILTRES = ('', 'impayees', 'retard', 'payees')


def _factures(user):
    return portee(user, FactureAbonnement).select_related('compagnie').prefetch_related('paiements')


@superutilisateur_requis
def facturation(request):
    filtre = request.GET.get('statut', '') if request.GET.get('statut', '') in FILTRES else ''
    factures = list(_factures(request.user))
    if filtre == 'impayees':
        factures = [f for f in factures if f.reste > 0]
    elif filtre == 'retard':
        factures = [f for f in factures if f.statut == 'retard']
    elif filtre == 'payees':
        factures = [f for f in factures if f.reste == 0]
    sans_abonnement = Compagnie.objects.filter(actif=True, abonnement_montant=0).order_by('nom')
    return render(request, 'transport/facturation.html', {
        'factures': factures, 'filtre': filtre, 'resume': resume_facturation(),
        'modes': PaiementAbonnement.MODE_CHOICES, 'sans_abonnement': sans_abonnement,
    })


@require_POST
@superutilisateur_requis
def generer_factures(request):
    creees = generer_factures_du_mois()
    if creees:
        messages.success(request, _("%(n)s facture(s) creee(s) pour ce mois.") % {'n': len(creees)})
    else:
        messages.info(request, _("Rien a creer : toutes les factures de ce mois existent deja (ou aucune entreprise n'a d'abonnement)."))
    return redirect('transport:facturation')


@require_POST
@superutilisateur_requis
def paiement_facture(request, pk):
    facture = get_object_or_404(FactureAbonnement, pk=pk)
    try:
        enregistrer_paiement(facture, request.POST.get('montant'), request.POST.get('mode', 'especes'), request.POST.get('reference', ''))
    except ValidationError as e:
        messages.error(request, ' '.join(e.messages))
    else:
        messages.success(request, _("Paiement enregistre pour %(numero)s.") % {'numero': facture.numero})
    return redirect('transport:facturation')


@require_POST
@superutilisateur_requis
def rappel_entreprise(request, pk):
    compagnie = get_object_or_404(Compagnie, pk=pk)
    if not compagnie.email:
        messages.error(request, _("%(nom)s n'a pas d'adresse e-mail : ajoutez-la dans la fiche de l'entreprise.") % {'nom': compagnie.nom})
    elif envoyer_rappel(compagnie):
        messages.success(request, _("Rappel envoye a %(email)s.") % {'email': compagnie.email})
    else:
        messages.error(request, _("Aucun rappel envoye : pas de facture a payer, ou l'envoi a echoue."))
    return redirect('transport:facturation')


def _pdg_ou_superutilisateur(vue):
    @staff_member_required
    @wraps(vue)
    def enveloppe(request, *args, **kwargs):
        employe = getattr(request.user, 'employe', None)
        if not request.user.is_superuser and (employe is None or employe.poste != 'pdg'):
            return redirect('admin:index')
        return vue(request, *args, **kwargs)
    return enveloppe


@_pdg_ou_superutilisateur
def mon_abonnement(request):
    """Le PDG voit les factures de SON entreprise (lecture seule)."""
    compagnie = compagnie_de(request.user)
    if compagnie is None:
        return redirect('transport:facturation')
    return render(request, 'transport/mon_abonnement.html', {'compagnie': compagnie, 'factures': list(_factures(request.user))})


@_pdg_ou_superutilisateur
def facture_imprimer(request, pk):
    facture = get_object_or_404(_factures(request.user), pk=pk)
    return render(request, 'transport/facture_abonnement.html', {'facture': facture})
