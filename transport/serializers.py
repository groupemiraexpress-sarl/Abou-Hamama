from rest_framework import serializers
from .models import Colis, TransfertArgent, Voyage, Reservation, Siege


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
