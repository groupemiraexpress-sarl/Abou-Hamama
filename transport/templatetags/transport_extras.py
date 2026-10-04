from django import template

from transport.models import Client

register = template.Library()

_LIBELLES = dict(Client.TYPE_PIECE_CHOICES)


@register.filter
def libelle_piece(valeur):
    """'cni' -> "Carte nationale d'identite" ; une ancienne valeur libre est affichee telle quelle."""
    return _LIBELLES.get(valeur, valeur or '')
