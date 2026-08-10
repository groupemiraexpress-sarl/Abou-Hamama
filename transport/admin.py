from django.contrib import admin
from .admin_filtres import FiltreAgenceMixin, FiltreAgenceListFilter
from .models import (
    Compagnie, Agence, Bus, Chauffeur, Trajet, Voyage,
    Client, Reservation, Colis, Employe, TransfertArgent,
    Entretien, PleinCarburant, Promotion, DemandeColis, DemandeTransfert, Ligne, ArretLigne,
    AlerteVoyage, AvisVoyage, QuestionFAQ
)
from django import forms
from django.contrib.auth.models import User
import secrets
import string


def _generer_mot_de_passe(longueur=8):
    """Genere un mot de passe temporaire aleatoire (lettres + chiffres)."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(longueur))


def _config_modifiable_uniquement_par_pdg(request):
    """
    Vrai uniquement pour le PDG et le superuser : utilise pour verrouiller
    l'ajout/modification/suppression sur les donnees de configuration
    partagees par toute la compagnie (Trajets, Promotions, Agences,
    Compagnie, FAQ). La consultation reste ouverte a tous les employes.
    """
    if request.user.is_superuser:
        return True
    employe = getattr(request.user, 'employe', None)
    return employe is not None and employe.poste == 'pdg'


admin.site.site_header = "Express Abou Hamama"
admin.site.site_title = "Gestion Abou Hamama"
admin.site.index_title = "Tableau de bord"


@admin.register(Compagnie)
class CompagnieAdmin(admin.ModelAdmin):
    list_display = ('nom', 'sigle', 'siege_social', 'telephone', 'actif')
    list_filter = ('actif',)
    search_fields = ('nom', 'sigle', 'siege_social')
    list_editable = ('actif',)
    ordering = ('nom',)

    def has_add_permission(self, request):
        return _config_modifiable_uniquement_par_pdg(request)

    def has_change_permission(self, request, obj=None):
        return _config_modifiable_uniquement_par_pdg(request)

    def has_delete_permission(self, request, obj=None):
        return _config_modifiable_uniquement_par_pdg(request)


@admin.register(Agence)
class AgenceAdmin(admin.ModelAdmin):
    list_display = ('nom', 'ville', 'compagnie', 'telephone', 'responsable', 'actif')
    list_filter = ('compagnie', 'ville', 'actif')
    search_fields = ('nom', 'ville', 'adresse', 'responsable')
    list_editable = ('actif',)
    ordering = ('compagnie', 'ville', 'nom')

    def has_add_permission(self, request):
        return _config_modifiable_uniquement_par_pdg(request)

    def has_change_permission(self, request, obj=None):
        return _config_modifiable_uniquement_par_pdg(request)

    def has_delete_permission(self, request, obj=None):
        return _config_modifiable_uniquement_par_pdg(request)


@admin.register(Bus)
class BusAdmin(FiltreAgenceMixin, admin.ModelAdmin):
    champs_agence = ['agence']
    champ_createur = None
    list_display = ('immatriculation', 'agence', 'marque', 'modele', 'capacite', 'statut', 'kilometrage')
    list_filter = ('statut', 'agence', 'compagnie', 'marque')
    search_fields = ('immatriculation', 'marque', 'modele')
    list_editable = ('statut',)
    ordering = ('agence__ville', 'agence__nom', 'immatriculation')


@admin.register(Chauffeur)
class ChauffeurAdmin(FiltreAgenceMixin, admin.ModelAdmin):
    champs_agence = ['agence']
    champ_createur = None
    list_display = ('nom', 'prenom', 'agence', 'telephone', 'numero_permis', 'date_expiration_permis', 'statut', 'note_moyenne_badge', 'actif')
    list_filter = ('statut', 'agence', 'compagnie', 'actif')
    search_fields = ('nom', 'prenom', 'numero_permis', 'telephone')
    list_editable = ('statut',)
    ordering = ('agence__ville', 'agence__nom', 'nom')

    def has_add_permission(self, request):
        from .admin_filtres import est_recruteur
        return est_recruteur(request.user)

    def has_change_permission(self, request, obj=None):
        from .admin_filtres import est_recruteur
        return est_recruteur(request.user)

    def has_delete_permission(self, request, obj=None):
        from .admin_filtres import voit_tout
        return voit_tout(request.user)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'agence':
            from .admin_filtres import voit_tout, agence_de
            if not voit_tout(request.user):
                agence = agence_de(request.user)
                if agence:
                    kwargs['queryset'] = Agence.objects.filter(id=agence.id)
                    kwargs['initial'] = agence.id
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description="Note moyenne")
    def note_moyenne_badge(self, obj):
        from django.utils.html import format_html
        from django.db.models import Avg
        moyenne = obj.avis.aggregate(m=Avg('note'))['m']
        if moyenne is None:
            return format_html('<span style="color:{};">Aucun avis</span>', '#9ca3af')
        if moyenne >= 4:
            couleur = '#059669'
        elif moyenne >= 3:
            couleur = '#d97706'
        else:
            couleur = '#dc2626'
        return format_html(
            '<span style="background:{}; color:#fff; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:600;">&#9733; {}/5 ({} avis)</span>',
            couleur, round(moyenne, 1), obj.avis.count()
        )


@admin.register(Trajet)
class TrajetAdmin(admin.ModelAdmin):
    list_display = ('ville_depart', 'ville_arrivee', 'distance_km', 'duree_estimee_heures', 'prix_base', 'compagnie', 'actif')
    list_filter = ('compagnie', 'actif', 'ville_depart')
    search_fields = ('ville_depart', 'ville_arrivee')
    list_editable = ('prix_base', 'actif')
    ordering = ('ville_depart', 'ville_arrivee')

    def has_add_permission(self, request):
        return _config_modifiable_uniquement_par_pdg(request)

    def has_change_permission(self, request, obj=None):
        return _config_modifiable_uniquement_par_pdg(request)

    def has_delete_permission(self, request, obj=None):
        return _config_modifiable_uniquement_par_pdg(request)


@admin.register(Voyage)
class VoyageAdmin(FiltreAgenceMixin, admin.ModelAdmin):
    champs_agence = ['bus__agence']
    champ_createur = None
    list_display = ('trajet', 'date_depart', 'heure_depart', 'bus', 'chauffeur', 'prix', 'places_disponibles', 'places_reelles', 'statut')
    list_filter = ('statut', 'date_depart', 'trajet__compagnie', 'bus')
    search_fields = ('trajet__ville_depart', 'trajet__ville_arrivee', 'bus__immatriculation')
    list_editable = ('statut',)
    ordering = ('-date_depart', '-heure_depart')
    date_hierarchy = 'date_depart'

    @admin.display(description="Places dispo (reel)")
    def places_reelles(self, obj):
        if not obj.ligne_id:
            return obj.places_disponibles
        total = obj.sieges.count()
        occupes = obj.sieges.filter(reservations__statut__in=['en_attente', 'payee']).distinct().count()
        return f"{total - occupes} / {total}"


class ClientAdminForm(forms.ModelForm):
    nom_utilisateur = forms.CharField(
        label="Nom d'utilisateur app (optionnel)", max_length=150, required=False,
        help_text="A remplir uniquement si ce client doit avoir un acces a l'application "
                   "mobile. Laisser vide pour un client comptoir classique (aucun compte cree)."
    )
    mot_de_passe = forms.CharField(
        label="Mot de passe", required=False, widget=forms.PasswordInput(render_value=False),
        help_text="Requis uniquement si un nom d'utilisateur est renseigne ci-dessus."
    )

    class Meta:
        model = Client
        exclude = ('user',)

    def clean(self):
        cleaned = super().clean()
        nom_utilisateur = cleaned.get('nom_utilisateur')
        if nom_utilisateur:
            if User.objects.filter(username=nom_utilisateur).exclude(pk=self.instance.user_id).exists():
                self.add_error('nom_utilisateur', "Ce nom d'utilisateur est deja pris.")
            if not self.instance.pk and not cleaned.get('mot_de_passe'):
                self.add_error('mot_de_passe', "Mot de passe requis pour creer le compte.")
        return cleaned


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    form = ClientAdminForm
    list_display = ('nom', 'prenom', 'telephone', 'email', 'type_client', 'niveau_badge', 'points_fidelite', 'nombre_voyages', 'code_parrainage', 'parraine_par', 'bonus_statut', 'nb_filleuls', 'actif')
    list_filter = ('type_client', 'niveau_fidelite', 'ville_residence', 'actif', ('parraine_par', admin.EmptyFieldListFilter))
    search_fields = ('nom', 'prenom', 'telephone', 'email', 'cni', 'code_parrainage')
    ordering = ('nom', 'prenom')
    readonly_fields = ('code_parrainage', 'bonus_parrainage_attribue')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is not None and obj.user_id:
            form.base_fields['nom_utilisateur'].initial = obj.user.username
        return form

    def save_model(self, request, obj, form, change):
        # NOTE : un compte Client n'a jamais acces a l'admin (pas is_staff),
        # donc pas besoin de groupe Django ici - uniquement pour les Employe.
        nom_utilisateur = form.cleaned_data.get('nom_utilisateur')
        mot_de_passe = form.cleaned_data.get('mot_de_passe')

        if nom_utilisateur:
            if obj.user:
                obj.user.username = nom_utilisateur
                if mot_de_passe:
                    obj.user.set_password(mot_de_passe)
                obj.user.first_name = obj.prenom
                obj.user.last_name = obj.nom
                obj.user.save()
            else:
                user = User.objects.create_user(
                    username=nom_utilisateur,
                    password=mot_de_passe,
                    first_name=obj.prenom,
                    last_name=obj.nom,
                )
                obj.user = user
        super().save_model(request, obj, form, change)

    @admin.display(description="Niveau", ordering='niveau_fidelite')
    def niveau_badge(self, obj):
        from django.utils.html import format_html
        couleurs = {'bronze': '#b45309', 'argent': '#6b7280', 'or': '#ca8a04'}
        couleur = couleurs.get(obj.niveau_fidelite, '#6b7280')
        return format_html(
            '<span style="background:{}; color:#fff; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:600;">{}</span>',
            couleur, obj.get_niveau_fidelite_display()
        )

    @admin.display(description="Bonus parrainage")
    def bonus_statut(self, obj):
        from django.utils.html import format_html
        if not obj.parraine_par_id:
            return format_html('<span style="color:{};">-</span>', '#9ca3af')
        if obj.bonus_parrainage_attribue:
            return format_html('<span style="color:{}; font-weight:600;">&#10003; Verse</span>', '#059669')
        return format_html('<span style="color:{}; font-weight:600;">En attente</span>', '#d97706')

    @admin.display(description="Filleuls")
    def nb_filleuls(self, obj):
        return obj.filleuls.count()


@admin.register(Reservation)
class ReservationAdmin(FiltreAgenceMixin, admin.ModelAdmin):
    champs_agence = ['agence']
    list_display = ('numero_reservation', 'client', 'voyage', 'nombre_places', 'montant_total', 'statut', 'origine', 'mode_paiement', 'modifie_par', 'date_reservation')
    list_filter = ('statut', 'mode_paiement', 'voyage__date_depart', 'agence')
    search_fields = ('numero_reservation', 'client__nom', 'client__telephone')
    ordering = ('-date_reservation',)
    date_hierarchy = 'date_reservation'

    @admin.display(description="Origine")
    def origine(self, obj):
        from django.utils.html import format_html
        from django.utils.safestring import mark_safe
        if obj.cree_par_id:
            return format_html(
                '<span style="color:#1F3864;">&#128100; {}</span>',
                obj.cree_par.nom
            )
        return mark_safe('<span style="color:#059669; font-weight:600;">&#128241; App mobile</span>')

    def get_readonly_fields(self, request, obj=None):
        employe = getattr(request.user, 'employe', None)
        poste = employe.poste if employe else None
        if request.user.is_superuser or poste in ('pdg', 'responsable'):
            return ('cree_par', 'modifie_par', 'numero_reservation', 'date_reservation')
        return ('cree_par', 'modifie_par', 'numero_reservation', 'date_reservation', 'montant_total')

    def save_model(self, request, obj, form, change):
        employe = getattr(request.user, 'employe', None)
        if employe:
            obj.modifie_par = employe
            if not change:
                obj.cree_par = employe
        super().save_model(request, obj, form, change)


@admin.register(Colis)
class ColisAdmin(FiltreAgenceMixin, admin.ModelAdmin):
    champs_agence = ['agence_depart', 'agence_arrivee']
    list_display = ('code_suivi', 'expediteur_nom', 'destinataire_nom', 'agence_depart', 'agence_arrivee', 'poids_kg', 'prix', 'statut', 'cree_par', 'modifie_par', 'date_enregistrement')
    list_filter = ('statut', 'agence_depart', 'agence_arrivee', 'compagnie')
    search_fields = ('code_suivi', 'expediteur_nom', 'expediteur_telephone', 'destinataire_nom', 'destinataire_telephone')
    ordering = ('-date_enregistrement',)
    date_hierarchy = 'date_enregistrement'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'agence_depart':
            from .admin_filtres import voit_tout, agence_de
            if not voit_tout(request.user):
                agence = agence_de(request.user)
                if agence:
                    kwargs['queryset'] = Agence.objects.filter(id=agence.id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        employe = getattr(request.user, 'employe', None)
        poste = employe.poste if employe else None
        base = ('cree_par', 'modifie_par', 'code_suivi', 'date_enregistrement')
        if request.user.is_superuser or poste in ('pdg', 'responsable'):
            return base
        if obj is not None:
            return base + ('prix',)
        return base

    def save_model(self, request, obj, form, change):
        employe = getattr(request.user, 'employe', None)
        if employe:
            obj.modifie_par = employe
            if not change:
                obj.cree_par = employe
        super().save_model(request, obj, form, change)


class EmployeAdminForm(forms.ModelForm):
    nom_utilisateur = forms.CharField(
        label="Nom d'utilisateur (connexion)", max_length=150, required=False,
        help_text="Laisser vide pour utiliser le telephone comme identifiant. "
                   "En modification, laisser vide pour ne pas toucher au compte existant."
    )
    mot_de_passe = forms.CharField(
        label="Mot de passe", required=False, widget=forms.PasswordInput(render_value=False),
        help_text="Laisser vide : a la creation, un mot de passe temporaire sera genere et affiche."
    )

    class Meta:
        model = Employe
        exclude = ('user',)

    def clean(self):
        cleaned = super().clean()

        # Un seul PDG autorise dans tout le logiciel
        poste = cleaned.get('poste')
        if poste == 'pdg':
            deja_pdg = Employe.objects.filter(poste='pdg').exclude(pk=self.instance.pk).exists()
            if deja_pdg:
                self.add_error('poste', "Un seul compte PDG est autorise dans le logiciel. Un PDG existe deja.")

        nom_utilisateur = cleaned.get('nom_utilisateur')

        if self.instance.pk:
            # Modification : si un nouveau nom d'utilisateur est fourni, verifier qu'il est libre
            if nom_utilisateur:
                deja_pris = User.objects.filter(username=nom_utilisateur).exclude(
                    pk=self.instance.user_id
                ).exists()
                if deja_pris:
                    self.add_error('nom_utilisateur', "Ce nom d'utilisateur est deja pris par un autre compte.")
            return cleaned  # le reste de la gestion du compte se fait dans save_model

        telephone = cleaned.get('telephone')
        identifiant = nom_utilisateur or telephone
        if not identifiant:
            raise forms.ValidationError("Renseignez un telephone ou un nom d'utilisateur pour creer le compte.")
        if User.objects.filter(username=identifiant).exists():
            self.add_error(
                'nom_utilisateur' if nom_utilisateur else 'telephone',
                "Cet identifiant (nom d'utilisateur ou telephone) est deja pris. "
                "Renseignez un nom d'utilisateur different."
            )
        return cleaned


@admin.register(Employe)
class EmployeAdmin(FiltreAgenceMixin, admin.ModelAdmin):
    form = EmployeAdminForm
    champs_agence = ['agence']
    champ_createur = None  # pas de notion de "createur" pour un employe
    list_display = ('agence', 'poste_badge', 'nom', 'prenom', 'telephone', 'compte_lie', 'actif')
    list_filter = (FiltreAgenceListFilter, 'poste', 'actif', 'compagnie')
    search_fields = ('nom', 'prenom', 'telephone', 'cni')
    list_editable = ('actif',)
    ordering = ('agence__ville', 'agence__nom', 'poste', 'nom')

    def has_add_permission(self, request):
        from .admin_filtres import est_recruteur
        return est_recruteur(request.user)

    def has_change_permission(self, request, obj=None):
        from .admin_filtres import est_recruteur
        return est_recruteur(request.user)

    def has_delete_permission(self, request, obj=None):
        from .admin_filtres import voit_tout
        return voit_tout(request.user)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is not None and obj.user_id:
            form.base_fields['nom_utilisateur'].initial = obj.user.username
        return form

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'agence':
            from .admin_filtres import voit_tout, agence_de, zone_de
            if not voit_tout(request.user):
                employe = getattr(request.user, 'employe', None)
                poste = employe.poste if employe else None
                if poste == 'resp_planning':
                    zone = zone_de(request.user)
                    if zone:
                        kwargs['queryset'] = Agence.objects.filter(zone=zone)
                else:
                    agence = agence_de(request.user)
                    if agence:
                        kwargs['queryset'] = Agence.objects.filter(id=agence.id)
                        kwargs['initial'] = agence.id
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == 'poste':
            from .admin_filtres import voit_tout, POSTES_RECRUTEURS, POSTES_RECRUTABLES_PAR_AGENCE
            employe = getattr(request.user, 'employe', None)
            poste = employe.poste if employe else None
            if not voit_tout(request.user) and poste in POSTES_RECRUTEURS:
                kwargs['choices'] = [c for c in db_field.choices if c[0] in POSTES_RECRUTABLES_PAR_AGENCE]
        return super().formfield_for_choice_field(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        from .admin_filtres import assigner_groupe_selon_poste

        nom_utilisateur = form.cleaned_data.get('nom_utilisateur')
        mot_de_passe = form.cleaned_data.get('mot_de_passe')

        if not change:
            username = nom_utilisateur or obj.telephone
            mdp_genere = mot_de_passe or _generer_mot_de_passe()
            user = User.objects.create_user(
                username=username, password=mdp_genere,
                first_name=obj.prenom, last_name=obj.nom, is_staff=True,
            )
            assigner_groupe_selon_poste(user, obj.poste)
            obj.user = user
            super().save_model(request, obj, form, change)
            if not mot_de_passe:
                self.message_user(
                    request,
                    f"Compte cree : identifiant \"{username}\" / mot de passe temporaire \"{mdp_genere}\". "
                    f"Communiquez-le a l'employe puis demandez-lui de le changer.",
                    level='warning',
                )
        else:
            if obj.user:
                if nom_utilisateur and nom_utilisateur != obj.user.username:
                    obj.user.username = nom_utilisateur
                if mot_de_passe:
                    obj.user.set_password(mot_de_passe)
                obj.user.first_name = obj.prenom
                obj.user.last_name = obj.nom
                obj.user.is_staff = True
                obj.user.save()
                assigner_groupe_selon_poste(obj.user, obj.poste)
            elif nom_utilisateur:
                mdp_genere = mot_de_passe or _generer_mot_de_passe()
                user = User.objects.create_user(
                    username=nom_utilisateur, password=mdp_genere,
                    first_name=obj.prenom, last_name=obj.nom, is_staff=True,
                )
                assigner_groupe_selon_poste(user, obj.poste)
                obj.user = user
                if not mot_de_passe:
                    self.message_user(
                        request,
                        f"Compte cree : identifiant \"{nom_utilisateur}\" / mot de passe temporaire \"{mdp_genere}\".",
                        level='warning',
                    )
            super().save_model(request, obj, form, change)

    @admin.display(description="Poste", ordering='poste')
    def poste_badge(self, obj):
        from django.utils.html import format_html
        couleurs = {
            'pdg': '#1F3864',
            'responsable': '#7c3aed',
            'secretaire': '#db2777',
            'guichetier': '#059669',
            'caissier': '#0891b2',
            'agent_colis': '#b45309',
            'agent_transfert': '#b45309',
        }
        couleur = couleurs.get(obj.poste, '#6b7280')
        return format_html(
            '<span style="background:{}; color:#fff; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:600;">{}</span>',
            couleur, obj.get_poste_display()
        )

    @admin.display(description="Compte lié")
    def compte_lie(self, obj):
        return obj.user.username if obj.user else "—"


@admin.register(TransfertArgent)
class TransfertArgentAdmin(FiltreAgenceMixin, admin.ModelAdmin):
    champs_agence = ['agence_depart', 'agence_retrait']
    list_display = ('code_transfert', 'expediteur_nom', 'beneficiaire_nom', 'montant', 'frais', 'agence_depart', 'agence_retrait', 'statut', 'cree_par', 'modifie_par', 'date_envoi')
    list_filter = ('statut', 'agence_depart', 'agence_retrait', 'compagnie')
    search_fields = ('code_transfert', 'expediteur_nom', 'expediteur_telephone', 'beneficiaire_nom', 'beneficiaire_telephone', 'code_retrait')
    ordering = ('-date_envoi',)
    date_hierarchy = 'date_envoi'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'agence_depart':
            from .admin_filtres import voit_tout, agence_de
            if not voit_tout(request.user):
                agence = agence_de(request.user)
                if agence:
                    kwargs['queryset'] = Agence.objects.filter(id=agence.id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        employe = getattr(request.user, 'employe', None)
        poste = employe.poste if employe else None
        base = ('cree_par', 'modifie_par', 'code_transfert', 'code_retrait', 'date_envoi')
        if request.user.is_superuser or poste in ('pdg', 'responsable'):
            return base
        if obj is not None:
            return base + ('montant', 'frais')
        return base

    def save_model(self, request, obj, form, change):
        employe = getattr(request.user, 'employe', None)
        if employe:
            obj.modifie_par = employe
            if not change:
                obj.cree_par = employe
        super().save_model(request, obj, form, change)


@admin.register(Entretien)
class EntretienAdmin(FiltreAgenceMixin, admin.ModelAdmin):
    champs_agence = ['bus__agence']
    list_display = ('bus', 'type_entretien', 'date_entretien', 'kilometrage', 'cout', 'cree_par')
    list_filter = ('type_entretien', 'date_entretien', 'bus')
    search_fields = ('bus__immatriculation', 'description')
    ordering = ('-date_entretien',)
    autocomplete_fields = ('bus', 'cree_par')


@admin.register(PleinCarburant)
class PleinCarburantAdmin(FiltreAgenceMixin, admin.ModelAdmin):
    champs_agence = ['bus__agence']
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

    def has_add_permission(self, request):
        return _config_modifiable_uniquement_par_pdg(request)

    def has_change_permission(self, request, obj=None):
        return _config_modifiable_uniquement_par_pdg(request)

    def has_delete_permission(self, request, obj=None):
        return _config_modifiable_uniquement_par_pdg(request)


@admin.register(DemandeColis)
class DemandeColisAdmin(FiltreAgenceMixin, admin.ModelAdmin):
    champs_agence = ['agence_depart', 'agence_arrivee']
    champ_createur = None  # demandes soumises par les clients, pas par un employe
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
class DemandeTransfertAdmin(FiltreAgenceMixin, admin.ModelAdmin):
    champs_agence = ['agence_depart', 'agence_retrait']
    champ_createur = None
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


            
from django.contrib.admin import AdminSite
from .admin_stats import statistiques_tableau_bord
from .admin_filtres import profil_tableau_bord

_ancien_index = AdminSite.index


def _index_avec_stats(self, request, extra_context=None):
    extra_context = extra_context or {}
    extra_context['stats'] = statistiques_tableau_bord(request.user)
    extra_context['stats_profil'] = profil_tableau_bord(request.user)
    return _ancien_index(self, request, extra_context)

AdminSite.index = _index_avec_stats


class ArretLigneInline(admin.TabularInline):
    model = ArretLigne
    extra = 3
    fields = ('ordre', 'agence', 'prix_depuis_depart')
    ordering = ('ordre',)


@admin.register(Ligne)
class LigneAdmin(FiltreAgenceMixin, admin.ModelAdmin):
    champs_agence = ['arrets__agence']
    champ_createur = None
    list_display = ('nom', 'compagnie', 'apercu_villes', 'actif')
    list_filter = ('compagnie', 'actif')
    search_fields = ('nom',)
    list_editable = ('actif',)
    inlines = [ArretLigneInline]

    @admin.display(description="Villes desservies")
    def apercu_villes(self, obj):
        villes = obj.villes()
        return " -> ".join(villes) if villes else "(aucun arret)"


@admin.register(AlerteVoyage)
class AlerteVoyageAdmin(FiltreAgenceMixin, admin.ModelAdmin):
    champs_agence = ['voyage__bus__agence']
    champ_createur = None
    list_display = ('type_alerte', 'voyage', 'message_court', 'date_creation', 'resolue')
    list_filter = ('type_alerte', 'resolue', 'date_creation')
    search_fields = ('voyage__bus__immatriculation', 'message')
    list_editable = ('resolue',)
    ordering = ('-date_creation',)

    @admin.display(description="Message")
    def message_court(self, obj):
        return obj.message[:60] + ('...' if len(obj.message) > 60 else '')

    def has_add_permission(self, request):
        return False


@admin.register(AvisVoyage)
class AvisVoyageAdmin(FiltreAgenceMixin, admin.ModelAdmin):
    champs_agence = ['voyage__bus__agence']
    champ_createur = None  # avis soumis par les clients, pas par un employe
    list_display = ('note_etoiles', 'chauffeur', 'client', 'voyage', 'critere_bus', 'critere_clim', 'critere_tv', 'critere_connexion', 'critere_chauffeur', 'critere_accompagnateur', 'commentaire_court', 'date_creation')
    list_filter = ('note', 'chauffeur', 'date_creation')
    search_fields = ('client__nom', 'client__telephone', 'chauffeur__nom', 'chauffeur__prenom', 'commentaire')
    ordering = ('-date_creation',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="Note", ordering='note')
    def note_etoiles(self, obj):
        from django.utils.html import format_html
        return format_html('<span style="color:{}; font-size:14px; font-weight:600;">{} {}/5</span>', '#ca8a04', '\u2605' * obj.note + '\u2606' * (5 - obj.note), obj.note)

    def _oui_non(self, valeur):
        from django.utils.html import format_html
        if valeur is True:
            return format_html('<span style="color:{}; font-weight:600;">&#10003;</span>', '#059669')
        if valeur is False:
            return format_html('<span style="color:{}; font-weight:600;">&#10007;</span>', '#dc2626')
        return format_html('<span style="color:{};">-</span>', '#9ca3af')

    @admin.display(description="Bus propre")
    def critere_bus(self, obj):
        return self._oui_non(obj.bus_propre)

    @admin.display(description="Clim")
    def critere_clim(self, obj):
        return self._oui_non(obj.climatisation_ok)

    @admin.display(description="TV")
    def critere_tv(self, obj):
        return self._oui_non(obj.television_ok)

    @admin.display(description="Connexion")
    def critere_connexion(self, obj):
        return self._oui_non(obj.connexion_ok)

    @admin.display(description="Chauffeur poli")
    def critere_chauffeur(self, obj):
        return self._oui_non(obj.chauffeur_poli)

    @admin.display(description="Accompagnateur")
    def critere_accompagnateur(self, obj):
        return self._oui_non(obj.accompagnateur_aimable)

    @admin.display(description="Commentaire")
    def commentaire_court(self, obj):
        if not obj.commentaire:
            return "-"
        return obj.commentaire[:50] + ('...' if len(obj.commentaire) > 50 else '')


@admin.register(QuestionFAQ)
class QuestionFAQAdmin(admin.ModelAdmin):
    list_display = ('ordre', 'question', 'actif', 'date_creation')
    list_filter = ('actif',)
    search_fields = ('question', 'reponse')
    list_editable = ('actif',)
    ordering = ('ordre', 'id')

    def has_add_permission(self, request):
        return _config_modifiable_uniquement_par_pdg(request)

    def has_change_permission(self, request, obj=None):
        return _config_modifiable_uniquement_par_pdg(request)

    def has_delete_permission(self, request, obj=None):
        return _config_modifiable_uniquement_par_pdg(request)