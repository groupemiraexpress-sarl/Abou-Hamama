"""Envoi de notifications push aux telephones des clients via l'API Expo.

Utilise uniquement la bibliotheque standard (urllib) pour eviter d'ajouter
une dependance externe (requests) qui devrait etre installee manuellement
sur le serveur.
"""
import json
import logging
import urllib.request
import urllib.error

from .models import PushToken, Client

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def _envoyer_vers_expo(messages):
    """Envoie une liste de messages au format attendu par l'API push d'Expo.
    Ne leve jamais d'exception : une notification qui echoue ne doit jamais
    casser une action metier (ex: confirmation de remise d'un colis).
    """
    if not messages:
        return
    try:
        data = json.dumps(messages).encode("utf-8")
        req = urllib.request.Request(
            EXPO_PUSH_URL,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
    except Exception:
        logger.exception("Echec de l'envoi de notification(s) push Expo")


def notifier_utilisateur(user, titre, corps, data=None):
    """Envoie une notification push a tous les appareils enregistres pour cet utilisateur."""
    if user is None:
        return
    tokens = list(PushToken.objects.filter(user=user).values_list("token", flat=True))
    if not tokens:
        return
    messages = [
        {
            "to": token,
            "title": titre,
            "body": corps,
            "data": data or {},
            "sound": "default",
        }
        for token in tokens
    ]
    _envoyer_vers_expo(messages)


def notifier_telephone(telephone, titre, corps, data=None):
    """Trouve le compte client lie a ce numero de telephone (s'il existe) et lui envoie une notification."""
    if not telephone:
        return
    client = Client.objects.filter(telephone=telephone, user__isnull=False).select_related("user").first()
    if client is None:
        return
    notifier_utilisateur(client.user, titre, corps, data)
