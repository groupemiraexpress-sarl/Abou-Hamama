"""
Gestion des appareils de confiance et de la regle "un seul appareil
connecte a la fois" par compte (client, chauffeur, agent de securite,
employe).

Principe, applique par authentifier_avec_verification_appareil() a chaque
connexion (une fois le mot de passe verifie par authenticate()) :

  - L'app mobile genere un identifiant unique a l'installation et l'envoie
    a chaque connexion (champ "identifiant_appareil").

  - Si cet appareil est deja connu (AppareilConfirme) pour ce compte :
    connexion autorisee, ET tous les jetons deja emis pour ce compte sont
    blacklistes -> les autres appareils eventuellement connectes seront
    deconnectes automatiquement (leur prochain rafraichissement de jeton
    echouera).

  - Si l'appareil est nouveau : aucun jeton n'est emis tout de suite. Un
    email de confirmation est envoye (si le compte a une adresse email) ;
    l'utilisateur doit cliquer sur le lien avant de pouvoir se connecter
    depuis ce nouvel appareil. Sans email enregistre, on autorise quand
    meme (impossible de demander confirmation), pour ne pas bloquer les
    comptes crees sans email.
"""
import secrets

from django.conf import settings
from django.core.mail import send_mail
from rest_framework_simplejwt.tokens import RefreshToken

from .models import AppareilConfirme, DemandeConfirmationAppareil


def _invalider_autres_sessions(user):
    """Blackliste tous les jetons de rafraichissement deja emis pour ce compte."""
    from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
    for jeton_emis in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=jeton_emis)


def _envoyer_email_confirmation(user, jeton):
    lien = settings.SITE_URL + '/api/confirmer-appareil/' + jeton + '/'
    send_mail(
        'Nouvelle connexion sur un appareil - Express Abou Hamama',
        (
            'Bonjour ' + user.username + ',\n\n'
            'Une tentative de connexion a votre compte a ete faite depuis un '
            'nouvel appareil.\n\n'
            "Si c'est bien vous, cliquez sur ce lien pour l'autoriser :\n" + lien + '\n\n'
            "Si ce n'est pas vous, ignorez cet email et changez votre mot de passe des que possible."
        ),
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True,
    )


def _emettre_jetons(user):
    refresh = RefreshToken.for_user(user)
    return {'access': str(refresh.access_token), 'refresh': str(refresh)}


def authentifier_avec_verification_appareil(user, identifiant_appareil):
    """
    A appeler juste apres authenticate(). Renvoie un tuple (statut, valeur) :
      - ('ok', {'access': ..., 'refresh': ...}) : connexion autorisee.
      - ('en_attente', "message a afficher a l'utilisateur") : email de
        confirmation envoye (ou en attente), pas de jeton emis.
    """
    identifiant_appareil = (identifiant_appareil or '').strip()

    if not identifiant_appareil:
        # Pas d'identifiant fourni (ancienne version de l'app) : on
        # n'applique pas la verification d'appareil plutot que de bloquer.
        _invalider_autres_sessions(user)
        return 'ok', _emettre_jetons(user)

    connu = AppareilConfirme.objects.filter(user=user, identifiant_appareil=identifiant_appareil).exists()
    if connu:
        _invalider_autres_sessions(user)
        return 'ok', _emettre_jetons(user)

    if not user.email:
        # Impossible d'envoyer une confirmation : on autorise directement.
        AppareilConfirme.objects.get_or_create(user=user, identifiant_appareil=identifiant_appareil)
        _invalider_autres_sessions(user)
        return 'ok', _emettre_jetons(user)

    demande = DemandeConfirmationAppareil.objects.filter(
        user=user, identifiant_appareil=identifiant_appareil, utilisee=False
    ).first()
    if not demande:
        jeton = secrets.token_urlsafe(32)
        demande = DemandeConfirmationAppareil.objects.create(
            user=user, identifiant_appareil=identifiant_appareil, jeton=jeton
        )
        _envoyer_email_confirmation(user, jeton)

    return 'en_attente', (
        'Nouvel appareil detecte. Un email de confirmation a ete envoye a '
        + user.email + '. Cliquez sur le lien puis reconnectez-vous.'
    )
