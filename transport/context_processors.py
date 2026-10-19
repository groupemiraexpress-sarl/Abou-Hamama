

def branding(request):
    """
    Marque (nom, logo, couleurs, slogan, pied de page) de la compagnie courante, disponible dans
    tous les templates : {{ branding.nom_entreprise }}, {{ branding.logo_url }}, etc.
    """
    from django.templatetags.static import static
    from .branding import BRANDING, assombrir, logo_par_defaut
    from .models import Compagnie
    from .tenant import compagnie_courante

    marque = dict(BRANDING)
    compagnie = compagnie_courante(request)
    marque['nom_complet'] = marque['nom_entreprise']
    marque['logo_url'] = static('transport/logo_abou_hamama.png')
    if compagnie is not None:
        couleur = compagnie.couleur_principale or marque['couleur_principale']
        marque.update(
            nom_entreprise=compagnie.nom,
            nom_complet=compagnie.nom_affiche or compagnie.nom,
            slogan=compagnie.slogan or marque['slogan'],
            couleur_principale=couleur,
            couleur_hover=assombrir(couleur),
            pied_de_page=compagnie.pied_de_page or f"Agence {compagnie.nom}",
            code=compagnie.code,
        )
        if compagnie.logo:
            marque['logo_url'] = compagnie.logo.url
        elif Compagnie.objects.order_by('id').values_list('pk', flat=True).first() != compagnie.pk:
            # compagnies suivantes sans logo : pastille avec leurs initiales
            marque['logo_url'] = logo_par_defaut(compagnie.nom_affiche or compagnie.nom, couleur)
    return {'branding': marque}


def compagnie_info(request):
    """
    Rend la fiche Compagnie (telephones a afficher sur les billets/recus...)
    disponible dans tous les templates via {{ compagnie_info.telephones_recus }}.
    Modifiable depuis l'admin (fiche Compagnie), sans toucher au code.
    """
    from .models import Compagnie
    from .tenant import compagnie_courante
    return {'compagnie_info': compagnie_courante(request)}