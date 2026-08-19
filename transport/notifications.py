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
            corps_reponse = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        logger.error("Echec de l'envoi de notification(s) push Expo (HTTP %s): %s", e.code, e.read().decode("utf-8", "replace"))
        return
    except Exception:
        logger.exception("Echec de l'envoi de notification(s) push Expo")
        return

    try:
        reponse = json.loads(corps_reponse)
    except ValueError:
        logger.error("Reponse Expo illisible: %s", corps_reponse)
        return

    tickets = reponse.get("data") if isinstance(reponse, dict) else None
    if isinstance(tickets, list):
        for ticket in tickets:
            if isinstance(ticket, dict) and ticket.get("status") == "error":
                logger.error("Erreur push Expo: %s", ticket)
    if isinstance(reponse, dict) and reponse.get("errors"):
        logger.error("Erreur push Expo (requete): %s", reponse["errors"])


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
