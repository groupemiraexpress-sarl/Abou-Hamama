from django.urls import path
from . import views
from . import api_views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

app_name = 'transport'

urlpatterns = [
    # Espace client (public)
    path('', views.accueil, name='accueil'),
    path('suivi/', views.suivi, name='suivi'),
    path('voyages/', views.recherche_voyage, name='recherche_voyage'),

    # Espace employé (connexion requise)
    path('espace/connexion/', views.connexion_employe, name='connexion'),
    path('espace/deconnexion/', views.deconnexion_employe, name='deconnexion'),
    path('espace/', views.tableau_bord, name='tableau_bord'),

    # Guichetier — vente de billets
    path('espace/vendre-billet/', views.vendre_billet, name='vendre_billet'),
    path('espace/billet/<int:reservation_id>/', views.billet_confirme, name='billet_confirme'),

    # Agent colis — enregistrement de colis
    path('espace/gerer-colis/', views.gerer_colis, name='gerer_colis'),
    path('espace/colis/<int:colis_id>/', views.colis_confirme, name='colis_confirme'),

    # Agent transfert — envoi d'argent
    path('espace/gerer-transfert/', views.gerer_transfert, name='gerer_transfert'),
    path('espace/transfert/<int:transfert_id>/', views.transfert_confirme, name='transfert_confirme'),

    # Comptable — caisse & finances
    path('espace/caisse/', views.caisse_finances, name='caisse_finances'),

    # RH — recrutement chauffeur
    path('espace/recruter-chauffeur/', views.recruter_chauffeur, name='recruter_chauffeur'),
    path('espace/chauffeur/<int:chauffeur_id>/', views.chauffeur_confirme, name='chauffeur_confirme'),

    # PDG — vue compagnie
    path('espace/vue-compagnie/', views.vue_compagnie, name='vue_compagnie'),

    # Responsable d'agence — vue agence
    path('espace/vue-agence/', views.vue_agence, name='vue_agence'),

    # Listes de consultation
    path('espace/liste-billets/', views.liste_billets, name='liste_billets'),
    path('espace/liste-colis/', views.liste_colis, name='liste_colis'),
    path('espace/liste-transferts/', views.liste_transferts, name='liste_transferts'),

    # Maintenance des véhicules
    path('espace/entretien/', views.gerer_entretien, name='gerer_entretien'),
    path('espace/flotte/', views.liste_entretiens, name='liste_entretiens'),

    path('espace/carburant/', views.gerer_carburant, name='gerer_carburant'),
    path('espace/liste-carburant/', views.liste_carburant, name='liste_carburant'),
    path('espace/billet/<int:reservation_id>/modifier/', views.modifier_billet, name='modifier_billet'),

    # API (pour la future application mobile)
    path('api/voyages/', api_views.api_voyages, name='api_voyages'),
    path('api/promotions/', api_views.api_promotions, name='api_promotions'),
    path('api/agences/', api_views.api_agences, name='api_agences'),
    path('api/demande-colis/', api_views.api_creer_demande_colis, name='api_creer_demande_colis'),
    path('api/mes-demandes-colis/', api_views.api_mes_demandes_colis, name='api_mes_demandes_colis'),
    path('api/demande-transfert/', api_views.api_creer_demande_transfert, name='api_creer_demande_transfert'),
    path('api/mes-demandes-transfert/', api_views.api_mes_demandes_transfert, name='api_mes_demandes_transfert'),
    path('api/colis/<str:code_suivi>/', api_views.api_suivi_colis, name='api_suivi_colis'),
    path('api/transfert/<str:code_transfert>/', api_views.api_suivi_transfert, name='api_suivi_transfert'),

    # API — Authentification des comptes clients (JWT)
    path('api/inscription/', api_views.api_inscription, name='api_inscription'),
    path('api/connexion/', TokenObtainPairView.as_view(), name='api_connexion'),
    path('api/token-refresh/', TokenRefreshView.as_view(), name='api_token_refresh'),
    path('api/mon-profil/', api_views.api_mon_profil, name='api_mon_profil'),
    path('api/modifier-profil/', api_views.api_modifier_profil, name='api_modifier_profil'),
    path('api/changer-mot-de-passe/', api_views.api_changer_mot_de_passe, name='api_changer_mot_de_passe'),
    path('api/valider-email/<str:uidb64>/<str:token>/', api_views.api_valider_email, name='api_valider_email'),

    # API — Réservations (client connecté)
    path('api/reserver/', api_views.api_reserver, name='api_reserver'),
    path('api/mes-billets/', api_views.api_mes_billets, name='api_mes_billets'),

    # API — Sièges
    path('api/voyage/<int:voyage_id>/sieges/', api_views.api_sieges_voyage, name='api_sieges_voyage'),
    path('api/reserver-siege/', api_views.api_reserver_siege, name='api_reserver_siege'),
    path('api/payer-reservation/', api_views.api_payer_reservation, name='api_payer_reservation'),
    path('api/annuler-demande-colis/', api_views.api_annuler_demande_colis, name='api_annuler_demande_colis'),
    path('api/annuler-demande-transfert/', api_views.api_annuler_demande_transfert, name='api_annuler_demande_transfert'),
]
