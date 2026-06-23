from django.contrib import admin
from .models import (
    Compagnie, Agence, Bus, Chauffeur, Trajet, Voyage,
    Client, Reservation, Colis, Employe, TransfertArgent,
    Entretien, PleinCarburant
)


@admin.register(Compagnie)
class CompagnieAdmin(admin.ModelAdmin):
    list_display = ('nom', 'sigle', 'siege_social', 'telephone', 'actif')
    list_filter = ('actif',)
    search_fields = ('nom', 'sigle', 'siege_social')
    list_editable = ('actif',)
    ordering = ('nom',)


@admin.register(Agence)
class AgenceAdmin(admin.ModelAdmin):
    list_display = ('nom', 'ville', 'compagnie', 'telephone', 'responsable', 'actif')
    list_filter = ('compagnie', 'ville', 'actif')
    search_fields = ('nom', 'ville', 'adresse', 'responsable')
    list_editable = ('actif',)
    ordering = ('compagnie', 'ville', 'nom')


@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ('immatriculation', 'marque', 'modele', 'capacite', 'statut', 'compagnie', 'kilometrage')
    list_filter = ('statut', 'compagnie', 'marque')
    search_fields = ('immatriculation', 'marque', 'modele')
    list_editable = ('statut',)
    ordering = ('immatriculation',)


@admin.register(Chauffeur)
class ChauffeurAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prenom', 'telephone', 'numero_permis', 'date_expiration_permis', 'statut', 'compagnie', 'actif')
    list_filter = ('statut', 'compagnie', 'actif')
    search_fields = ('nom', 'prenom', 'numero_permis', 'telephone')
    list_editable = ('statut',)
    ordering = ('nom', 'prenom')


@admin.register(Trajet)
class TrajetAdmin(admin.ModelAdmin):
    list_display = ('ville_depart', 'ville_arrivee', 'distance_km', 'duree_estimee_heures', 'prix_base', 'compagnie', 'actif')
    list_filter = ('compagnie', 'actif', 'ville_depart')
    search_fields = ('ville_depart', 'ville_arrivee')
    list_editable = ('prix_base', 'actif')
    ordering = ('ville_depart', 'ville_arrivee')


@admin.register(Voyage)
class VoyageAdmin(admin.ModelAdmin):
    list_display = ('trajet', 'date_depart', 'heure_depart', 'bus', 'chauffeur', 'prix', 'places_disponibles', 'statut')
    list_filter = ('statut', 'date_depart', 'trajet__compagnie', 'bus')
    search_fields = ('trajet__ville_depart', 'trajet__ville_arrivee', 'bus__immatriculation')
    list_editable = ('statut',)
    ordering = ('-date_depart', '-heure_depart')
    date_hierarchy = 'date_depart'


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prenom', 'telephone', 'email', 'type_client', 'ville_residence', 'nombre_voyages', 'actif')
    list_filter = ('type_client', 'ville_residence', 'actif')
    search_fields = ('nom', 'prenom', 'telephone', 'email', 'cni')
    ordering = ('nom', 'prenom')


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('numero_reservation', 'client', 'voyage', 'nombre_places', 'montant_total', 'statut', 'mode_paiement', 'date_reservation')
    list_filter = ('statut', 'mode_paiement', 'voyage__date_depart', 'agence')
    search_fields = ('numero_reservation', 'client__nom', 'client__telephone')
    list_editable = ('statut',)
    ordering = ('-date_reservation',)
    date_hierarchy = 'date_reservation'


@admin.register(Colis)
class ColisAdmin(admin.ModelAdmin):
    list_display = ('code_suivi', 'expediteur_nom', 'destinataire_nom', 'agence_depart', 'agence_arrivee', 'poids_kg', 'prix', 'statut', 'date_enregistrement')
    list_filter = ('statut', 'agence_depart', 'agence_arrivee', 'compagnie')
    search_fields = ('code_suivi', 'expediteur_nom', 'expediteur_telephone', 'destinataire_nom', 'destinataire_telephone')
    list_editable = ('statut',)
    ordering = ('-date_enregistrement',)
    date_hierarchy = 'date_enregistrement'


@admin.register(Employe)
class EmployeAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prenom', 'poste', 'agence', 'telephone', 'compte_lie', 'compagnie', 'actif')
    list_filter = ('poste', 'actif', 'compagnie', 'agence')
    search_fields = ('nom', 'prenom', 'telephone', 'cni')
    list_editable = ('actif',)
    ordering = ('nom', 'prenom')
    autocomplete_fields = ('user',)
    fieldsets = (
        ("Compte de connexion", {
            'fields': ('user',),
            'description': "Liez ici le compte de connexion de l'employé. "
                           "Créez d'abord le compte dans Utilisateurs (avec son email comme identifiant), "
                           "puis sélectionnez-le ici.",
        }),
        ("Informations personnelles", {
            'fields': ('nom', 'prenom', 'telephone', 'cni'),
        }),
        ("Poste et affectation", {
            'fields': ('poste', 'compagnie', 'agence'),
        }),
        ("Emploi", {
            'fields': ('date_embauche', 'salaire', 'actif'),
        }),
    )

    @admin.display(description="Compte lié")
    def compte_lie(self, obj):
        return obj.user.username if obj.user else "—"


@admin.register(TransfertArgent)
class TransfertArgentAdmin(admin.ModelAdmin):
    list_display = ('code_transfert', 'expediteur_nom', 'beneficiaire_nom', 'montant', 'frais', 'agence_depart', 'agence_retrait', 'statut', 'date_envoi')
    list_filter = ('statut', 'agence_depart', 'agence_retrait', 'compagnie')
    search_fields = ('code_transfert', 'expediteur_nom', 'expediteur_telephone', 'beneficiaire_nom', 'beneficiaire_telephone', 'code_retrait')
    readonly_fields = ('code_transfert', 'code_retrait', 'date_envoi')
    list_editable = ('statut',)
    ordering = ('-date_envoi',)
    date_hierarchy = 'date_envoi'

@admin.register(Entretien)
class EntretienAdmin(admin.ModelAdmin):
    list_display = ('bus', 'type_entretien', 'date_entretien', 'kilometrage', 'cout', 'cree_par')
    list_filter = ('type_entretien', 'date_entretien', 'bus')
    search_fields = ('bus__immatriculation', 'description')
    ordering = ('-date_entretien',)
    autocomplete_fields = ('bus', 'cree_par')


@admin.register(PleinCarburant)
class PleinCarburantAdmin(admin.ModelAdmin):
    list_display = ('bus', 'voyage', 'date_plein', 'litres', 'montant', 'cree_par')
    list_filter = ('date_plein', 'bus')
    search_fields = ('bus__immatriculation',)
    ordering = ('-date_plein',)
    autocomplete_fields = ('bus', 'voyage', 'cree_par')