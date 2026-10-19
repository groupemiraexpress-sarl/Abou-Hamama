"""
Console de l'administrateur de la plateforme (superutilisateur uniquement) :
voir toutes les entreprises, en creer une avec son PDG, reinitialiser l'acces d'un PDG,
suspendre ou reactiver une entreprise.
"""
from datetime import timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .models import Agence, Bus, Compagnie, Employe, Reservation, Voyage
from .services_plateforme import basculer_compagnie, creer_compagnie_avec_pdg, reinitialiser_acces_pdg, resume_entreprises


def superutilisateur_requis(vue):
    @staff_member_required
    @wraps(vue)
    def enveloppe(request, *args, **kwargs):
        if not request.user.is_superuser:
            return redirect('admin:index')
        return vue(request, *args, **kwargs)
    return enveloppe


@superutilisateur_requis
def plateforme(request):
    lignes, totaux = resume_entreprises()
    return render(request, 'transport/plateforme.html', {'lignes': lignes, 'totaux': totaux})


@superutilisateur_requis
def nouvelle_compagnie(request):
    valeurs, erreurs = {}, {}
    if request.method == 'POST':
        valeurs = {k: request.POST.get(k, '').strip() for k in (
            'nom', 'code', 'siege', 'telephone', 'nom_affiche', 'couleur', 'domaine',
            'pdg_nom', 'pdg_prenom', 'pdg_telephone')}
        try:
            compagnie, identifiant, mot_de_passe = creer_compagnie_avec_pdg(
                nom=valeurs['nom'], code=valeurs['code'], siege=valeurs['siege'], telephone=valeurs['telephone'],
                pdg_nom=valeurs['pdg_nom'], pdg_prenom=valeurs['pdg_prenom'], pdg_telephone=valeurs['pdg_telephone'],
                nom_affiche=valeurs['nom_affiche'], couleur=valeurs['couleur'] or '#261F64', domaine=valeurs['domaine'],
                logo=request.FILES.get('logo'),
            )
        except ValidationError as e:
            erreurs = {k: ' '.join(v) for k, v in e.message_dict.items()} if hasattr(e, 'error_dict') else {'': ' '.join(e.messages)}
        else:
            # page affichee une seule fois (pas de redirection) : le mot de passe temporaire n'est jamais conserve
            return render(request, 'transport/plateforme_acces.html', {
                'compagnie': compagnie, 'identifiant': identifiant, 'mot_de_passe': mot_de_passe, 'titre_page': _("Entreprise creee"),
            })
    return render(request, 'transport/plateforme_nouvelle.html', {'valeurs': valeurs, 'erreurs': erreurs})


@require_POST
@superutilisateur_requis
def reinitialiser_pdg(request, pk):
    compagnie = get_object_or_404(Compagnie, pk=pk)
    acces = reinitialiser_acces_pdg(compagnie)
    if acces is None:
        messages.error(request, _("Cette entreprise n'a pas de PDG avec un compte de connexion."))
        return redirect('transport:plateforme')
    identifiant, mot_de_passe = acces
    return render(request, 'transport/plateforme_acces.html', {
        'compagnie': compagnie, 'identifiant': identifiant, 'mot_de_passe': mot_de_passe, 'titre_page': _("Nouvel acces du PDG"),
    })


@require_POST
@superutilisateur_requis
def basculer(request, pk):
    compagnie = get_object_or_404(Compagnie, pk=pk)
    if compagnie.actif and Compagnie.objects.filter(actif=True).count() <= 1:
        messages.error(request, _("Impossible de suspendre la seule entreprise active."))
    elif basculer_compagnie(compagnie):
        messages.success(request, _("%(nom)s est reactivee.") % {'nom': compagnie.nom})
    else:
        messages.success(request, _("%(nom)s est suspendue : ses employes ne peuvent plus se connecter.") % {'nom': compagnie.nom})
    return redirect('transport:plateforme')
