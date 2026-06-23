from django.shortcuts import render
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Colis, TransfertArgent, Voyage, Trajet, Client, Reservation, Agence, Chauffeur, Compagnie, Employe, Bus


def accueil(request):
    """Page d'accueil avec les 3 services."""
    return render(request, 'transport/accueil.html')


def suivi(request):
    """
    Recherche un colis ou un transfert d'argent par son code.
    Si aucun code n'est fourni, affiche le formulaire de recherche.
    """
    code = request.GET.get('code', '').strip().upper()

    if not code:
        return render(request, 'transport/recherche_suivi.html')

    contexte = {'code': code}
    colis = Colis.objects.filter(code_suivi=code).first()
    transfert = TransfertArgent.objects.filter(code_transfert=code).first()

    if colis:
        contexte['type'] = 'colis'
        contexte['colis'] = colis
        # Étapes de progression du colis
        etapes = ['enregistre', 'en_transit', 'arrive', 'livre']
        if colis.statut in etapes:
            contexte['etape_actuelle'] = etapes.index(colis.statut) + 1
        else:
            # statut "retourne" ou autre : pas dans le parcours normal
            contexte['etape_actuelle'] = 0
    elif transfert:
        contexte['type'] = 'transfert'
        contexte['transfert'] = transfert
    else:
        contexte['type'] = 'introuvable'

    return render(request, 'transport/suivi.html', contexte)


def recherche_voyage(request):
    """
    Recherche les voyages disponibles selon ville de départ,
    ville d'arrivée et date.
    """
    villes_depart = Trajet.objects.values_list('ville_depart', flat=True).distinct().order_by('ville_depart')
    villes_arrivee = Trajet.objects.values_list('ville_arrivee', flat=True).distinct().order_by('ville_arrivee')

    contexte = {
        'villes_depart': villes_depart,
        'villes_arrivee': villes_arrivee,
    }

    depart = request.GET.get('depart', '').strip()
    arrivee = request.GET.get('arrivee', '').strip()
    date = request.GET.get('date', '').strip()

    if depart or arrivee or date:
        voyages = Voyage.objects.filter(statut='programme')

        if depart:
            voyages = voyages.filter(trajet__ville_depart=depart)
        if arrivee:
            voyages = voyages.filter(trajet__ville_arrivee=arrivee)
        if date:
            voyages = voyages.filter(date_depart=date)

        voyages = voyages.filter(date_depart__gte=timezone.now().date(), places_disponibles__gt=0)
        voyages = voyages.order_by('date_depart', 'heure_depart')

        contexte['voyages'] = voyages
        contexte['recherche_faite'] = True
        contexte['depart'] = depart
        contexte['arrivee'] = arrivee
        contexte['date'] = date

    return render(request, 'transport/recherche_voyage.html', contexte)

# ============================================================
# ESPACE EMPLOYÉ — connexion, déconnexion, tableau de bord
# ============================================================

def connexion_employe(request):
    """Page de connexion pour les employés."""
    erreur = None

    if request.method == 'POST':
        identifiant = request.POST.get('identifiant', '').strip()
        mot_de_passe = request.POST.get('mot_de_passe', '')

        utilisateur = authenticate(request, username=identifiant, password=mot_de_passe)

        if utilisateur is not None:
            login(request, utilisateur)
            return redirect('transport:tableau_bord')
        else:
            erreur = "Identifiant ou mot de passe incorrect."

    return render(request, 'transport/connexion.html', {'erreur': erreur})


def deconnexion_employe(request):
    """Déconnecte l'employé et renvoie à la page de connexion."""
    logout(request)
    return redirect('transport:connexion')


@login_required(login_url='transport:connexion')
def tableau_bord(request):
    """
    Tableau de bord de l'employé connecté.
    Affiche les outils selon son poste.
    """
    # On récupère la fiche employé liée au compte connecté
    employe = getattr(request.user, 'employe', None)

    contexte = {
        'employe': employe,
        'est_superuser': request.user.is_superuser,
    }

    if employe:
        contexte['poste'] = employe.poste
        contexte['poste_libelle'] = employe.get_poste_display()

    return render(request, 'transport/tableau_bord.html', contexte)

@login_required(login_url='transport:connexion')
def vendre_billet(request):
    """
    Interface guichetier : vendre un billet.
    Affiche les voyages disponibles et crée la réservation.
    """
    employe = getattr(request.user, 'employe', None)

    # Voyages programmés, à venir, avec des places
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

        # Validation simple
        if not voyage_id or not client_nom or not client_telephone:
            contexte['erreur'] = "Veuillez remplir tous les champs obligatoires."
            return render(request, 'transport/vendre_billet.html', contexte)

        try:
            nombre_places = int(nombre_places)
        except ValueError:
            nombre_places = 1

        voyage = Voyage.objects.filter(id=voyage_id).first()
        if not voyage:
            contexte['erreur'] = "Voyage introuvable."
            return render(request, 'transport/vendre_billet.html', contexte)

        if nombre_places > voyage.places_disponibles:
            contexte['erreur'] = f"Plus que {voyage.places_disponibles} place(s) disponible(s)."
            return render(request, 'transport/vendre_billet.html', contexte)

        # Réutiliser le client existant (par téléphone) ou le créer
        client, cree = Client.objects.get_or_create(
            telephone=client_telephone,
            defaults={'nom': client_nom},
        )

        # Créer la réservation (le modèle gère le numéro, le montant, les places)
        try:
            reservation = Reservation.objects.create(
                client=client,
                voyage=voyage,
                agence=employe.agence if employe else None,
                nombre_places=nombre_places,
                statut='payee',
                mode_paiement=mode_paiement,
                cree_par=employe,
            )
        
        except ValueError as e:
            contexte['erreur'] = str(e)
            return render(request, 'transport/vendre_billet.html', contexte)

        return redirect('transport:billet_confirme', reservation_id=reservation.id)

    return render(request, 'transport/vendre_billet.html', contexte)


@login_required(login_url='transport:connexion')
def billet_confirme(request, reservation_id):
    """Affiche le reçu après la vente d'un billet."""
    reservation = Reservation.objects.filter(id=reservation_id).first()
    return render(request, 'transport/billet_confirme.html', {'reservation': reservation})

@login_required(login_url='transport:connexion')
def gerer_colis(request):
    """
    Interface agent colis : enregistrer un nouveau colis.
    """
    employe = getattr(request.user, 'employe', None)

    # Agences disponibles pour le départ/arrivée
    agences = Agence.objects.filter(actif=True).order_by('ville', 'nom')

    contexte = {'agences': agences, 'employe': employe}

    if request.method == 'POST':
        expediteur_nom = request.POST.get('expediteur_nom', '').strip()
        expediteur_telephone = request.POST.get('expediteur_telephone', '').strip()
        destinataire_nom = request.POST.get('destinataire_nom', '').strip()
        destinataire_telephone = request.POST.get('destinataire_telephone', '').strip()
        agence_depart_id = request.POST.get('agence_depart')
        agence_arrivee_id = request.POST.get('agence_arrivee')
        description = request.POST.get('description', '').strip()
        poids_kg = request.POST.get('poids_kg', '').strip()
        prix = request.POST.get('prix', '').strip()

        # Validation simple
        if not all([expediteur_nom, expediteur_telephone, destinataire_nom,
                    destinataire_telephone, agence_depart_id, agence_arrivee_id,
                    description, poids_kg, prix]):
            contexte['erreur'] = "Veuillez remplir tous les champs."
            return render(request, 'transport/gerer_colis.html', contexte)

        try:
            poids_kg = float(poids_kg)
            prix = int(prix)
        except ValueError:
            contexte['erreur'] = "Poids et prix doivent être des nombres."
            return render(request, 'transport/gerer_colis.html', contexte)

        agence_depart = Agence.objects.filter(id=agence_depart_id).first()
        agence_arrivee = Agence.objects.filter(id=agence_arrivee_id).first()

        # La compagnie vient de l'employé connecté (ou de l'agence de départ)
        compagnie = None
        if employe and employe.compagnie:
            compagnie = employe.compagnie
        elif agence_depart:
            compagnie = agence_depart.compagnie

        colis = Colis.objects.create(
            compagnie=compagnie,
            expediteur_nom=expediteur_nom,
            expediteur_telephone=expediteur_telephone,
            destinataire_nom=destinataire_nom,
            destinataire_telephone=destinataire_telephone,
            agence_depart=agence_depart,
            agence_arrivee=agence_arrivee,
            description=description,
            poids_kg=poids_kg,
            prix=prix,
            statut='enregistre',
            cree_par=employe,
        )

        return redirect('transport:colis_confirme', colis_id=colis.id)

    return render(request, 'transport/gerer_colis.html', contexte)


@login_required(login_url='transport:connexion')
def colis_confirme(request, colis_id):
    """Affiche le reçu après l'enregistrement d'un colis."""
    colis = Colis.objects.filter(id=colis_id).first()
    return render(request, 'transport/colis_confirme.html', {'colis': colis})

@login_required(login_url='transport:connexion')
def gerer_transfert(request):
    """
    Interface agent transfert : envoyer de l'argent entre agences.
    """
    employe = getattr(request.user, 'employe', None)
    agences = Agence.objects.filter(actif=True).order_by('ville', 'nom')

    contexte = {'agences': agences, 'employe': employe}

    if request.method == 'POST':
        expediteur_nom = request.POST.get('expediteur_nom', '').strip()
        expediteur_telephone = request.POST.get('expediteur_telephone', '').strip()
        beneficiaire_nom = request.POST.get('beneficiaire_nom', '').strip()
        beneficiaire_telephone = request.POST.get('beneficiaire_telephone', '').strip()
        agence_depart_id = request.POST.get('agence_depart')
        agence_retrait_id = request.POST.get('agence_retrait')
        montant = request.POST.get('montant', '').strip()
        frais = request.POST.get('frais', '0').strip()

        if not all([expediteur_nom, expediteur_telephone, beneficiaire_nom,
                    beneficiaire_telephone, agence_depart_id, agence_retrait_id, montant]):
            contexte['erreur'] = "Veuillez remplir tous les champs obligatoires."
            return render(request, 'transport/gerer_transfert.html', contexte)

        try:
            montant = int(montant)
            frais = int(frais) if frais else 0
        except ValueError:
            contexte['erreur'] = "Montant et frais doivent être des nombres."
            return render(request, 'transport/gerer_transfert.html', contexte)

        agence_depart = Agence.objects.filter(id=agence_depart_id).first()
        agence_retrait = Agence.objects.filter(id=agence_retrait_id).first()

        compagnie = None
        if employe and employe.compagnie:
            compagnie = employe.compagnie
        elif agence_depart:
            compagnie = agence_depart.compagnie

        transfert = TransfertArgent.objects.create(
            compagnie=compagnie,
            expediteur_nom=expediteur_nom,
            expediteur_telephone=expediteur_telephone,
            beneficiaire_nom=beneficiaire_nom,
            beneficiaire_telephone=beneficiaire_telephone,
            agence_depart=agence_depart,
            agence_retrait=agence_retrait,
            montant=montant,
            frais=frais,
            statut='en_attente',
            cree_par=employe,
        )

        return redirect('transport:transfert_confirme', transfert_id=transfert.id)

    return render(request, 'transport/gerer_transfert.html', contexte)


@login_required(login_url='transport:connexion')
def transfert_confirme(request, transfert_id):
    """Affiche le reçu après l'envoi d'un transfert."""
    transfert = TransfertArgent.objects.filter(id=transfert_id).first()
    return render(request, 'transport/transfert_confirme.html', {'transfert': transfert})

@login_required(login_url='transport:connexion')
def caisse_finances(request):
    """
    Interface comptable : recettes du jour et du mois.
    Calcule les totaux billets + colis + transferts.
    """
    from django.db.models import Sum, Count

    employe = getattr(request.user, 'employe', None)
    aujourd_hui = timezone.now().date()
    debut_mois = aujourd_hui.replace(day=1)

    # --- RECETTES DU JOUR ---
    billets_jour = Reservation.objects.filter(
        statut='payee', date_reservation__date=aujourd_hui
    ).aggregate(total=Sum('montant_total'), nb=Count('id'))

    colis_jour = Colis.objects.filter(
        date_enregistrement__date=aujourd_hui
    ).aggregate(total=Sum('prix'), nb=Count('id'))

    transferts_jour = TransfertArgent.objects.filter(
        date_envoi__date=aujourd_hui
    ).aggregate(total=Sum('frais'), nb=Count('id'))

    # --- RECETTES DU MOIS ---
    billets_mois = Reservation.objects.filter(
        statut='payee', date_reservation__date__gte=debut_mois
    ).aggregate(total=Sum('montant_total'), nb=Count('id'))

    colis_mois = Colis.objects.filter(
        date_enregistrement__date__gte=debut_mois
    ).aggregate(total=Sum('prix'), nb=Count('id'))

    transferts_mois = TransfertArgent.objects.filter(
        date_envoi__date__gte=debut_mois
    ).aggregate(total=Sum('frais'), nb=Count('id'))

    # Petite fonction pour éviter les None (si aucune donnée)
    def val(x):
        return x or 0

    contexte = {
        'employe': employe,
        'date_jour': aujourd_hui,

        # Jour
        'billets_jour_total': val(billets_jour['total']),
        'billets_jour_nb': val(billets_jour['nb']),
        'colis_jour_total': val(colis_jour['total']),
        'colis_jour_nb': val(colis_jour['nb']),
        'transferts_jour_total': val(transferts_jour['total']),
        'transferts_jour_nb': val(transferts_jour['nb']),
        'total_jour': val(billets_jour['total']) + val(colis_jour['total']) + val(transferts_jour['total']),

        # Mois
        'billets_mois_total': val(billets_mois['total']),
        'colis_mois_total': val(colis_mois['total']),
        'transferts_mois_total': val(transferts_mois['total']),
        'total_mois': val(billets_mois['total']) + val(colis_mois['total']) + val(transferts_mois['total']),
    }

    return render(request, 'transport/caisse_finances.html', contexte)

@login_required(login_url='transport:connexion')
def recruter_chauffeur(request):
    """
    Interface RH : enregistrer un nouveau chauffeur.
    """
    employe = getattr(request.user, 'employe', None)
    contexte = {'employe': employe}

    if request.method == 'POST':
        nom = request.POST.get('nom', '').strip()
        prenom = request.POST.get('prenom', '').strip()
        telephone = request.POST.get('telephone', '').strip()
        numero_permis = request.POST.get('numero_permis', '').strip()
        annees_experience = request.POST.get('annees_experience', '0').strip()

        if not all([nom, prenom, telephone, numero_permis]):
            contexte['erreur'] = "Veuillez remplir tous les champs obligatoires."
            return render(request, 'transport/recruter_chauffeur.html', contexte)

        try:
            annees_experience = int(annees_experience) if annees_experience else 0
        except ValueError:
            annees_experience = 0

        # Vérifier que le numéro de permis n'existe pas déjà
        if Chauffeur.objects.filter(numero_permis=numero_permis).exists():
            contexte['erreur'] = "Un chauffeur avec ce numéro de permis existe déjà."
            return render(request, 'transport/recruter_chauffeur.html', contexte)

        compagnie = employe.compagnie if employe and employe.compagnie else None
        if not compagnie:
            compagnie = Compagnie.objects.first()

        chauffeur = Chauffeur.objects.create(
            compagnie=compagnie,
            nom=nom,
            prenom=prenom,
            telephone=telephone,
            numero_permis=numero_permis,
            annees_experience=annees_experience,
            statut='disponible',
            actif=True,
        )

        return redirect('transport:chauffeur_confirme', chauffeur_id=chauffeur.id)

    return render(request, 'transport/recruter_chauffeur.html', contexte)


@login_required(login_url='transport:connexion')
def chauffeur_confirme(request, chauffeur_id):
    """Affiche la confirmation après l'enregistrement d'un chauffeur."""
    chauffeur = Chauffeur.objects.filter(id=chauffeur_id).first()
    return render(request, 'transport/chauffeur_confirme.html', {'chauffeur': chauffeur})

@login_required(login_url='transport:connexion')
def vue_compagnie(request):
    """
    Interface PDG : vue d'ensemble de toute la compagnie.
    Indicateurs globaux : recettes, activité, ressources.
    """
    from django.db.models import Sum, Count

    employe = getattr(request.user, 'employe', None)
    aujourd_hui = timezone.now().date()
    debut_mois = aujourd_hui.replace(day=1)

    def val(x):
        return x or 0

    # --- RECETTES DU MOIS (toute la compagnie) ---
    billets_mois = Reservation.objects.filter(
        statut='payee', date_reservation__date__gte=debut_mois
    ).aggregate(total=Sum('montant_total'))
    colis_mois = Colis.objects.filter(
        date_enregistrement__date__gte=debut_mois
    ).aggregate(total=Sum('prix'))
    transferts_mois = TransfertArgent.objects.filter(
        date_envoi__date__gte=debut_mois
    ).aggregate(total=Sum('frais'))

    recette_mois = val(billets_mois['total']) + val(colis_mois['total']) + val(transferts_mois['total'])

    # --- ACTIVITÉ (totaux globaux) ---
    nb_voyages = Voyage.objects.filter(statut='programme').count()
    nb_colis = Colis.objects.count()
    nb_transferts = TransfertArgent.objects.count()
    nb_reservations = Reservation.objects.filter(statut='payee').count()

    # --- RESSOURCES ---
    nb_agences = Agence.objects.filter(actif=True).count()
    nb_bus = Voyage.objects.values('bus').distinct().count()
    nb_chauffeurs = Chauffeur.objects.filter(actif=True).count()
    nb_employes = Employe.objects.filter(actif=True).count()

    contexte = {
        'employe': employe,
        'recette_mois': recette_mois,
        'billets_mois': val(billets_mois['total']),
        'colis_mois': val(colis_mois['total']),
        'transferts_mois': val(transferts_mois['total']),
        'nb_voyages': nb_voyages,
        'nb_colis': nb_colis,
        'nb_transferts': nb_transferts,
        'nb_reservations': nb_reservations,
        'nb_agences': nb_agences,
        'nb_chauffeurs': nb_chauffeurs,
        'nb_employes': nb_employes,
    }

    return render(request, 'transport/vue_compagnie.html', contexte)

@login_required(login_url='transport:connexion')
def vue_agence(request):
    """
    Interface responsable d'agence : vue d'ensemble de SON agence.
    Indicateurs filtrés sur l'agence du responsable connecté.
    """
    from django.db.models import Sum, Count

    employe = getattr(request.user, 'employe', None)
    agence = employe.agence if employe else None
    aujourd_hui = timezone.now().date()
    debut_mois = aujourd_hui.replace(day=1)

    def val(x):
        return x or 0

    contexte = {'employe': employe, 'agence': agence}

    # Si pas d'agence rattachée (ex. admin sans fiche), on prévient
    if not agence:
        contexte['pas_agence'] = True
        return render(request, 'transport/vue_agence.html', contexte)

    # --- RECETTES DU MOIS (uniquement cette agence) ---
    billets_mois = Reservation.objects.filter(
        statut='payee', date_reservation__date__gte=debut_mois, agence=agence
    ).aggregate(total=Sum('montant_total'))

    colis_mois = Colis.objects.filter(
        date_enregistrement__date__gte=debut_mois, agence_depart=agence
    ).aggregate(total=Sum('prix'))

    transferts_mois = TransfertArgent.objects.filter(
        date_envoi__date__gte=debut_mois, agence_depart=agence
    ).aggregate(total=Sum('frais'))

    recette_mois = val(billets_mois['total']) + val(colis_mois['total']) + val(transferts_mois['total'])

    nb_reservations = Reservation.objects.filter(statut='payee', agence=agence).count()
    nb_colis = Colis.objects.filter(agence_depart=agence).count()
    nb_transferts = TransfertArgent.objects.filter(agence_depart=agence).count()
    nb_employes = Employe.objects.filter(actif=True, agence=agence).count()

    contexte.update({
        'recette_mois': recette_mois,
        'billets_mois': val(billets_mois['total']),
        'colis_mois': val(colis_mois['total']),
        'transferts_mois': val(transferts_mois['total']),
        'nb_reservations': nb_reservations,
        'nb_colis': nb_colis,
        'nb_transferts': nb_transferts,
        'nb_employes': nb_employes,
    })

    return render(request, 'transport/vue_agence.html', contexte)


@login_required(login_url='transport:connexion')
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

    # Qui voit quoi ?
    if est_superuser or poste == 'pdg':
        # Tout
        pass
    elif poste == 'responsable':
        # Tous les billets de son agence
        if employe and employe.agence:
            billets = billets.filter(agence=employe.agence)
        else:
            billets = billets.none()
    else:
        # Les autres (guichetier...) : seulement CE QU'ILS ONT créé
        if employe:
            billets = billets.filter(cree_par=employe)
        else:
            billets = billets.none()

    billets = billets.order_by('-date_reservation')

    # Compteur personnel
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

@login_required(login_url='transport:connexion')
def liste_colis(request):
    """
    Liste des colis, vue par agence :
    - Départs : colis partis de mon agence
    - Arrivées : colis à destination de mon agence
    - En transit : colis en cours de route
    Permission : tous consultent, responsable/PDG/admin modifient.
    """
    employe = getattr(request.user, 'employe', None)
    est_superuser = request.user.is_superuser
    poste = employe.poste if employe else None

    peut_modifier = est_superuser or poste in ('pdg', 'responsable')

    base = Colis.objects.select_related('agence_depart', 'agence_arrivee', 'cree_par').order_by('-date_enregistrement')

    # PDG et admin voient tout ; les autres se limitent à leur agence
    agence = employe.agence if employe else None

    if est_superuser or poste == 'pdg':
        departs = base.filter(statut__in=['enregistre'])
        arrivees = base.filter(statut__in=['arrive', 'livre'])
        en_transit = base.filter(statut='en_transit')
    elif agence:
        departs = base.filter(agence_depart=agence, statut='enregistre')
        arrivees = base.filter(agence_arrivee=agence, statut__in=['arrive', 'livre'])
        en_transit = base.filter(agence_depart=agence, statut='en_transit')
    else:
        departs = base.none()
        arrivees = base.none()
        en_transit = base.none()

    contexte = {
        'departs': departs,
        'arrivees': arrivees,
        'en_transit': en_transit,
        'peut_modifier': peut_modifier,
        'employe': employe,
        'poste': poste,
    }

    return render(request, 'transport/liste_colis.html', contexte)

@login_required(login_url='transport:connexion')
def liste_transferts(request):
    """
    Liste des transferts, vue par agence :
    - Envoyés : déposés dans mon agence (départ)
    - À retirer : à payer dans mon agence (retrait)
    Permission : tous consultent, responsable/PDG/admin modifient.
    """
    employe = getattr(request.user, 'employe', None)
    est_superuser = request.user.is_superuser
    poste = employe.poste if employe else None

    peut_modifier = est_superuser or poste in ('pdg', 'responsable')

    base = TransfertArgent.objects.select_related('agence_depart', 'agence_retrait', 'cree_par').order_by('-date_envoi')

    agence = employe.agence if employe else None

    if est_superuser or poste == 'pdg':
        envoyes = base.all()
        a_retirer = base.filter(statut='en_attente')
    elif agence:
        envoyes = base.filter(agence_depart=agence)
        a_retirer = base.filter(agence_retrait=agence, statut='en_attente')
    else:
        envoyes = base.none()
        a_retirer = base.none()

    contexte = {
        'envoyes': envoyes,
        'a_retirer': a_retirer,
        'peut_modifier': peut_modifier,
        'employe': employe,
        'poste': poste,
    }

    return render(request, 'transport/liste_transferts.html', contexte)

@login_required(login_url='transport:connexion')
def gerer_entretien(request):
    """
    Interface responsable maintenance : enregistrer un entretien sur un bus.
    """
    employe = getattr(request.user, 'employe', None)
    bus_list = Bus.objects.all().order_by('immatriculation')

    # Types d'entretien (depuis le modèle)
    from .models import Entretien
    types = Entretien.TYPE_CHOICES

    contexte = {'bus_list': bus_list, 'types': types, 'employe': employe}

    if request.method == 'POST':
        bus_id = request.POST.get('bus')
        type_entretien = request.POST.get('type_entretien')
        date_entretien = request.POST.get('date_entretien')
        kilometrage = request.POST.get('kilometrage', '0').strip()
        cout = request.POST.get('cout', '0').strip()
        description = request.POST.get('description', '').strip()
        prochain_km = request.POST.get('prochain_km', '').strip()

        if not all([bus_id, type_entretien, date_entretien]):
            contexte['erreur'] = "Veuillez remplir le bus, le type et la date."
            return render(request, 'transport/gerer_entretien.html', contexte)

        try:
            kilometrage = int(kilometrage) if kilometrage else 0
            cout = int(cout) if cout else 0
            prochain_km = int(prochain_km) if prochain_km else None
        except ValueError:
            contexte['erreur'] = "Kilométrage, coût et prochaine échéance doivent être des nombres."
            return render(request, 'transport/gerer_entretien.html', contexte)

        bus = Bus.objects.filter(id=bus_id).first()
        if not bus:
            contexte['erreur'] = "Bus introuvable."
            return render(request, 'transport/gerer_entretien.html', contexte)

        Entretien.objects.create(
            bus=bus,
            type_entretien=type_entretien,
            date_entretien=date_entretien,
            kilometrage=kilometrage,
            cout=cout,
            description=description,
            prochain_km=prochain_km,
            cree_par=employe,
        )

        return redirect('transport:liste_entretiens')

    return render(request, 'transport/gerer_entretien.html', contexte)

@login_required(login_url='transport:connexion')
def liste_entretiens(request):
    """
    État de la flotte : pour chaque bus, sa dernière vidange,
    les jours écoulés depuis, et son dernier entretien.
    """
    employe = getattr(request.user, 'employe', None)
    est_superuser = request.user.is_superuser
    poste = employe.poste if employe else None

    peut_modifier = est_superuser or poste in ('pdg', 'responsable', 'resp_maintenance')

    from .models import Entretien
    aujourd_hui = timezone.now().date()

    bus_list = Bus.objects.all().order_by('immatriculation')

    flotte = []
    for bus in bus_list:
        # Dernière vidange de ce bus
        derniere_vidange = Entretien.objects.filter(
            bus=bus, type_entretien='vidange'
        ).order_by('-date_entretien').first()

        # Dernier entretien (tout type)
        dernier_entretien = Entretien.objects.filter(
            bus=bus
        ).order_by('-date_entretien').first()

        jours_depuis_vidange = None
        if derniere_vidange:
            jours_depuis_vidange = (aujourd_hui - derniere_vidange.date_entretien).days

        flotte.append({
            'bus': bus,
            'derniere_vidange': derniere_vidange,
            'jours_depuis_vidange': jours_depuis_vidange,
            'dernier_entretien': dernier_entretien,
        })

    # Les 10 derniers entretiens (toutes catégories)
    derniers = Entretien.objects.select_related('bus', 'cree_par').order_by('-date_entretien')[:10]

    contexte = {
        'flotte': flotte,
        'derniers': derniers,
        'peut_modifier': peut_modifier,
        'employe': employe,
    }

    return render(request, 'transport/liste_entretiens.html', contexte)

@login_required(login_url='transport:connexion')
def gerer_carburant(request):
    """
    Interface maintenance : enregistrer un plein de carburant,
    lié à un bus et à un voyage.
    """
    employe = getattr(request.user, 'employe', None)
    bus_list = Bus.objects.all().order_by('immatriculation')
    voyages = Voyage.objects.select_related('trajet', 'bus').order_by('-date_depart')[:50]

    from .models import PleinCarburant
    contexte = {'bus_list': bus_list, 'voyages': voyages, 'employe': employe}

    if request.method == 'POST':
        bus_id = request.POST.get('bus')
        voyage_id = request.POST.get('voyage')
        date_plein = request.POST.get('date_plein')
        litres = request.POST.get('litres', '0').strip()
        montant = request.POST.get('montant', '0').strip()
        kilometrage = request.POST.get('kilometrage', '').strip()

        if not all([bus_id, date_plein]):
            contexte['erreur'] = "Veuillez remplir au moins le bus et la date."
            return render(request, 'transport/gerer_carburant.html', contexte)

        try:
            litres = float(litres) if litres else 0
            montant = int(montant) if montant else 0
            kilometrage = int(kilometrage) if kilometrage else None
        except ValueError:
            contexte['erreur'] = "Litres, montant et kilométrage doivent être des nombres."
            return render(request, 'transport/gerer_carburant.html', contexte)

        bus = Bus.objects.filter(id=bus_id).first()
        if not bus:
            contexte['erreur'] = "Bus introuvable."
            return render(request, 'transport/gerer_carburant.html', contexte)

        voyage = Voyage.objects.filter(id=voyage_id).first() if voyage_id else None

        PleinCarburant.objects.create(
            bus=bus,
            voyage=voyage,
            date_plein=date_plein,
            litres=litres,
            montant=montant,
            kilometrage=kilometrage,
            cree_par=employe,
        )

        return redirect('transport:liste_carburant')

    return render(request, 'transport/gerer_carburant.html', contexte)

@login_required(login_url='transport:connexion')
def liste_carburant(request):
    """
    Récap des pleins de carburant : liste + total du mois.
    """
    from django.db.models import Sum
    from .models import PleinCarburant

    employe = getattr(request.user, 'employe', None)
    aujourd_hui = timezone.now().date()
    debut_mois = aujourd_hui.replace(day=1)

    pleins = PleinCarburant.objects.select_related('bus', 'voyage', 'voyage__trajet').order_by('-date_plein')[:50]

    total_mois = PleinCarburant.objects.filter(
        date_plein__gte=debut_mois
    ).aggregate(total=Sum('montant'))['total'] or 0

    contexte = {
        'pleins': pleins,
        'total_mois': total_mois,
        'employe': employe,
    }

    return render(request, 'transport/liste_carburant.html', contexte)

@login_required(login_url='transport:connexion')
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

    # Le remboursement est réservé au PDG / admin
    peut_rembourser = est_superuser or poste == 'pdg'

    # Statuts proposés selon le poste
    statuts = [('payee', 'Payée'), ('annulee', 'Annulée')]
    if peut_rembourser:
        statuts.append(('remboursee', 'Remboursée'))

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
            contexte['erreur'] = "Action non autorisée pour votre poste."

    return render(request, 'transport/modifier_billet.html', contexte)