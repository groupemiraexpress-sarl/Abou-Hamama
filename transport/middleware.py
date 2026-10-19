from django.contrib.auth import logout
from django.shortcuts import redirect

from .tenant import compagnie_du_domaine


class CompagnieDomaineMiddleware:
    """
    Reconnait la compagnie d'apres l'adresse web (request.compagnie_domaine).
    Un employe connecte a l'adresse d'UNE compagnie alors que son compte appartient a une
    autre est deconnecte : on ne peut pas utiliser le site de l'entreprise A avec un compte de B.
    (Le superutilisateur, administrateur de la plateforme, peut se connecter partout.)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.compagnie_domaine = compagnie_du_domaine(request.get_host())
        compagnie = request.compagnie_domaine
        user = getattr(request, 'user', None)
        if (
            compagnie is not None and user is not None and user.is_authenticated and not user.is_superuser
            and not request.path.startswith(('/api/', '/static/', '/media/'))
        ):
            employe = getattr(user, 'employe', None)
            if employe is not None and employe.compagnie_id != compagnie.id:
                logout(request)
                return redirect('admin:login')
        return self.get_response(request)
