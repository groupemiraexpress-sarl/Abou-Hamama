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

from .models import Voyage, Colis, TransfertArgent, Client, Reservation, Siege
from .serializers import VoyageSerializer, ColisSerializer, TransfertArgentSerializer, ReservationSerializer, SiegeSerializer


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
    email = request.data.get('email', '').strip()
    password = request.data.get('password', '')
    if not username or not password:
        return Response({'erreur': 'Nom et mot de passe obligatoires.'}, status=400)
    if not email:
        return Response({'erreur': 'Email obligatoire.'}, status=400)
    if len(password) < 6:
        return Response({'erreur': 'Mot de passe trop court (min 6).'}, status=400)
    if User.objects.filter(username=username).exists():
        return Response({'erreur': 'Nom deja pris.'}, status=400)
    user = User.objects.create_user(username=username, email=email, password=password)
    user.is_active = False
    user.save()
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
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'date_inscription': user.date_joined,
    })


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
    client = Client.objects.filter(user=user).first()
    if not client:
        client = Client.objects.filter(telephone=telephone).first()
        if not client:
            client = Client.objects.create(nom=nom, telephone=telephone, email=user.email)
        client.user = user
        client.save()
    try:
        reservation = Reservation.objects.create(
            client=client,
            voyage=voyage,
            nombre_places=nombre_places,
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
    client = Client.objects.filter(user=user).first()
    if not client:
        client = Client.objects.filter(telephone=telephone).first()
        if not client:
            client = Client.objects.create(nom=nom, telephone=telephone, email=user.email)
        client.user = user
    client.nom = nom
    client.prenom = prenom
    client.telephone = telephone
    client.type_piece = type_piece
    client.cni = numero_piece
    client.save()
    try:
        reservation = Reservation.objects.create(
            client=client,
            voyage=voyage,
            nombre_places=1,
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
