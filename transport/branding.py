# ============================================================
# MARQUE PAR COMPAGNIE
# ============================================================
# Le nom, le logo, les couleurs, le slogan et le pied de page de chaque compagnie
# se reglent dans l'admin (menu Compagnies). Les valeurs ci-dessous ne servent
# que de secours quand aucune compagnie n'est connue.
import re
from urllib.parse import quote

BRANDING = {
    'nom_entreprise': 'Abou Hamama',
    'slogan': "Transport · Colis · Transfert d'argent",
    'couleur_principale': "#261F64",
    'couleur_hover': '#2c4a82',
    'pied_de_page': 'Agence Abou Hamama',
    'prefixe_colis': 'COL',
    'prefixe_transfert': 'TRF',
}


# Marque de la PLATEFORME (administrateur, ecran de connexion general) : logo MIRA, bleu du logo
PLATEFORME = {
    'couleur_principale': '#0B3A94',
    'slogan': "Voyage · Colis · Confiance · Partout",
}


def assombrir(couleur, facteur=0.82):
    """Couleur #RRGGBB un peu plus foncee (survol des boutons)."""
    if not re.fullmatch(r'#[0-9a-fA-F]{6}', couleur or ''):
        return BRANDING['couleur_hover']
    r, g, b = (int(couleur[i:i + 2], 16) for i in (1, 3, 5))
    return '#%02x%02x%02x' % (int(r * facteur), int(g * facteur), int(b * facteur))


def logo_par_defaut(nom, couleur):
    """Pastille avec les initiales de la compagnie (image integree, sans fichier) quand elle n'a pas de logo."""
    mots = [m for m in re.split(r'\s+', (nom or '').strip()) if m]
    initiales = ''.join(m[0] for m in mots[:2]).upper() or '?'
    if not re.fullmatch(r'#[0-9a-fA-F]{6}', couleur or ''):
        couleur = BRANDING['couleur_principale']
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        f'<circle cx="50" cy="50" r="50" fill="{couleur}"/>'
        '<text x="50" y="50" text-anchor="middle" dominant-baseline="central" '
        'font-family="Arial, sans-serif" font-size="40" font-weight="bold" fill="#ffffff">'
        f'{initiales}</text></svg>'
    )
    return 'data:image/svg+xml;charset=utf-8,' + quote(svg)
