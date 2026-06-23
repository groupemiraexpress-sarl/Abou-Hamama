from .branding import BRANDING


def branding(request):
    """
    Rend la configuration de marque disponible dans tous les templates.
    Utilisable dans les pages via {{ branding.nom_entreprise }}, etc.
    """
    return {'branding': BRANDING}