from django.contrib import admin
from .models import (
    Compagnie, Agence, Bus, Chauffeur, Trajet, Voyage,
    Client, Reservation, Colis, Employe, TransfertArgent,
    Entretien, PleinCarburant, Promotion, DemandeColis, DemandeTransfert
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


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ('titre', 'date_debut', 'date_fin', 'actif')
    list_filter = ('actif',)
    search_fields = ('titre', 'texte')
    ordering = ('-date_creation',)


@admin.register(DemandeColis)
class DemandeColisAdmin(admin.ModelAdmin):
    list_display = ('numero_demande', 'expediteur_nom', 'destinataire_nom', 'agence_depart', 'agence_arrivee', 'poids_estime', 'poids_reel', 'prix', 'statut', 'date_demande')
    list_filter = ('statut', 'agence_depart', 'agence_arrivee')
    search_fields = ('numero_demande', 'expediteur_nom', 'expediteur_telephone', 'destinataire_nom')
    list_editable = ('poids_reel', 'prix', 'statut')
    ordering = ('-date_demande',)
    actions = ['valider_et_creer_colis']

    @admin.action(description="Valider et creer le colis")
    def valider_et_creer_colis(self, request, queryset):
        crees = 0
        ignorees = 0
        for demande in queryset:
            if demande.statut != 'en_attente':
                ignorees += 1
                continue
            if not demande.poids_reel or not demande.prix:
                ignorees += 1
                continue
            compagnie = demande.agence_depart.compagnie
            colis = Colis.objects.create(
                compagnie=compagnie,
                expediteur_nom=demande.expediteur_nom,
                expediteur_telephone=demande.expediteur_telephone,
                destinataire_nom=demande.destinataire_nom,
                destinataire_telephone=demande.destinataire_telephone,
                agence_depart=demande.agence_depart,
                agence_arrivee=demande.agence_arrivee,
                description=demande.description,
                poids_kg=demande.poids_reel,
                prix=demande.prix,
                statut='enregistre',
            )
            demande.colis = colis
            demande.statut = 'validee'
            demande.save()
            crees += 1
        if crees:
            self.message_user(request, f"{crees} colis cree(s) avec succes.")
        if ignorees:
            self.message_user(request, f"{ignorees} demande(s) ignoree(s) : deja traitee ou poids/prix manquant.", level='warning')


@admin.register(DemandeTransfert)
class DemandeTransfertAdmin(admin.ModelAdmin):
    list_display = ('numero_demande', 'expediteur_nom', 'beneficiaire_nom', 'agence_depart', 'agence_retrait', 'montant', 'frais', 'statut', 'date_demande')
    list_filter = ('statut', 'agence_depart', 'agence_retrait')
    search_fields = ('numero_demande', 'expediteur_nom', 'expediteur_telephone', 'beneficiaire_nom')
    list_editable = ('frais',)
    ordering = ('-date_demande',)
    readonly_fields = ('numero_demande', 'date_demande', 'transfert')
    actions = ['valider_et_creer_transfert']

    @admin.action(description="Valider et creer le transfert")
    def valider_et_creer_transfert(self, request, queryset):
        crees = 0
        ignorees = 0
        for demande in queryset:
            if demande.statut != 'en_attente':
                ignorees += 1
                continue
            if demande.frais is None:
                ignorees += 1
                continue
            compagnie = demande.agence_depart.compagnie
            transfert = TransfertArgent.objects.create(
                compagnie=compagnie,
                expediteur_nom=demande.expediteur_nom,
                expediteur_telephone=demande.expediteur_telephone,
                beneficiaire_nom=demande.beneficiaire_nom,
                beneficiaire_telephone=demande.beneficiaire_telephone,
                agence_depart=demande.agence_depart,
                agence_retrait=demande.agence_retrait,
                montant=demande.montant,
                frais=demande.frais,
                statut='en_attente',
            )
            demande.transfert = transfert
            demande.statut = 'validee'
            demande.save()
            crees += 1
        if crees:
            self.message_user(request, f"{crees} transfert(s) cree(s) avec succes.")
        if ignorees:
            self.message_user(request, f"{ignorees} demande(s) ignoree(s) : deja validee, ou frais manquants.", level='warning')