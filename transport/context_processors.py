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
    from .tenant import compagnie_de
    # Employe connecte : sa compagnie. Sinon (page de connexion, superutilisateur) : la premiere compagnie active.
    compagnie = compagnie_de(getattr(request, 'user', None))
    return {'compagnie_info': compagnie or Compagnie.objects.filter(actif=True).first()}