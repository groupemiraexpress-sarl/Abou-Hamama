from .branding import BRANDING


def branding(request):
    """
    Rend la configuration de marque disponible dans tous les templates.
    Utilisable dans les pages via {{ branding.nom_entreprise }}, etc.
    """
    return {'branding': BRANDING}


def compagnie_info(request):
    """
    Rend la fiche Compagnie (telephones a afficher sur les billets/recus...)
    disponible dans tous les templates via {{ compagnie_info.telephones_recus }}.
    Modifiable depuis l'admin (fiche Compagnie), sans toucher au code.
    """
    from .models import Compagnie
    return {'compagnie_info': Compagnie.objects.filter(actif=True).first()}