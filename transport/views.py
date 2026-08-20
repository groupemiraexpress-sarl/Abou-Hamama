from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.utils import timezone
from .models import Voyage, Client, Reservation, Agence, Chauffeur, Employe, Colis, TransfertArgent
from django.urls import reverse


@staff_member_required
def api_stats_tableau_bord(request):
    """
    Renvoie les chiffres du tableau de bord (admin) en JSON, pour permettre
    a la page d'accueil de l'admin de se rafraichir toute seule sans recharger
    toute la page (juste les chiffres). Reutilise exactement le meme calcul
    que la page d'accueil (memes filtres agence/zone/poste par utilisateur).
    """
    from .admin_stats import statistiques_tableau_bord
    return JsonResponse(statistiques_tableau_bord(request.user))


@staff_member_required
def vendre_billet(request):
    """
    Interface guichetier : vendre un ou plusieurs billets,
    avec une identite distincte pour chaque passager.
    Accessible au PDG, au Responsable d'agence, a la Secretaire, au
    Guichetier et au Caissier uniquement (memes postes que le raccourci
    "Vendre un billet" sur le tableau de bord). Les autres postes
    (responsable planning, agent colis, RH, comptable, etc.) ne vendent
    pas de billets.
    """
    employe = getattr(request.user, 'employe', None)
    poste = employe.poste if employe else None
    autorise = request.user.is_superuser or poste in ('pdg', 'responsable', 'secretaire', 'guichetier', 'caissier')

    if not autorise:
        return redirect('admin:index')

    voyages = Voyage.objects.filter(
        statut='programme',
        date_depart__gte=timezone.now().date(),
        places_disponibles__gt=0,
    ).order_by('date_depart', 'heure_depart')

    contexte = {'voyages': voyages, 'employe': employe}

    if request.method == 'POST':
        voyage_id = request.POST.get('voyage')
        client_nom = request.POST.get('client_nom', '').strip()
        client_telephone = request.POST.get('client_telephone', '').strip()
        nombre_places = request.POST.get('nombre_places', '1').strip()
        mode_paiement = request.POST.get('mode_paiement', 'especes')

        if not voyage_id or not client_nom or not client_telephone:
            contexte['erreur'] = "Veuillez remplir tous les champs obligatoires."
            return render(request, 'transport/vendre_billet.html', contexte)

        try:
            nombre_places = int(nombre_places)
        except ValueError:
            nombre_places = 1
        if nombre_places < 1:
            nombre_places = 1

        voyage = Voyage.objects.filter(id=voyage_id).first()
        if not voyage:
            contexte['erreur'] = "Voyage introuvable."
            return render(request, 'transport/vendre_billet.html', contexte)

        if nombre_places > voyage.places_disponibles:
            contexte['erreur'] = f"Plus que {voyage.places_disponibles} place(s) disponible(s)."
            return render(request, 'transport/vendre_billet.html', contexte)

        passagers = []
        for i in range(1, nombre_places + 1):
            nom_p = request.POST.get(f'passager_nom_{i}', '').strip()
            prenom_p = request.POST.get(f'passager_prenom_{i}', '').strip()
            telephone_p = request.POST.get(f'passager_telephone_{i}', '').strip()
            type_piece_p = request.POST.get(f'passager_type_piece_{i}', '').strip()
            numero_piece_p = request.POST.get(f'passager_numero_piece_{i}', '').strip()

            if not nom_p:
                nom_p = client_nom if i == 1 else f"{client_nom} (passager {i})"
            if not telephone_p:
                telephone_p = client_telephone

            passagers.append({
                'nom': nom_p,
                'prenom': prenom_p,
                'telephone': telephone_p,
                'type_piece': type_piece_p,
                'numero_piece': numero_piece_p,
            })

        client, cree = Client.objects.get_or_create(
            telephone=client_telephone,
            defaults={'nom': client_nom},
        )

        reservations_creees = []
        try:
            for p in passagers:
                reservation = Reservation.objects.create(
                    client=client,
                    voyage=voyage,
                    agence=employe.agence if employe else None,
                    nombre_places=1,
                    voyageur_nom=p['nom'],
                    voyageur_prenom=p['prenom'],
                    voyageur_telephone=p['telephone'],
                    voyageur_type_piece=p['type_piece'],
                    voyageur_numero_piece=p['numero_piece'],
                    statut='payee',
                    mode_paiement=mode_paiement,
                    cree_par=employe,
                )
                reservations_creees.append(reservation)
        except ValueError as e:
            contexte['erreur'] = str(e)
            return render(request, 'transport/vendre_billet.html', contexte)

        ids = ','.join(str(r.id) for r in reservations_creees)
        return redirect(f"{reverse('transport:billets_confirmes')}?ids={ids}")

    return render(request, 'transport/vendre_billet.html', contexte)


@staff_member_required
def billets_confirmes(request):
    """Affiche le recu apres la vente d'un ou plusieurs billets."""
    ids_param = request.GET.get('ids', '')
    ids = [int(i) for i in ids_param.split(',') if i.isdigit()]
    reservations = Reservation.objects.filter(id__in=ids).select_related(
        'voyage', 'voyage__trajet', 'client'
    )
    montant_total = sum(r.montant_total for r in reservations)
    return render(request, 'transport/billets_confirmes.html', {
        'reservations': reservations,
        'montant_total': montant_total,
    })


@staff_member_required
def billet_confirme(request, reservation_id):
    """Affiche le recu apres la vente d'un billet (ancienne route, gardee par securite)."""
    reservation = Reservation.objects.filter(id=reservation_id).first()
    return render(request, 'transport/billet_confirme.html', {'reservation': reservation})


@staff_member_required
def recu_colis(request, colis_id):
    """Affiche un recu imprimable pour un colis (comme le recu de billet)."""
    colis = Colis.objects.filter(id=colis_id).select_related('agence_depart', 'agence_arrivee').first()
    return render(request, 'transport/recu_colis.html', {'colis': colis})


@staff_member_required
def recu_transfert(request, transfert_id):
    """Affiche un recu imprimable pour un transfert d'argent (comme le recu de billet)."""
    transfert = TransfertArgent.objects.filter(id=transfert_id).select_related('agence_depart', 'agence_retrait').first()
    return render(request, 'transport/recu_transfert.html', {'transfert': transfert})


# Pour chaque poste, quelles sections de transactions sont pertinentes sur
# sa page "Mon activite" (on ne montre pas les billets a un agent colis,
# ni les colis/transferts a un guichetier : chacun voit son propre metier).
SECTIONS_ACTIVITE_PAR_POSTE = {
    'pdg': {'billets', 'colis', 'transferts'},
    'responsable': {'billets', 'colis', 'transferts'},
    'secretaire': {'billets'},
    'guichetier': {'billets'},
    'caissier': {'billets'},
    'agent_colis': {'colis'},
    'agent_transfert': {'transferts'},
}


@staff_member_required
def historique_employe(request):
    """
    Page dediee (tous postes) : l'activite d'un employe pour une journee
    donnee (billets vendus, colis enregistres/remis, transferts enregistres/
    retires), comme une archive professionnelle du travail du jour.

    Chacun voit uniquement sa propre activite (par exemple, l'agent colis
    ne voit que ce que lui-meme a enregistre). Seuls le PDG/superutilisateur
    et le Responsable d'agence peuvent choisir un autre employe et voir ce
    que celui-ci a genere (toute la compagnie pour le PDG, leur agence pour
    le responsable). Cette page ne concerne pas le Responsable planning (il
    supervise une zone, pas le personnel des agences) : il n'y a pas acces.

    Les sections affichees (billets / colis / transferts) dependent du
    poste de l'employe consulte, pas du poste de la personne connectee :
    un responsable qui consulte la fiche d'un agent colis ne voit que la
    section colis, meme si lui-meme a acces a tout sur sa propre fiche.
    """
    from datetime import datetime
    from .admin_filtres import voit_tout, agence_de

    employe_connecte = getattr(request.user, 'employe', None)
    poste_connecte = employe_connecte.poste if employe_connecte else None
    tout_voir = voit_tout(request.user)

    if not tout_voir and poste_connecte == 'resp_planning':
        return redirect('admin:index')

    peut_superviser = tout_voir or poste_connecte == 'responsable'

    if tout_voir:
        employes_visibles = Employe.objects.filter(actif=True).order_by('agence__ville', 'nom')
    elif poste_connecte == 'responsable':
        agence = agence_de(request.user)
        employes_visibles = Employe.objects.filter(actif=True, agence=agence).order_by('nom') if agence else Employe.objects.none()
    else:
        employes_visibles = Employe.objects.filter(pk=employe_connecte.pk) if employe_connecte else Employe.objects.none()

    employe_id = request.GET.get('employe')
    employe_cible = None
    if peut_superviser and employe_id:
        employe_cible = employes_visibles.filter(pk=employe_id).first()
    if not employe_cible:
        employe_cible = employe_connecte

    date_str = request.GET.get('date')
    try:
        date_choisie = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.now().date()
    except ValueError:
        date_choisie = timezone.now().date()

    poste_cible = employe_cible.poste if employe_cible else None
    sections_actives = set(SECTIONS_ACTIVITE_PAR_POSTE.get(poste_cible, ()))
    if not sections_actives and tout_voir and (employe_cible is None or employe_cible == employe_connecte and poste_cible is None):
        # Superutilisateur sans fiche Employe liee : on lui montre tout par securite.
        sections_actives = {'billets', 'colis', 'transferts'}

    contexte = {
        'employes_visibles': employes_visibles if peut_superviser else None,
        'employe_cible': employe_cible,
        'date_choisie': date_choisie,
        'peut_superviser': peut_superviser,
        'voit_billets': 'billets' in sections_actives,
        'voit_colis': 'colis' in sections_actives,
        'voit_transferts': 'transferts' in sections_actives,
    }

    if not employe_cible:
        return render(request, 'transport/historique_employe.html', contexte)

    reservations = Reservation.objects.filter(
        cree_par=employe_cible, date_reservation__date=date_choisie
    ).select_related('voyage', 'voyage__trajet', 'client').order_by('date_reservation')
    colis_enregistres = Colis.objects.filter(
        cree_par=employe_cible, date_enregistrement__date=date_choisie
    ).order_by('date_enregistrement')
    colis_remis = Colis.objects.filter(
        modifie_par=employe_cible, statut='livre', date_livraison__date=date_choisie
    ).order_by('date_livraison')
    transferts_enregistres = TransfertArgent.objects.filter(
        cree_par=employe_cible, date_envoi__date=date_choisie
    ).order_by('date_envoi')
    transferts_retires = TransfertArgent.objects.filter(
        modifie_par=employe_cible, statut='retire', date_retrait__date=date_choisie
    ).order_by('date_retrait')

    montant_billets = sum(r.montant_total for r in reservations.filter(statut='payee'))
    montant_colis = sum(c.prix for c in colis_enregistres)
    montant_transferts = sum(t.frais for t in transferts_enregistres)
    total_genere = montant_billets + montant_colis + montant_transferts

    contexte.update({
        'reservations': reservations,
        'colis_enregistres': colis_enregistres,
        'colis_remis': colis_remis,
        'transferts_enregistres': transferts_enregistres,
        'transferts_retires': transferts_retires,
        'montant_billets': montant_billets,
        'montant_colis': montant_colis,
        'montant_transferts': montant_transferts,
        'total_genere': total_genere,
    })
    return render(request, 'transport/historique_employe.html', contexte)


@staff_member_required
def liste_billets(request):
    """
    Liste des billets vendus.
    - Guichetier : voit SES propres ventes uniquement
    - Responsable : voit tous les billets de son agence (+ peut modifier)
    - PDG / admin : voient tout (+ peuvent modifier)
    """
    employe = getattr(request.user, 'employe', None)
    est_superuser = request.user.is_superuser
    poste = employe.poste if employe else None

    peut_modifier = est_superuser or poste in ('pdg', 'responsable')

    billets = Reservation.objects.filter(statut='payee').select_related(
        'client', 'voyage', 'voyage__trajet', 'agence', 'cree_par'
    )

    if est_superuser or poste == 'pdg':
        pass
    elif poste == 'responsable':
        if employe and employe.agence:
            billets = billets.filter(agence=employe.agence)
        else:
            billets = billets.none()
    else:
        if employe:
            billets = billets.filter(cree_par=employe)
        else:
            billets = billets.none()

    billets = billets.order_by('-date_reservation')

    mes_ventes = None
    if poste == 'guichetier' and employe:
        mes_ventes = billets.count()

    contexte = {
        'billets': billets,
        'peut_modifier': peut_modifier,
        'employe': employe,
        'mes_ventes': mes_ventes,
        'poste': poste,
    }

    return render(request, 'transport/liste_billets.html', contexte)


@staff_member_required
def modifier_billet(request, reservation_id):
    """
    Modifier le statut d'un billet.
    - Responsable : peut annuler
    - PDG / admin : peut annuler ET rembourser
    """
    employe = getattr(request.user, 'employe', None)
    est_superuser = request.user.is_superuser
    poste = employe.poste if employe else None

    peut_modifier = est_superuser or poste in ('pdg', 'responsable')
    if not peut_modifier:
        return redirect('transport:liste_billets')

    reservation = Reservation.objects.filter(id=reservation_id).first()
    if not reservation:
        return redirect('transport:liste_billets')

    peut_rembourser = est_superuser or poste == 'pdg'

    statuts = [('payee', 'Payee'), ('annulee', 'Annulee')]
    if peut_rembourser:
        statuts.append(('remboursee', 'Remboursee'))

    contexte = {
        'reservation': reservation,
        'statuts': statuts,
        'peut_rembourser': peut_rembourser,
        'employe': employe,
    }

    if request.method == 'POST':
        nouveau_statut = request.POST.get('statut')
        valeurs_valides = [s[0] for s in statuts]
        if nouveau_statut in valeurs_valides:
            reservation.statut = nouveau_statut
            reservation.save()
            return redirect('transport:liste_billets')
        else:
            contexte['erreur'] = "Action non autorisee pour votre poste."

    return render(request, 'transport/modifier_billet.html', contexte)

@staff_member_required
def mon_profil(request):
    """Page en lecture seule affichant les infos de l'employe connecte."""
    employe = getattr(request.user, 'employe', None)
    return render(request, 'transport/mon_profil.html', {'employe': employe})


@staff_member_required
def rapport_agence(request):
    """
    Rapport imprimable pour une agence : employes, chauffeurs, effectifs par poste.
    Accessible au RH, PDG, et superuser uniquement.
    Sections et employe cible selectionnables via GET.
    """
    employe_connecte = getattr(request.user, 'employe', None)
    poste = employe_connecte.poste if employe_connecte else None
    autorise = request.user.is_superuser or poste in ('pdg', 'rh')

    if not autorise:
        return redirect('admin:index')

    agences = Agence.objects.filter(actif=True).order_by('ville', 'nom')
    agence_choisie = None
    employes_agence = []
    chauffeurs_agence = []
    effectifs_poste = []
    employe_cible = None

    agence_id = request.GET.get('agence')
    if agence_id:
        agence_choisie = Agence.objects.filter(id=agence_id).first()
        if agence_choisie:
            employes_agence = Employe.objects.filter(agence=agence_choisie, actif=True).order_by('poste', 'nom')
            chauffeurs_agence = Chauffeur.objects.filter(agence=agence_choisie, actif=True).order_by('nom')

            employe_id = request.GET.get('employe')
            if employe_id:
                employe_cible = employes_agence.filter(id=employe_id).first()
                if employe_cible:
                    employes_agence = employes_agence.filter(id=employe_id)

            from django.db.models import Count
            effectifs_poste = list(
                Employe.objects.filter(agence=agence_choisie, actif=True)
                .values('poste')
                .annotate(total=Count('id'))
                .order_by('poste')
            )
            for e in effectifs_poste:
                e['poste_libelle'] = dict(Employe.POSTE_CHOICES).get(e['poste'], e['poste'])

    sections = {
        'effectifs': request.GET.get('sec_effectifs', '1') == '1',
        'employes': request.GET.get('sec_employes', '1') == '1',
        'chauffeurs': request.GET.get('sec_chauffeurs', '1') == '1',
    }

    return render(request, 'transport/rapport_agence.html', {
        'agences': agences,
        'agence_choisie': agence_choisie,
        'employes_agence': employes_agence,
        'chauffeurs_agence': chauffeurs_agence,
        'effectifs_poste': effectifs_poste,
        'employe_cible': employe_cible,
        'tous_employes_agence': Employe.objects.filter(agence=agence_choisie, actif=True).order_by('nom') if agence_choisie else [],
        'sections': sections,
    })


@staff_member_required
def rapport_finances_agence(request):
    """Rapport financier imprimable par agence, pour le Comptable et le PDG."""
    from django.db.models import Sum, Count
    from .models import Colis, TransfertArgent

    employe = getattr(request.user, 'employe', None)
    poste = employe.poste if employe else None
    autorise = request.user.is_superuser or poste in ('pdg', 'comptable')

    if not autorise:
        return redirect('admin:index')

    agences = Agence.objects.filter(actif=True).order_by('ville', 'nom')
    agence_choisie = None
    donnees = None

    agence_id = request.GET.get('agence')
    if agence_id:
        agence_choisie = Agence.objects.filter(id=agence_id).first()
        if agence_choisie:
            aujourd_hui = timezone.now().date()
            debut_mois = aujourd_hui.replace(day=1)

            def val(x):
                return x or 0

            billets = Reservation.objects.filter(
                statut='payee', agence=agence_choisie, date_reservation__date__gte=debut_mois
            ).aggregate(total=Sum('montant_total'), nb=Count('id'))

            colis = Colis.objects.filter(
                agence_depart=agence_choisie, date_enregistrement__date__gte=debut_mois
            ).aggregate(total=Sum('prix'), nb=Count('id'))

            transferts = TransfertArgent.objects.filter(
                agence_depart=agence_choisie, date_envoi__date__gte=debut_mois
            ).aggregate(total=Sum('frais'), nb=Count('id'))

            donnees = {
                'billets_total': val(billets['total']),
                'billets_nb': val(billets['nb']),
                'colis_total': val(colis['total']),
                'colis_nb': val(colis['nb']),
                'transferts_total': val(transferts['total']),
                'transferts_nb': val(transferts['nb']),
                'total_general': val(billets['total']) + val(colis['total']) + val(transferts['total']),
            }

    return render(request, 'transport/rapport_finances_agence.html', {
        'agences': agences,
        'agence_choisie': agence_choisie,
        'donnees': donnees,
    })


@staff_member_required
def rapport_maintenance_agence(request):
    """Rapport imprimable d'entretien et carburant par agence, pour Maintenance et le PDG."""
    from django.db.models import Sum
    from .models import Entretien, PleinCarburant, Bus

    employe = getattr(request.user, 'employe', None)
    poste = employe.poste if employe else None
    autorise = request.user.is_superuser or poste in ('pdg', 'resp_maintenance')

    if not autorise:
        return redirect('admin:index')

    agences = Agence.objects.filter(actif=True).order_by('ville', 'nom')
    agence_choisie = None
    bus_agence = []
    entretiens_agence = []
    total_carburant = 0
    bus_cible = None

    agence_id = request.GET.get('agence')
    if agence_id:
        agence_choisie = Agence.objects.filter(id=agence_id).first()
        if agence_choisie:
            bus_agence = Bus.objects.filter(agence=agence_choisie).order_by('immatriculation')
            entretiens_agence = Entretien.objects.filter(bus__agence=agence_choisie).select_related('bus').order_by('-date_entretien')
            total_carburant_qs = PleinCarburant.objects.filter(bus__agence=agence_choisie)

            bus_id = request.GET.get('bus')
            if bus_id:
                bus_cible = bus_agence.filter(id=bus_id).first()
                if bus_cible:
                    bus_agence = bus_agence.filter(id=bus_id)
                    entretiens_agence = entretiens_agence.filter(bus_id=bus_id)
                    total_carburant_qs = total_carburant_qs.filter(bus_id=bus_id)

            total_carburant = total_carburant_qs.aggregate(total=Sum('montant'))['total'] or 0
            entretiens_agence = entretiens_agence[:30]

    sections = {
        'bus': request.GET.get('sec_bus', '1') == '1',
        'carburant': request.GET.get('sec_carburant', '1') == '1',
        'entretiens': request.GET.get('sec_entretiens', '1') == '1',
    }

    return render(request, 'transport/rapport_maintenance_agence.html', {
        'agences': agences,
        'agence_choisie': agence_choisie,
        'bus_agence': bus_agence,
        'entretiens_agence': entretiens_agence,
        'total_carburant': total_carburant,
        'bus_cible': bus_cible,
        'tous_bus_agence': Bus.objects.filter(agence=agence_choisie).order_by('immatriculation') if agence_choisie else [],
        'sections': sections,
    })


@staff_member_required
def rapport_mon_agence(request):
    """
    Rapport complet (RH + finances + maintenance) pour le responsable,
    verrouille automatiquement sur sa propre agence.
    """
    from django.db.models import Sum, Count
    from .models import Colis, TransfertArgent, Entretien, PleinCarburant, Bus

    employe = getattr(request.user, 'employe', None)
    poste = employe.poste if employe else None
    autorise = request.user.is_superuser or poste in ('pdg', 'responsable')

    if not autorise:
        return redirect('admin:index')

    agence = employe.agence if employe else None
    if request.user.is_superuser and not agence:
        # Un superuser sans fiche employe peut choisir via ?agence=
        agence_id = request.GET.get('agence')
        if agence_id:
            agence = Agence.objects.filter(id=agence_id).first()

    if not agence:
        return render(request, 'transport/rapport_mon_agence.html', {
            'agence': None,
            'agences_dispo': Agence.objects.filter(actif=True).order_by('nom') if request.user.is_superuser else None,
        })

    aujourd_hui = timezone.now().date()
    debut_mois = aujourd_hui.replace(day=1)

    def val(x):
        return x or 0

    employes_agence = Employe.objects.filter(agence=agence, actif=True).order_by('poste', 'nom')
    chauffeurs_agence = Chauffeur.objects.filter(agence=agence, actif=True).order_by('nom')
    bus_agence = Bus.objects.filter(agence=agence).order_by('immatriculation')

    effectifs_poste = list(
        Employe.objects.filter(agence=agence, actif=True)
        .values('poste')
        .annotate(total=Count('id'))
        .order_by('poste')
    )
    for e in effectifs_poste:
        e['poste_libelle'] = dict(Employe.POSTE_CHOICES).get(e['poste'], e['poste'])

    billets = Reservation.objects.filter(
        statut='payee', agence=agence, date_reservation__date__gte=debut_mois
    ).aggregate(total=Sum('montant_total'), nb=Count('id'))
    colis = Colis.objects.filter(
        agence_depart=agence, date_enregistrement__date__gte=debut_mois
    ).aggregate(total=Sum('prix'), nb=Count('id'))
    transferts = TransfertArgent.objects.filter(
        agence_depart=agence, date_envoi__date__gte=debut_mois
    ).aggregate(total=Sum('frais'), nb=Count('id'))

    finances = {
        'billets_total': val(billets['total']),
        'billets_nb': val(billets['nb']),
        'colis_total': val(colis['total']),
        'colis_nb': val(colis['nb']),
        'transferts_total': val(transferts['total']),
        'transferts_nb': val(transferts['nb']),
        'total_general': val(billets['total']) + val(colis['total']) + val(transferts['total']),
    }

    total_carburant = PleinCarburant.objects.filter(bus__agence=agence).aggregate(total=Sum('montant'))['total'] or 0
    entretiens_agence = Entretien.objects.filter(bus__agence=agence).select_related('bus').order_by('-date_entretien')[:30]

    return render(request, 'transport/rapport_mon_agence.html', {
        'agence': agence,
        'employes_agence': employes_agence,
        'chauffeurs_agence': chauffeurs_agence,
        'bus_agence': bus_agence,
        'effectifs_poste': effectifs_poste,
        'finances': finances,
        'total_carburant': total_carburant,
        'entretiens_agence': entretiens_agence,
    })

@staff_member_required
def carte_bus_temps_reel(request):
    """
    Carte en temps reel des bus en cours de voyage.
    PDG : voit tous les bus. Responsable/Securite : voient ceux de leur agence.
    """
    from .models import PositionBus

    employe = getattr(request.user, 'employe', None)
    poste = employe.poste if employe else None
    autorise = request.user.is_superuser or poste in ('pdg', 'responsable', 'securite')

    if not autorise:
        return redirect('admin:index')

    voyages_en_cours = Voyage.objects.filter(statut='en_cours').select_related('trajet', 'bus', 'chauffeur')

    if not (request.user.is_superuser or poste == 'pdg'):
        agence = employe.agence if employe else None
        if agence:
            voyages_en_cours = voyages_en_cours.filter(bus__agence=agence)
        else:
            voyages_en_cours = voyages_en_cours.none()

    voyages_data = []
    voyages_json = []
    for v in voyages_en_cours:
        derniere = PositionBus.objects.filter(voyage=v).order_by('-horodatage').first()
        voyages_data.append({
            'voyage': v,
            'derniere_position': derniere,
        })
        voyages_json.append({
            'voyageId': v.id,
            'trajet': f"{v.trajet.ville_depart} -> {v.trajet.ville_arrivee}",
            'bus': v.bus.immatriculation,
            'lat': derniere.latitude if derniere else None,
            'lng': derniere.longitude if derniere else None,
            'horodatage': derniere.horodatage.isoformat() if derniere else None,
        })

    return render(request, 'transport/carte_bus_temps_reel.html', {
        'voyages_data': voyages_data,
        'voyages_json': voyages_json,
    })


@staff_member_required
def manifeste_bord(request):
    """
    Manifeste de bord imprimable : liste des passagers d'un voyage,
    avec leur statut d'embarquement (scanne ou non).
    Accessible au PDG, Responsable, et Securite.
    """
    employe = getattr(request.user, 'employe', None)
    poste = employe.poste if employe else None
    autorise = request.user.is_superuser or poste in ('pdg', 'responsable', 'securite')

    if not autorise:
        return redirect('admin:index')

    voyage_choisi = None
    reservations = []

    voyages_disponibles = Voyage.objects.filter(
        statut__in=['programme', 'en_cours', 'termine']
    ).select_related('trajet', 'bus').order_by('-date_depart', '-heure_depart')

    if not (request.user.is_superuser or poste == 'pdg'):
        agence = employe.agence if employe else None
        if agence:
            voyages_disponibles = voyages_disponibles.filter(bus__agence=agence)
        else:
            voyages_disponibles = voyages_disponibles.none()

    voyages_disponibles = voyages_disponibles[:50]

    voyage_id = request.GET.get('voyage')
    if voyage_id:
        voyage_choisi = Voyage.objects.filter(id=voyage_id).select_related('trajet', 'bus', 'chauffeur').first()
        if voyage_choisi:
            reservations = Reservation.objects.filter(
                voyage=voyage_choisi, statut='payee'
            ).select_related('client', 'siege').order_by('embarque', 'voyageur_nom')

    nombre_embarques = reservations.filter(embarque=True).count() if voyage_choisi else 0

    return render(request, 'transport/manifeste_bord.html', {
        'voyages_disponibles': voyages_disponibles,
        'voyage_choisi': voyage_choisi,
        'reservations': reservations,
        'nombre_embarques': nombre_embarques,
    })


@staff_member_required
def tableau_bord_pdg(request):
    """
    Vue synthetique pour le PDG : indicateurs cles de toute la compagnie.
    """
    from django.db.models import Sum, Count, Q as DQ
    from .models import AlerteVoyage, Colis, TransfertArgent

    employe = getattr(request.user, 'employe', None)
    poste = employe.poste if employe else None
    autorise = request.user.is_superuser or poste == 'pdg'

    if not autorise:
        return redirect('admin:index')

    aujourd_hui = timezone.now().date()

    def val(x):
        return x or 0

    # Recette du jour, toutes agences
    recette_billets = Reservation.objects.filter(
        statut='payee', date_reservation__date=aujourd_hui
    ).aggregate(total=Sum('montant_total'))['total']
    recette_colis = Colis.objects.filter(
        date_enregistrement__date=aujourd_hui
    ).aggregate(total=Sum('prix'))['total']
    recette_transferts = TransfertArgent.objects.filter(
        date_envoi__date=aujourd_hui
    ).aggregate(total=Sum('frais'))['total']

    recette_totale = val(recette_billets) + val(recette_colis) + val(recette_transferts)

    # Bus en circulation
    bus_en_circulation = Voyage.objects.filter(statut='en_cours').count()

    # Alertes non resolues
    alertes_actives = AlerteVoyage.objects.filter(resolue=False).count()

    # Taux de remplissage moyen du jour (voyages du jour uniquement)
    voyages_jour = Voyage.objects.filter(date_depart=aujourd_hui).select_related('bus')
    taux_total = 0
    nb_voyages_calcules = 0
    for v in voyages_jour:
        if v.bus and v.bus.capacite:
            places_vendues = Reservation.objects.filter(voyage=v, statut='payee').count()
            taux = (places_vendues / v.bus.capacite) * 100
            taux_total += taux
            nb_voyages_calcules += 1
    taux_remplissage_moyen = round(taux_total / nb_voyages_calcules, 1) if nb_voyages_calcules else 0

    # Top 3 agences par recette du jour (billets)
    top_agences = (
        Reservation.objects.filter(statut='payee', date_reservation__date=aujourd_hui, agence__isnull=False)
        .values('agence__nom')
        .annotate(total=Sum('montant_total'))
        .order_by('-total')[:3]
    )

    # Repartition Nord/Sud (billets du jour, via agence de vente)
    repartition = (
        Reservation.objects.filter(statut='payee', date_reservation__date=aujourd_hui, agence__zone__in=['nord', 'sud'])
        .values('agence__zone')
        .annotate(total=Sum('montant_total'), nb=Count('id'))
    )
    repartition_dict = {r['agence__zone']: {'total': r['total'], 'nb': r['nb']} for r in repartition}

    # Colis et transferts du jour
    colis_jour = Colis.objects.filter(date_enregistrement__date=aujourd_hui).count()
    transferts_jour = TransfertArgent.objects.filter(date_envoi__date=aujourd_hui).count()

    return render(request, 'transport/tableau_bord_pdg.html', {
        'recette_totale': recette_totale,
        'recette_billets': val(recette_billets),
        'recette_colis': val(recette_colis),
        'recette_transferts': val(recette_transferts),
        'bus_en_circulation': bus_en_circulation,
        'alertes_actives': alertes_actives,
        'taux_remplissage_moyen': taux_remplissage_moyen,
        'top_agences': top_agences,
        'repartition_nord': repartition_dict.get('nord', {'total': 0, 'nb': 0}),
        'repartition_sud': repartition_dict.get('sud', {'total': 0, 'nb': 0}),
        'colis_jour': colis_jour,
        'transferts_jour': transferts_jour,
    })