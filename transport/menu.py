"""
Menu lateral de l'administration : une liste courte, avec icones, selon le poste de l'employe.

  - superutilisateur (administrateur de la plateforme) : Plateforme, Facturation, Creer une entreprise
    + tout le reste du site range dans « Administration » ;
  - autre compte : seulement ce que son poste lui permet (droits Django + profil du tableau de bord).

Les modeles qui ne sont pas dans la liste principale restent accessibles, ranges dans « Autres ».
"""
from django.contrib import admin
from django.urls import NoReverseMatch, reverse
from django.utils.translation import gettext_lazy as _

from .admin_filtres import profil_tableau_bord

# (modele, libelle, icone) : pages d'administration affichees dans le menu principal, dans cet ordre
MODELES_PRINCIPAUX = [
    ('Reservation', _("Reservations"), 'fa-clipboard-list'),
    ('Voyage', _("Voyages"), 'fa-route'),
    ('Colis', _("Colis"), 'fa-box'),
    ('TransfertArgent', _("Transferts d'argent"), 'fa-money-bill-transfer'),
    ('Client', _("Clients"), 'fa-users'),
    ('Bus', _("Bus"), 'fa-bus'),
    ('Chauffeur', _("Chauffeurs"), 'fa-id-card'),
    ('Agence', _("Agences"), 'fa-building'),
    ('Employe', _("Employes"), 'fa-user-tie'),
    ('ArticleStock', _("Stock"), 'fa-boxes-stacked'),
    ('Compagnie', _("Entreprise"), 'fa-gear'),
]


def _url(nom, *args):
    try:
        return reverse(nom, args=args)
    except NoReverseMatch:
        return None


def _lien(libelle, icone, url, actif_si_prefixe=True):
    return {'libelle': libelle, 'icone': icone, 'url': url, 'prefixe': actif_si_prefixe}


def construire_menu(request):
    """Renvoie {'principal': [...], 'autres': [(titre, [liens])]} ; chaque lien : libelle, icone, url, actif."""
    user = request.user
    if not (user.is_authenticated and user.is_staff):
        return {'principal': [], 'autres': []}

    employe = getattr(user, 'employe', None)
    est_pdg = employe is not None and employe.poste == 'pdg'
    profil = profil_tableau_bord(user)
    principal = [_lien(_("Accueil"), 'fa-house', _url('admin:index'), actif_si_prefixe=False)]

    if user.is_superuser:
        principal += [
            _lien(_("Plateforme (entreprises)"), 'fa-layer-group', _url('transport:plateforme')),
            _lien(_("Facturation"), 'fa-file-invoice-dollar', _url('transport:facturation')),
            _lien(_("Creer une entreprise"), 'fa-circle-plus', _url('transport:nouvelle_compagnie')),
        ]
    else:
        if profil.get('voit_raccourci_vente'):
            principal.append(_lien(_("Vendre un billet"), 'fa-ticket', _url('transport:vendre_billet')))
        if profil.get('voit_raccourci_caisse'):
            principal.append(_lien(_("Caisse"), 'fa-cash-register', _url('transport:caisse')))
        if profil.get('voit_raccourci_dettes'):
            principal.append(_lien(_("Dettes (billets non payes)"), 'fa-file-invoice', _url('transport:dettes')))

    try:
        applications = admin.site.get_app_list(request)
    except Exception:
        applications = []
    modeles = {}
    for appli in applications:
        for m in appli['models']:
            if m.get('admin_url'):
                modeles[(appli['app_label'], m['object_name'])] = (appli, m)

    deja = set()
    if not user.is_superuser:
        for objet, libelle, icone in MODELES_PRINCIPAUX:
            trouve = modeles.get(('transport', objet))
            if trouve:
                principal.append(_lien(libelle, icone, trouve[1]['admin_url']))
                deja.add(('transport', objet))
        if est_pdg:
            principal.append(_lien(_("Vue d'ensemble PDG"), 'fa-chart-column', _url('transport:tableau_bord_pdg')))
            principal.append(_lien(_("Mon abonnement"), 'fa-file-invoice-dollar', _url('transport:mon_abonnement')))
        if est_pdg or (employe is not None and employe.poste in ('responsable', 'securite')):
            principal.append(_lien(_("Carte des bus en direct"), 'fa-map-location-dot', _url('transport:carte_bus_temps_reel')))
        if profil.get('voit_historique_employe'):
            principal.append(_lien(_("Mon activite / Historique par employe"), 'fa-clock-rotate-left', _url('transport:historique_employe')))

    autres = []
    for appli in applications:
        liens = [
            _lien(m['name'], 'fa-angle-right', m['admin_url'])
            for m in appli['models']
            if m.get('admin_url') and (appli['app_label'], m['object_name']) not in deja
        ]
        if liens:
            autres.append((appli['name'], liens))

    # actif = l'adresse courante commence par celle du lien (l'accueil : adresse exacte)
    chemin = request.path
    tous = principal + [lien for _titre, liens in autres for lien in liens]
    for lien in tous:
        url = lien['url'] or ''
        lien['actif'] = bool(url) and (chemin.startswith(url) if lien['prefixe'] else chemin == url)
    principal = [lien for lien in principal if lien['url']]
    titre_autres = _("Administration") if user.is_superuser else _("Autres")
    return {'principal': principal, 'autres': autres, 'titre_autres': titre_autres,
            'autre_ouvert': any(lien['actif'] for _t, liens in autres for lien in liens)}
