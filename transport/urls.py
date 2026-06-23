from django.urls import path
from . import views

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
]
