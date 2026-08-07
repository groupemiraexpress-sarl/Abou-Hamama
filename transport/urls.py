from django.urls import path
from . import views
from . import api_views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

app_name = 'transport'

urlpatterns = [
    # Guichetier - vente de billets (connexion via admin Django)
    path('espace/vendre-billet/', views.vendre_billet, name='vendre_billet'),
    path('espace/mon-profil/', views.mon_profil, name='mon_profil'),
    path('espace/rapport-agence/', views.rapport_agence, name='rapport_agence'),
    path('espace/rapport-finances/', views.rapport_finances_agence, name='rapport_finances_agence'),
    path('espace/rapport-maintenance/', views.rapport_maintenance_agence, name='rapport_maintenance_agence'),
    path('espace/rapport-mon-agence/', views.rapport_mon_agence, name='rapport_mon_agence'),
    path('espace/carte-bus/', views.carte_bus_temps_reel, name='carte_bus_temps_reel'),
    path('espace/manifeste-bord/', views.manifeste_bord, name='manifeste_bord'),
    path('espace/tableau-pdg/', views.tableau_bord_pdg, name='tableau_bord_pdg'),
    path('espace/billet/<int:reservation_id>/', views.billet_confirme, name='billet_confirme'),
    path('espace/billets-confirmes/', views.billets_confirmes, name='billets_confirmes'),
    path('espace/liste-billets/', views.liste_billets, name='liste_billets'),
    path('espace/billet/<int:reservation_id>/modifier/', views.modifier_billet, name='modifier_billet'),

    # API (pour l'application mobile)
    path('api/voyages/', api_views.api_voyages, name='api_voyages'),
    path('api/promotions/', api_views.api_promotions, name='api_promotions'),
    path('api/agences/', api_views.api_agences, name='api_agences'),
    path('api/demande-colis/', api_views.api_creer_demande_colis, name='api_creer_demande_colis'),
    path('api/mes-demandes-colis/', api_views.api_mes_demandes_colis, name='api_mes_demandes_colis'),
    path('api/demande-transfert/', api_views.api_creer_demande_transfert, name='api_creer_demande_transfert'),
    path('api/mes-demandes-transfert/', api_views.api_mes_demandes_transfert, name='api_mes_demandes_transfert'),
    path('api/colis/<str:code_suivi>/', api_views.api_suivi_colis, name='api_suivi_colis'),
    path('api/transfert/<str:code_transfert>/', api_views.api_suivi_transfert, name='api_suivi_transfert'),

    # API - Authentification des comptes clients (JWT)
    path('api/inscription/', api_views.api_inscription, name='api_inscription'),
    path('api/connexion/', TokenObtainPairView.as_view(), name='api_connexion'),
    path('api/token-refresh/', TokenRefreshView.as_view(), name='api_token_refresh'),
    path('api/mon-profil/', api_views.api_mon_profil, name='api_mon_profil'),
    path('api/modifier-profil/', api_views.api_modifier_profil, name='api_modifier_profil'),
    path('api/changer-mot-de-passe/', api_views.api_changer_mot_de_passe, name='api_changer_mot_de_passe'),
    path('api/valider-email/<str:uidb64>/<str:token>/', api_views.api_valider_email, name='api_valider_email'),

    # API - Reservations (client connecte)
    path('api/reserver/', api_views.api_reserver, name='api_reserver'),
    path('api/mes-billets/', api_views.api_mes_billets, name='api_mes_billets'),
    path('api/donner-avis/', api_views.api_donner_avis),

    # API - Sieges
    path('api/voyage/<int:voyage_id>/sieges/', api_views.api_sieges_voyage, name='api_sieges_voyage'),
    path('api/reserver-siege/', api_views.api_reserver_siege, name='api_reserver_siege'),
    path('api/payer-reservation/', api_views.api_payer_reservation, name='api_payer_reservation'),
    path('api/annuler-demande-colis/', api_views.api_annuler_demande_colis, name='api_annuler_demande_colis'),
    path('api/annuler-demande-transfert/', api_views.api_annuler_demande_transfert, name='api_annuler_demande_transfert'),

# API - Chauffeurs et suivi GPS
    path('api/chauffeur/connexion/', api_views.api_connexion_chauffeur, name='api_connexion_chauffeur'),
    path('api/chauffeur/mes-voyages/', api_views.api_mes_voyages_chauffeur, name='api_mes_voyages_chauffeur'),
    path('api/chauffeur/position/', api_views.api_enregistrer_position, name='api_enregistrer_position'),
    path('api/voyage/<int:voyage_id>/positions/', api_views.api_positions_voyage, name='api_positions_voyage'),
    path('api/chauffeur/terminer-voyage/', api_views.api_terminer_voyage, name='api_terminer_voyage'),
    path('api/securite/connexion/', api_views.api_connexion_securite, name='api_connexion_securite'),
    path('api/securite/scanner-billet/', api_views.api_scanner_billet, name='api_scanner_billet'),
    path('api/voyage/<int:voyage_id>/historique-positions/', api_views.api_historique_positions_voyage, name='api_historique_positions_voyage'),
]