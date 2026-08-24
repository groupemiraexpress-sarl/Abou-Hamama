"""
Envoi d'emails transactionnels via l'API HTTPS de Brevo.

PythonAnywhere bloque les connexions SMTP sortantes (meme vers un relai
comme Brevo, teste et confirme), donc on ne peut pas utiliser le backend
SMTP standard de Django. On utilise a la place l'API HTTP de Brevo
(https://api.brevo.com/v3/smtp/email), qui passe par une simple requete
HTTPS - non bloquee.

N'utilise que la bibliotheque standard (urllib), comme notifications.py,
pour eviter une dependance externe supplementaire.
"""
import json
import logging
import urllib.request
import urllib.error

from django.conf import settings

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def envoyer_email(destinataire, sujet, corps_texte):
    """
    Envoie un email transactionnel via l'API Brevo.
    Ne leve jamais d'exception : renvoie True/False.
    """
    if not settings.BREVO_API_KEY:
        logger.warning("BREVO_API_KEY non configuree, email non envoye a %s", destinataire)
        return False
    if not settings.EMAIL_FROM_ADDRESS:
        logger.warning("EMAIL_FROM_ADDRESS non configuree, email non envoye a %s", destinataire)
        return False

    try:
        data = json.dumps({
            "sender": {"name": "Express Abou Hamama", "email": settings.EMAIL_FROM_ADDRESS},
            "to": [{"email": destinataire}],
            "subject": sujet,
            "textContent": corps_texte,
        }).encode("utf-8")
        req = urllib.request.Request(
            BREVO_API_URL,
            data=data,
            headers={
                "accept": "application/json",
                "api-key": settings.BREVO_API_KEY,
                "content-type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
        return True
    except urllib.error.HTTPError as e:
        logger.error(
            "Echec envoi email Brevo (HTTP %s) a %s : %s",
            e.code, destinataire, e.read().decode("utf-8", "replace"),
        )
        return False
    except Exception:
        logger.exception("Echec envoi email Brevo a %s", destinataire)
        return False
