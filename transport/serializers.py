from rest_framework import serializers
from .models import Colis, TransfertArgent, Voyage


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