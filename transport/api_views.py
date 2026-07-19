from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str

from .models import Voyage, Colis, TransfertArgent, Client, Reservation, Siege, Promotion, DemandeColis, Agence, DemandeTransfert
from .serializers import VoyageSerializer, ColisSerializer, TransfertArgentSerializer, ReservationSerializer, SiegeSerializer, PromotionSerializer, DemandeColisSerializer, AgenceSerializer, DemandeTransfertSerializer


@api_view(['GET'])
def api_voyages(request):
    aujourd_hui = timezone.now().date()
    voyages = Voyage.objects.select_related('trajet', 'bus').filter(
        date_depart__gte=aujourd_hui
    ).order_by('date_depart')
    return Response(VoyageSerializer(voyages, many=True).data)


@api_view(['GET'])
def api_suivi_colis(request, code_suivi):
    colis = Colis.objects.filter(code_suivi=code_suivi).first()
    if not colis:
        return Response({'erreur': 'Colis introuvable'}, status=404)
    return Response(ColisSerializer(colis).data)


@api_view(['GET'])
def api_suivi_transfert(request, code_transfert):
    transfert = TransfertArgent.objects.filter(code_transfert=code_transfert).first()
    if not transfert:
        return Response({'erreur': 'Transfert introuvable'}, status=404)
    return Response(TransfertArgentSerializer(transfert).data)


@api_view(['POST'])
def api_inscription(request):
    username = request.data.get('username', '').strip()
    email = request.data.get('email', '').strip().lower()
    telephone = request.data.get('telephone', '').strip()
    password = request.data.get('password', '')
    if not username or not password:
        return Response({'erreur': 'Nom et mot de passe obligatoires.'}, status=400)
    if not email:
        return Response({'erreur': 'Email obligatoire.'}, status=400)
    if not telephone:
        return Response({'erreur': 'Numero de telephone obligatoire.'}, status=400)
    if len(password) < 6:
        return Response({'erreur': 'Mot de passe trop court (min 6).'}, status=400)
    if User.objects.filter(username=username).exists():
        return Response({'erreur': 'Ce nom d\'utilisateur est deja pris.'}, status=400)
    if User.objects.filter(email__iexact=email).exists():
        return Response({'erreur': 'Un compte existe deja avec cet email.'}, status=400)
    if Client.objects.filter(telephone=telephone).exists():
        return Response({'erreur': 'Un compte existe deja avec ce numero de telephone.'}, status=400)

    user = User.objects.create_user(username=username, email=email, password=password)
    user.is_active = False
    user.save()

    # Creer la fiche client avec le vrai numero
    client = Client.objects.create(nom=username, telephone=telephone, email=email)
    client.user = user
    client.save()

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    lien = settings.SITE_URL + '/api/valider-email/' + uid + '/' + token + '/'
    send_mail(
        'Validez votre compte Express Abou Hamama',
        'Bienvenue ' + username + ' ! Cliquez sur ce lien pour valider votre compte : ' + lien,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )
    return Response({'message': 'Compte cree. Email de validation envoye.'}, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_mon_profil(request):
    user = request.user
    client = Client.objects.filter(user=user).first()
    return Response({
        'username': user.username,
        'email': user.email,
        'nom': client.nom if client else '',
        'prenom': client.prenom if client else '',
        'telephone': client.telephone if (client and not client.telephone.startswith('compte-')) else '',
        'date_inscription': user.date_joined,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_modifier_profil(request):
    user = request.user
    nom = request.data.get('nom', '').strip()
    prenom = request.data.get('prenom', '').strip()
    telephone = request.data.get('telephone', '').strip()
    email = request.data.get('email', '').strip()

    client = Client.objects.filter(user=user).first()
    if not client:
        client = Client.objects.create(nom=nom or user.username, telephone="compte-" + str(user.id), email=user.email)
        client.user = user

    if nom:
        client.nom = nom
    client.prenom = prenom
    if telephone:
        autre = Client.objects.filter(telephone=telephone).exclude(pk=client.pk).first()
        if autre:
            return Response({'erreur': 'Ce numero est deja utilise par un autre compte.'}, status=400)
        client.telephone = telephone
    if email:
        autre_user = User.objects.filter(email__iexact=email).exclude(pk=user.pk).first()
        if autre_user:
            return Response({'erreur': 'Cet email est deja utilise par un autre compte.'}, status=400)
        client.email = email
        user.email = email
        user.save()
    try:
        client.save()
    except Exception:
        return Response({'erreur': 'Impossible d\'enregistrer le profil.'}, status=400)
    return Response({'message': 'Profil mis a jour avec succes.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_changer_mot_de_passe(request):
    user = request.user
    ancien = request.data.get('ancien', '')
    nouveau = request.data.get('nouveau', '')
    if not ancien or not nouveau:
        return Response({'erreur': 'Ancien et nouveau mot de passe obligatoires.'}, status=400)
    if not user.check_password(ancien):
        return Response({'erreur': 'Ancien mot de passe incorrect.'}, status=400)
    if len(nouveau) < 6:
        return Response({'erreur': 'Nouveau mot de passe trop court (min 6).'}, status=400)
    user.set_password(nouveau)
    user.save()
    return Response({'message': 'Mot de passe change avec succes.'})


@api_view(['GET'])
def api_valider_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and default_token_generator.check_token(user, token):
        if user.is_active:
            return Response({'message': 'Compte deja valide.'})
        user.is_active = True
        user.save()
        return Response({'message': 'Compte valide avec succes !'})
    return Response({'erreur': 'Lien invalide ou expire.'}, status=400)


@api_view(['GET'])
def api_sieges_voyage(request, voyage_id):
    voyage = Voyage.objects.filter(id=voyage_id).first()
    if not voyage:
        return Response({'erreur': 'Voyage introuvable.'}, status=404)
    sieges = Siege.objects.filter(voyage=voyage).order_by('numero')
    return Response(SiegeSerializer(sieges, many=True).data)


def _get_ou_cree_client_du_compte(user):
    client = Client.objects.filter(user=user).first()
    if not client:
        client = Client.objects.create(
            nom=user.username,
            telephone="compte-" + str(user.id),
            email=user.email,
        )
        client.user = user
        client.save()
    return client


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_reserver(request):
    user = request.user
    voyage_id = request.data.get('voyage_id')
    nombre_places = request.data.get('nombre_places', 1)
    nom = request.data.get('nom', '').strip()
    telephone = request.data.get('telephone', '').strip()
    if not voyage_id or not telephone or not nom:
        return Response({'erreur': 'voyage_id, nom et telephone obligatoires.'}, status=400)
    try:
        nombre_places = int(nombre_places)
    except (ValueError, TypeError):
        return Response({'erreur': 'nombre_places doit etre un nombre.'}, status=400)
    if nombre_places < 1:
        return Response({'erreur': 'Au moins 1 place.'}, status=400)
    voyage = Voyage.objects.filter(id=voyage_id).first()
    if not voyage:
        return Response({'erreur': 'Voyage introuvable.'}, status=404)
    if nombre_places > voyage.places_disponibles:
        return Response({'erreur': 'Pas assez de places disponibles.'}, status=400)
    client = _get_ou_cree_client_du_compte(user)
    try:
        reservation = Reservation.objects.create(
            client=client,
            voyage=voyage,
            nombre_places=nombre_places,
            voyageur_nom=nom,
            voyageur_telephone=telephone,
            statut='en_attente',
        )
    except ValueError as e:
        return Response({'erreur': str(e)}, status=400)
    return Response({
        'message': 'Reservation creee avec succes.',
        'numero_reservation': reservation.numero_reservation,
        'montant_total': reservation.montant_total,
        'statut': reservation.statut,
        'places': reservation.nombre_places,
    }, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_reserver_siege(request):
    user = request.user
    voyage_id = request.data.get('voyage_id')
    numero_siege = request.data.get('numero_siege')
    nom = request.data.get('nom', '').strip()
    prenom = request.data.get('prenom', '').strip()
    telephone = request.data.get('telephone', '').strip()
    type_piece = request.data.get('type_piece', '').strip()
    numero_piece = request.data.get('numero_piece', '').strip()
    if not voyage_id or not numero_siege or not nom or not telephone:
        return Response({'erreur': 'voyage_id, numero_siege, nom et telephone obligatoires.'}, status=400)
    if not type_piece or not numero_piece:
        return Response({'erreur': 'Piece d\'identite obligatoire (type et numero).'}, status=400)
    try:
        numero_siege = int(numero_siege)
    except (ValueError, TypeError):
        return Response({'erreur': 'numero_siege doit etre un nombre.'}, status=400)
    voyage = Voyage.objects.filter(id=voyage_id).first()
    if not voyage:
        return Response({'erreur': 'Voyage introuvable.'}, status=404)
    siege = Siege.objects.filter(voyage=voyage, numero=numero_siege).first()
    if not siege:
        return Response({'erreur': 'Siege introuvable.'}, status=404)
    if siege.occupe:
        return Response({'erreur': 'Ce siege est deja occupe.'}, status=400)
    client = _get_ou_cree_client_du_compte(user)
    try:
        reservation = Reservation.objects.create(
            client=client,
            voyage=voyage,
            nombre_places=1,
            voyageur_nom=nom,
            voyageur_prenom=prenom,
            voyageur_telephone=telephone,
            voyageur_type_piece=type_piece,
            voyageur_numero_piece=numero_piece,
            statut='en_attente',
        )
    except ValueError as e:
        return Response({'erreur': str(e)}, status=400)
    siege.occupe = True
    siege.reservation = reservation
    siege.save()
    return Response({
        'message': 'Siege reserve avec succes.',
        'numero_reservation': reservation.numero_reservation,
        'numero_siege': siege.numero,
        'voyageur': nom,
        'montant_total': reservation.montant_total,
        'statut': reservation.statut,
    }, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_mes_billets(request):
    user = request.user
    client = Client.objects.filter(user=user).first()
    if not client:
        return Response([])
    reservations = Reservation.objects.filter(client=client).select_related(
        'voyage', 'voyage__trajet'
    ).order_by('-date_reservation')
    return Response(ReservationSerializer(reservations, many=True).data)


@api_view(['GET'])
def api_promotions(request):
    aujourd_hui = timezone.now().date()
    promotions = Promotion.objects.filter(
        actif=True,
        date_debut__lte=aujourd_hui,
        date_fin__gte=aujourd_hui,
    )
    return Response(PromotionSerializer(promotions, many=True, context={'request': request}).data)


@api_view(['GET'])
def api_agences(request):
    agences = Agence.objects.filter(actif=True).order_by('ville', 'nom')
    return Response(AgenceSerializer(agences, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_creer_demande_colis(request):
    user = request.user
    expediteur_nom = request.data.get('expediteur_nom', '').strip()
    expediteur_telephone = request.data.get('expediteur_telephone', '').strip()
    destinataire_nom = request.data.get('destinataire_nom', '').strip()
    destinataire_telephone = request.data.get('destinataire_telephone', '').strip()
    agence_depart_id = request.data.get('agence_depart')
    agence_arrivee_id = request.data.get('agence_arrivee')
    description = request.data.get('description', '').strip()
    poids_estime = request.data.get('poids_estime')
    valeur_declaree = request.data.get('valeur_declaree', 0)

    if not expediteur_nom or not expediteur_telephone or not destinataire_nom or not destinataire_telephone:
        return Response({'erreur': 'Informations expediteur et destinataire obligatoires.'}, status=400)
    if not agence_depart_id or not agence_arrivee_id:
        return Response({'erreur': 'Agences de depart et arrivee obligatoires.'}, status=400)
    if not description or not poids_estime:
        return Response({'erreur': 'Description et poids obligatoires.'}, status=400)

    agence_depart = Agence.objects.filter(id=agence_depart_id).first()
    agence_arrivee = Agence.objects.filter(id=agence_arrivee_id).first()
    if not agence_depart or not agence_arrivee:
        return Response({'erreur': 'Agence introuvable.'}, status=404)

    client = Client.objects.filter(user=user).first()

    demande = DemandeColis.objects.create(
        client=client,
        expediteur_nom=expediteur_nom,
        expediteur_telephone=expediteur_telephone,
        destinataire_nom=destinataire_nom,
        destinataire_telephone=destinataire_telephone,
        agence_depart=agence_depart,
        agence_arrivee=agence_arrivee,
        description=description,
        poids_estime=float(poids_estime),
        valeur_declaree=int(valeur_declaree or 0),
    )
    return Response({
        'message': 'Demande enregistree.',
        'numero_demande': demande.numero_demande,
    }, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_mes_demandes_colis(request):
    client = Client.objects.filter(user=request.user).first()
    if not client:
        return Response([])
    demandes = DemandeColis.objects.filter(client=client).order_by('-date_demande')
    return Response(DemandeColisSerializer(demandes, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_creer_demande_transfert(request):
    user = request.user
    expediteur_nom = request.data.get('expediteur_nom', '').strip()
    expediteur_telephone = request.data.get('expediteur_telephone', '').strip()
    beneficiaire_nom = request.data.get('beneficiaire_nom', '').strip()
    beneficiaire_telephone = request.data.get('beneficiaire_telephone', '').strip()
    agence_depart_id = request.data.get('agence_depart')
    agence_retrait_id = request.data.get('agence_retrait')
    montant = request.data.get('montant')

    if not expediteur_nom or not expediteur_telephone or not beneficiaire_nom or not beneficiaire_telephone:
        return Response({'erreur': 'Informations expediteur et beneficiaire obligatoires.'}, status=400)
    if not agence_depart_id or not agence_retrait_id:
        return Response({'erreur': 'Agences de depart et de retrait obligatoires.'}, status=400)
    if not montant:
        return Response({'erreur': 'Montant obligatoire.'}, status=400)

    try:
        montant = int(montant)
    except (ValueError, TypeError):
        return Response({'erreur': 'Montant invalide.'}, status=400)
    if montant < 1:
        return Response({'erreur': 'Montant invalide.'}, status=400)

    agence_depart = Agence.objects.filter(id=agence_depart_id).first()
    agence_retrait = Agence.objects.filter(id=agence_retrait_id).first()
    if not agence_depart or not agence_retrait:
        return Response({'erreur': 'Agence introuvable.'}, status=404)

    client = Client.objects.filter(user=user).first()

    demande = DemandeTransfert.objects.create(
        client=client,
        expediteur_nom=expediteur_nom,
        expediteur_telephone=expediteur_telephone,
        beneficiaire_nom=beneficiaire_nom,
        beneficiaire_telephone=beneficiaire_telephone,
        agence_depart=agence_depart,
        agence_retrait=agence_retrait,
        montant=montant,
    )
    return Response({
        'message': 'Demande enregistree.',
        'numero_demande': demande.numero_demande,
    }, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_mes_demandes_transfert(request):
    client = Client.objects.filter(user=request.user).first()
    if not client:
        return Response([])
    demandes = DemandeTransfert.objects.filter(client=client).order_by('-date_demande')
    return Response(DemandeTransfertSerializer(demandes, many=True).data)