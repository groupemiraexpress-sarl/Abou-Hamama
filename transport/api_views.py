from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated

from .models import Voyage, Colis, TransfertArgent
from .serializers import VoyageSerializer, ColisSerializer, TransfertArgentSerializer


@api_view(['GET'])
def api_voyages(request):
    """
    Liste des voyages à venir (départs futurs).
    L'app mobile appelle cette adresse pour afficher les voyages disponibles.
    """
    aujourd_hui = timezone.now().date()
    voyages = Voyage.objects.select_related('trajet', 'bus').filter(
        date_depart__gte=aujourd_hui
    ).order_by('date_depart')

    serializer = VoyageSerializer(voyages, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def api_suivi_colis(request, code_suivi):
    """
    Suivi d'un colis par son code.
    L'app appelle /api/colis/COL-XXXX/ pour suivre un colis.
    """
    colis = Colis.objects.filter(code_suivi=code_suivi).first()
    if not colis:
        return Response({'erreur': 'Colis introuvable'}, status=404)

    serializer = ColisSerializer(colis)
    return Response(serializer.data)


@api_view(['GET'])
def api_suivi_transfert(request, code_transfert):
    """
    Suivi d'un transfert par son code.
    L'app appelle /api/transfert/TRF-XXXX/ pour suivre un transfert.
    """
    transfert = TransfertArgent.objects.filter(code_transfert=code_transfert).first()
    if not transfert:
        return Response({'erreur': 'Transfert introuvable'}, status=404)

    serializer = TransfertArgentSerializer(transfert)
    return Response(serializer.data)

@api_view(['POST'])
def api_inscription(request):
    """
    Inscription d'un nouveau client.
    Reçoit : username, email, password.
    Crée le compte et renvoie directement les tokens JWT (connexion automatique).
    """
    username = request.data.get('username', '').strip()
    email = request.data.get('email', '').strip()
    password = request.data.get('password', '')

    # Vérifications de base
    if not username or not password:
        return Response({'erreur': 'Nom d\'utilisateur et mot de passe obligatoires.'}, status=400)

    if len(password) < 6:
        return Response({'erreur': 'Le mot de passe doit faire au moins 6 caractères.'}, status=400)

    if User.objects.filter(username=username).exists():
        return Response({'erreur': 'Ce nom d\'utilisateur est déjà pris.'}, status=400)

    # Création du compte (le mot de passe est chiffré automatiquement)
    user = User.objects.create_user(username=username, email=email, password=password)

    # Génération des tokens JWT (connexion automatique après inscription)
    refresh = RefreshToken.for_user(user)

    return Response({
        'message': 'Compte créé avec succès.',
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }, status=201)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_mon_profil(request):
    """
    Renvoie les infos du client connecté.
    Protégée : nécessite un token JWT valide.
    """
    user = request.user
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'date_inscription': user.date_joined,
    })