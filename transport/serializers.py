from rest_framework import serializers
from .models import Colis, TransfertArgent, Voyage, Reservation, Siege, Promotion, DemandeColis, Agence, DemandeTransfert


class ColisSerializer(serializers.ModelSerializer):
    statut_libelle = serializers.CharField(source='get_statut_display', read_only=True)
    agence_depart_nom = serializers.CharField(source='agence_depart.__str__', read_only=True)
    agence_arrivee_nom = serializers.CharField(source='agence_arrivee.__str__', read_only=True)

    class Meta:
        model = Colis
        fields = [
            'code_suivi', 'statut', 'statut_libelle',
            'expediteur_nom', 'destinataire_nom',
            'agence_depart_nom', 'agence_arrivee_nom',
            'poids_kg', 'prix', 'date_enregistrement',
        ]


class TransfertArgentSerializer(serializers.ModelSerializer):
    statut_libelle = serializers.CharField(source='get_statut_display', read_only=True)
    agence_depart_nom = serializers.CharField(source='agence_depart.__str__', read_only=True)
    agence_retrait_nom = serializers.CharField(source='agence_retrait.__str__', read_only=True)

    class Meta:
        model = TransfertArgent
        fields = [
            'code_transfert', 'statut', 'statut_libelle',
            'expediteur_nom', 'beneficiaire_nom',
            'agence_depart_nom', 'agence_retrait_nom',
            'montant', 'date_envoi',
        ]


class VoyageSerializer(serializers.ModelSerializer):
    ville_depart = serializers.CharField(source='trajet.ville_depart', read_only=True)
    ville_arrivee = serializers.CharField(source='trajet.ville_arrivee', read_only=True)
    bus_immatriculation = serializers.CharField(source='bus.immatriculation', read_only=True)

    class Meta:
        model = Voyage
        fields = [
            'id', 'ville_depart', 'ville_arrivee',
            'date_depart', 'heure_depart', 'prix',
            'places_disponibles', 'bus_immatriculation', 'statut',
        ]


class ReservationSerializer(serializers.ModelSerializer):
    statut_libelle = serializers.CharField(source='get_statut_display', read_only=True)
    ville_depart = serializers.CharField(source='voyage.trajet.ville_depart', read_only=True)
    ville_arrivee = serializers.CharField(source='voyage.trajet.ville_arrivee', read_only=True)
    date_depart = serializers.DateField(source='voyage.date_depart', read_only=True)
    heure_depart = serializers.TimeField(source='voyage.heure_depart', read_only=True)
    numeros_sieges = serializers.SerializerMethodField()
    voyageur = serializers.SerializerMethodField()

    def get_numeros_sieges(self, obj):
        return list(obj.sieges.order_by('numero').values_list('numero', flat=True))

    def get_voyageur(self, obj):
        nom_complet = (obj.voyageur_prenom + ' ' + obj.voyageur_nom).strip()
        return nom_complet if nom_complet else ''

    class Meta:
        model = Reservation
        fields = [
            'numero_reservation', 'ville_depart', 'ville_arrivee',
            'date_depart', 'heure_depart', 'nombre_places',
            'montant_total', 'statut', 'statut_libelle', 'date_reservation',
            'numeros_sieges', 'voyageur', 'voyageur_telephone',
        ]


class SiegeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Siege
        fields = ['numero', 'occupe']


class PromotionSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    class Meta:
        model = Promotion
        fields = ['id', 'titre', 'texte', 'image_url', 'date_debut', 'date_fin', 'service']


class AgenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agence
        fields = ['id', 'nom', 'ville']


class DemandeColisSerializer(serializers.ModelSerializer):
    statut_libelle = serializers.CharField(source='get_statut_display', read_only=True)
    agence_depart_nom = serializers.CharField(source='agence_depart.__str__', read_only=True)
    agence_arrivee_nom = serializers.CharField(source='agence_arrivee.__str__', read_only=True)
    code_suivi = serializers.SerializerMethodField()

    def get_code_suivi(self, obj):
        return obj.colis.code_suivi if obj.colis else None

    class Meta:
        model = DemandeColis
        fields = ['numero_demande', 'expediteur_nom', 'expediteur_telephone', 'destinataire_nom', 'destinataire_telephone', 'agence_depart_nom', 'agence_arrivee_nom', 'description', 'poids_estime', 'valeur_declaree', 'statut', 'statut_libelle', 'date_demande', 'code_suivi']


class DemandeTransfertSerializer(serializers.ModelSerializer):
    statut_libelle = serializers.CharField(source='get_statut_display', read_only=True)
    agence_depart_nom = serializers.CharField(source='agence_depart.__str__', read_only=True)
    agence_retrait_nom = serializers.CharField(source='agence_retrait.__str__', read_only=True)
    code_suivi = serializers.SerializerMethodField()

    def get_code_suivi(self, obj):
        return obj.transfert.code_transfert if obj.transfert else None

    class Meta:
        model = DemandeTransfert
        fields = ['numero_demande', 'expediteur_nom', 'expediteur_telephone', 'beneficiaire_nom', 'beneficiaire_telephone', 'agence_depart_nom', 'agence_retrait_nom', 'montant', 'frais', 'statut', 'statut_libelle', 'date_demande', 'code_suivi']