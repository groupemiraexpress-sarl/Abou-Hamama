from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from .models import Voyage, Client, Reservation, Agence, Chauffeur, Employe
from django.urls import reverse


@staff_member_required
def vendre_billet(request):
    """
    Interface guichetier : vendre un ou plusieurs billets,
    avec une identite distincte pour chaque passager.
    """
    employe = getattr(request.user, 'employe', None)

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