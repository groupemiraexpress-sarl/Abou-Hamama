from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str

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
    Crée le compte (inactif) et envoie un email de validation.
    Le compte devient actif quand le client clique sur le lien.
    """
    username = request.data.get('username', '').strip()
    email = request.data.get('email', '').strip()
    password = request.data.get('password', '')

    if not username or not password:
        return Response({'erreur': 'Nom d\'utilisateur et mot de passe obligatoires.'}, status=400)

    if not email:
        return Response({'erreur': 'L\'email est obligatoire pour la validation du compte.'}, status=400)

    if len(password) < 6:
        return Response({'erreur': 'Le mot de passe doit faire au moins 6 caractères.'}, status=400)

    if User.objects.filter(username=username).exists():
        return Response({'erreur': 'Ce nom d\'utilisateur est déjà pris.'}, status=400)

    # Création du compte INACTIF (en attente de validation email)
    user = User.objects.create_user(username=username, email=email, password=password)
    user.is_active = False
    user.save()

    # Génération du lien de validation unique et sécurisé
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    lien_validation = f"{settings.SITE_URL}/api/valider-email/{uid}/{token}/"

    # Envoi de l'email (affiché dans le terminal en mode console)
    send_mail(
        subject='Validez votre compte Express Abou Hamama',
        message=f'Bienvenue {username} !\n\nCliquez sur ce lien pour valider votre compte :\n{lien_validation}\n\nMerci.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )

    return Response({
        'message': 'Compte créé. Un email de validation a été envoyé.',
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


@api_view(['GET'])
def api_valider_email(request, uidb64, token):
    """
    Valide le compte quand le client clique sur le lien reçu par email.
    Active le compte si le lien est valide.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if user.is_active:
            return Response({'message': 'Ce compte est déjà validé.'})
        user.is_active = True
        user.save()
        return Response({'message': 'Compte validé avec succès ! Vous pouvez maintenant vous connecter.'})
    else:
        return Response({'erreur': 'Lien de validation invalide ou expiré.'}, status=400)