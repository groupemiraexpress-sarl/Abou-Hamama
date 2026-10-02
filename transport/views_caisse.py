"""
Caisse, depenses de voyage, dettes (billets non payes), changement de bus et
feuille chauffeur : les outils annexes de la vente de billets au guichet.

Tous les calculs d'argent sont faits ici, cote serveur (la page ne fait
qu'afficher). Un agent ne voit que son agence ; le PDG et le superutilisateur
voient tout (voir admin_filtres.voit_tout).
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .admin_filtres import agence_de, voit_tout
from .models import (
    Agence, Bus, Depense, MouvementCaisse, Reservation, SessionCaisse, Siege, Voyage,
)

POSTES_VENTE = ('pdg', 'responsable', 'secretaire', 'guichetier', 'caissier')
POSTES_CAISSE = ('pdg', 'responsable', 'secretaire', 'caissier')
POSTES_PLANNING_BUS = ('pdg', 'responsable', 'secretaire')


def _poste(user):
    employe = getattr(user, 'employe', None)
    return employe.poste if employe else None


def _employe(user):
    return getattr(user, 'employe', None)


def _a_le_droit(user, postes):
    return user.is_superuser or _poste(user) in postes


def _voyage_autorise(user, voyage_id):
    """Le voyage demande, s'il appartient a l'agence de l'utilisateur (sinon None)."""
    voyage = Voyage.objects.filter(id=voyage_id).select_related('bus__agence', 'trajet', 'chauffeur').first()
    if not voyage:
        return None
    if not voit_tout(user):
        agence = agence_de(user)
        if not agence or voyage.bus.agence_id != agence.id:
            return None
    return voyage


def _interdit():
    return JsonResponse({'erreur': _("Action non autorisee pour votre poste.")}, status=403)


# ---------------------------------------------------------------- depenses

def _depenses_json(voyage):
    liste = list(voyage.depenses.select_related('cree_par').order_by('date_creation'))
    return {
        'depenses': [{
            'id': d.id, 'libelle': d.libelle, 'montant': d.montant,
            'par': f"{d.cree_par.prenom} {d.cree_par.nom}" if d.cree_par else '',
            'heure': timezone.localtime(d.date_creation).strftime('%H:%M'),
        } for d in liste],
        'total': sum(d.montant for d in liste),
        'nombre': len(liste),
    }


@staff_member_required
def depenses_voyage(request, voyage_id):
    """GET : liste des depenses du voyage. POST (action=ajouter|supprimer) : les modifier."""
    if not _a_le_droit(request.user, POSTES_VENTE):
        return _interdit()
    voyage = _voyage_autorise(request.user, voyage_id)
    if not voyage:
        return JsonResponse({'erreur': _("Voyage introuvable (ou ne fait pas partie de votre agence).")}, status=404)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'ajouter':
            libelle = request.POST.get('libelle', '').strip()
            try:
                montant = int(request.POST.get('montant', '0'))
            except ValueError:
                montant = 0
            if not libelle or montant <= 0:
                return JsonResponse({'erreur': _("Indiquez le motif et un montant superieur a 0.")}, status=400)
            Depense.objects.create(voyage=voyage, libelle=libelle[:150], montant=montant, cree_par=_employe(request.user))
        elif action == 'supprimer':
            depense = voyage.depenses.filter(id=request.POST.get('id')).first()
            if not depense:
                return JsonResponse({'erreur': _("Depense introuvable.")}, status=404)
            # Un guichetier/caissier ne supprime que ses propres saisies.
            employe = _employe(request.user)
            if not (voit_tout(request.user) or _poste(request.user) in POSTES_PLANNING_BUS
                    or (employe and depense.cree_par_id == employe.id)):
                return _interdit()
            depense.delete()
        else:
            return JsonResponse({'erreur': 'action'}, status=400)
    return JsonResponse(_depenses_json(voyage))


# ------------------------------------------------------------ changer le bus

@staff_member_required
def changer_bus_voyage(request, voyage_id):
    """GET : bus possibles. POST (bus_id) : affecte un autre bus de l'agence au voyage."""
    if not _a_le_droit(request.user, POSTES_PLANNING_BUS):
        return _interdit()
    voyage = _voyage_autorise(request.user, voyage_id)
    if not voyage:
        return JsonResponse({'erreur': _("Voyage introuvable (ou ne fait pas partie de votre agence).")}, status=404)

    candidats = Bus.objects.filter(agence_id=voyage.bus.agence_id, statut='en_service').order_by('immatriculation')

    if request.method == 'GET':
        return JsonResponse({
            'bus_actuel': voyage.bus.immatriculation,
            'bus': [{'id': b.id, 'immatriculation': b.immatriculation, 'capacite': b.capacite} for b in candidats],
        })

    nouveau = candidats.filter(id=request.POST.get('bus_id')).first()
    if not nouveau:
        return JsonResponse({'erreur': _("Bus introuvable ou indisponible.")}, status=400)
    if nouveau.id == voyage.bus_id:
        return JsonResponse({'erreur': _("Ce bus est deja affecte a ce voyage.")}, status=400)

    with transaction.atomic():
        reservations = voyage.reservations.all()
        actives = reservations.exclude(statut__in=['annulee', 'remboursee'])
        if actives.count() > nouveau.capacite:
            return JsonResponse({'erreur': _("Ce bus est trop petit : %(n)s billet(s) deja vendu(s).") % {'n': actives.count()}}, status=400)
        if reservations.filter(siege__numero__gt=nouveau.capacite).exists():
            return JsonResponse({'erreur': _("Des billets existent deja sur des places au-dela de %(n)s : impossible de reduire le bus.") % {'n': nouveau.capacite}}, status=400)

        Siege.objects.filter(voyage=voyage, numero__gt=nouveau.capacite).delete()
        existants = set(Siege.objects.filter(voyage=voyage).values_list('numero', flat=True))
        Siege.objects.bulk_create([
            Siege(voyage=voyage, numero=n) for n in range(1, nouveau.capacite + 1) if n not in existants
        ])
        voyage.bus = nouveau
        if not voyage.ligne_id:
            voyage.places_disponibles = nouveau.capacite - actives.count()
        voyage.save()
    return JsonResponse({'ok': True, 'bus': nouveau.immatriculation, 'capacite': nouveau.capacite})


# --------------------------------------------------------- feuille chauffeur

@staff_member_required
def feuille_chauffeur(request, voyage_id):
    """Feuille de route imprimable (a enregistrer en PDF) : passagers, recettes, depenses."""
    if not _a_le_droit(request.user, POSTES_VENTE):
        return redirect('admin:index')
    voyage = _voyage_autorise(request.user, voyage_id)
    if not voyage:
        return redirect('transport:vendre_billet')

    billets = list(
        voyage.reservations.exclude(statut__in=['annulee', 'remboursee'])
        .select_related('siege', 'commissionnaire', 'cree_par').order_by('siege__numero', 'id')
    )
    payes = [b for b in billets if b.statut == 'payee']
    depenses = list(voyage.depenses.order_by('date_creation'))
    total_recette = sum(b.montant_total for b in payes)
    total_depenses = sum(d.montant for d in depenses)
    commissions = sum(b.commissionnaire.commission_par_billet for b in payes if b.commissionnaire_id)
    contexte = {
        'voyage': voyage, 'billets': billets,
        'nb_payes': len(payes), 'nb_non_payes': len(billets) - len(payes),
        'nb_gratuits': sum(1 for b in payes if b.montant_total == 0),
        'total_recette': total_recette, 'depenses': depenses, 'total_depenses': total_depenses,
        'commissions': commissions, 'net': total_recette - total_depenses - commissions,
        'non_paye_montant': sum(b.montant_total for b in billets if b.statut != 'payee'),
    }
    return render(request, 'transport/feuille_chauffeur.html', contexte)


# -------------------------------------------------------------------- dettes

@staff_member_required
def dettes(request):
    """Billets vendus 'Non paye' : liste, recherche, encaissement ou annulation."""
    if not _a_le_droit(request.user, POSTES_VENTE):
        return redirect('admin:index')
    employe = _employe(request.user)

    billets = Reservation.objects.filter(statut='en_attente').select_related('voyage__trajet', 'voyage__bus', 'siege', 'cree_par')
    if not voit_tout(request.user):
        agence = agence_de(request.user)
        billets = billets.filter(agence=agence) if agence else billets.none()
        # Un guichetier ne gere que les dettes de ses propres ventes.
        if _poste(request.user) == 'guichetier' and employe:
            billets = billets.filter(cree_par=employe)

    message = ''
    if request.method == 'POST':
        billet = billets.filter(id=request.POST.get('id')).first()
        action = request.POST.get('action')
        if not billet:
            message = _("Billet introuvable.")
        elif action == 'encaisser':
            mode = request.POST.get('mode_paiement', 'especes')
            if mode not in dict(Reservation.MODE_PAIEMENT_CHOICES):
                mode = 'especes'
            billet.statut = 'payee'
            billet.mode_paiement = mode
            billet.date_paiement = timezone.now()
            billet.modifie_par = employe
            billet.save()
            message = _("Billet %(n)s encaisse.") % {'n': billet.numero_reservation}
        elif action == 'annuler':
            # Annuler libere la place : on restitue la place au voyage, comme l'admin.
            billet.statut = 'annulee'
            billet.modifie_par = employe
            billet.save()
            if not billet.voyage.ligne_id:
                Voyage.objects.filter(pk=billet.voyage_id).update(
                    places_disponibles=billet.voyage.places_disponibles + billet.nombre_places)
            message = _("Billet %(n)s annule.") % {'n': billet.numero_reservation}
        billets = billets.exclude(statut__in=['payee', 'annulee'])

    q = request.GET.get('q', '').strip()
    if q:
        from django.db.models import Q
        billets = billets.filter(
            Q(voyageur_nom__icontains=q) | Q(voyageur_telephone__icontains=q)
            | Q(numero_reservation__icontains=q) | Q(client__nom__icontains=q))
    billets = billets.order_by('voyage__date_depart', 'date_reservation')
    liste = list(billets)
    return render(request, 'transport/dettes.html', {
        'billets': liste, 'q': q, 'message': message,
        'total': sum(b.montant_total for b in liste),
        'modes': Reservation.MODE_PAIEMENT_CHOICES,
    })


# --------------------------------------------------------------------- caisse

def resume_session(session):
    """Tous les chiffres d'une session de caisse (agence entiere, sur la periode de la session)."""
    debut, fin = session.ouverte_le, session.fin
    payes = (Reservation.objects.filter(agence=session.agence, statut='payee')
             .annotate(quand=Coalesce('date_paiement', 'date_reservation'))
             .filter(quand__gte=debut, quand__lte=fin))
    par_mode = {m: 0 for m, _libelle in Reservation.MODE_PAIEMENT_CHOICES}
    for ligne in payes.values('mode_paiement').annotate(t=Sum('montant_total')):
        par_mode[ligne['mode_paiement'] or 'especes'] = par_mode.get(ligne['mode_paiement'] or 'especes', 0) + (ligne['t'] or 0)
    total_billets = sum(par_mode.values())

    par_vendeur = [{
        'nom': f"{l['cree_par__prenom']} {l['cree_par__nom']}" if l['cree_par__nom'] else '—',
        'billets': l['n'], 'montant': l['t'] or 0,
    } for l in payes.values('cree_par__nom', 'cree_par__prenom').annotate(n=Count('id'), t=Sum('montant_total')).order_by('-t')]

    commissions = sum(
        r.commissionnaire.commission_par_billet
        for r in payes.filter(commissionnaire__isnull=False).select_related('commissionnaire'))

    depenses = Depense.objects.filter(voyage__bus__agence=session.agence, date_creation__gte=debut, date_creation__lte=fin)
    total_depenses = depenses.aggregate(t=Sum('montant'))['t'] or 0
    mouvements = session.mouvements.all()
    encaissements = mouvements.filter(type_mouvement='encaissement').aggregate(t=Sum('montant'))['t'] or 0
    decaissements = mouvements.filter(type_mouvement='decaissement').aggregate(t=Sum('montant'))['t'] or 0

    non_payes = Reservation.objects.filter(agence=session.agence, statut='en_attente', date_reservation__gte=debut, date_reservation__lte=fin)

    especes_attendues = (session.fond_initial + par_mode.get('especes', 0)
                         + encaissements - decaissements - total_depenses)
    return {
        'nb_billets': payes.count(),
        'nb_gratuits': payes.filter(montant_total=0).count(),
        'par_mode': [(libelle, par_mode.get(m, 0)) for m, libelle in Reservation.MODE_PAIEMENT_CHOICES],
        'total_billets': total_billets,
        'par_vendeur': par_vendeur,
        'commissions': commissions,
        'depenses': list(depenses.select_related('voyage__trajet', 'cree_par').order_by('date_creation')),
        'total_depenses': total_depenses,
        'encaissements': encaissements,
        'decaissements': decaissements,
        'mouvements': list(mouvements.select_related('cree_par').order_by('date_creation')),
        'nb_non_payes': non_payes.count(),
        'montant_non_paye': non_payes.aggregate(t=Sum('montant_total'))['t'] or 0,
        'net': total_billets + encaissements - decaissements - total_depenses,
        'especes_attendues': especes_attendues,
    }


def _entier(valeur, defaut=0):
    try:
        return max(int(str(valeur).strip() or defaut), 0)
    except ValueError:
        return defaut


@staff_member_required
def caisse(request):
    """Ouverture / pause / cloture de la caisse de l'agence + encaissements et decaissements."""
    if not _a_le_droit(request.user, POSTES_CAISSE):
        return redirect('admin:index')
    employe = _employe(request.user)

    # Agence : celle de l'employe ; le PDG / superutilisateur choisit.
    agences = Agence.objects.filter(actif=True).order_by('ville', 'nom') if voit_tout(request.user) else None
    agence = agence_de(request.user)
    if voit_tout(request.user):
        agence = agences.filter(id=request.GET.get('agence') or request.POST.get('agence')).first() or agence or agences.first()
    if not agence:
        return render(request, 'transport/caisse.html', {'sans_agence': True})

    session = SessionCaisse.objects.filter(agence=agence).exclude(statut='cloturee').order_by('-ouverte_le').first()
    erreur = message = ''

    if request.method == 'POST':
        action = request.POST.get('action')
        maintenant = timezone.now()
        if action == 'ouvrir':
            if session:
                erreur = _("Une caisse est deja ouverte pour cette agence.")
            else:
                session = SessionCaisse.objects.create(
                    agence=agence, employe=employe, fond_initial=_entier(request.POST.get('fond_initial')))
                message = _("Caisse ouverte.")
        elif not session:
            erreur = _("Aucune caisse ouverte.")
        elif action == 'pause' and session.statut == 'ouverte':
            session.statut, session.pause_depuis = 'pause', maintenant
            session.save()
            message = _("Caisse en pause.")
        elif action == 'reprendre' and session.statut == 'pause':
            if session.pause_depuis:
                session.secondes_pause += int((maintenant - session.pause_depuis).total_seconds())
            session.statut, session.pause_depuis = 'ouverte', None
            session.save()
            message = _("Caisse reprise.")
        elif action in ('encaissement', 'decaissement'):
            montant = _entier(request.POST.get('montant'))
            motif = request.POST.get('motif', '').strip()
            if session.statut == 'pause':
                erreur = _("La caisse est en pause : reprenez-la d'abord.")
            elif montant <= 0 or not motif:
                erreur = _("Indiquez le motif et un montant superieur a 0.")
            else:
                MouvementCaisse.objects.create(
                    session=session, type_mouvement=action, montant=montant, motif=motif[:150], cree_par=employe)
                message = _("Mouvement enregistre.")
        elif action == 'cloturer':
            if session.statut == 'pause' and session.pause_depuis:
                session.secondes_pause += int((maintenant - session.pause_depuis).total_seconds())
                session.pause_depuis = None
            session.statut, session.cloturee_le = 'cloturee', maintenant
            attendu = resume_session(session)['especes_attendues']
            texte = request.POST.get('montant_compte', '').strip()
            if texte:
                session.montant_compte = _entier(texte)
                session.ecart = session.montant_compte - attendu
            session.notes = request.POST.get('notes', '').strip()
            session.save()
            message = _("Caisse cloturee.")
            session = None
        else:
            erreur = _("Action impossible dans l'etat actuel de la caisse.")

    # Session affichee : la session en cours, sinon la derniere cloturee.
    affichee = session or SessionCaisse.objects.filter(agence=agence).order_by('-ouverte_le').first()
    return render(request, 'transport/caisse.html', {
        'agence': agence, 'agences': agences, 'session': session, 'affichee': affichee,
        'resume': resume_session(affichee) if affichee else None,
        'historique': SessionCaisse.objects.filter(agence=agence, statut='cloturee').select_related('employe').order_by('-ouverte_le')[:10],
        'erreur': erreur, 'message': message,
    })
