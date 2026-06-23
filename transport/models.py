from django.db import models


class Compagnie(models.Model):
    nom = models.CharField(max_length=100)
    sigle = models.CharField(max_length=20, blank=True)
    siege_social = models.CharField(max_length=200)
    telephone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    date_creation = models.DateField(null=True, blank=True)
    actif = models.BooleanField(default=True)

    def __str__(self):
        return self.nom


class Agence(models.Model):
    compagnie = models.ForeignKey(Compagnie, on_delete=models.CASCADE, related_name='agences')
    nom = models.CharField(max_length=100)
    ville = models.CharField(max_length=50)
    adresse = models.CharField(max_length=200)
    telephone = models.CharField(max_length=20)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    responsable = models.CharField(max_length=100, blank=True)
    actif = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nom} ({self.ville})"


class Bus(models.Model):
    STATUT_CHOICES = [
        ('en_service', 'En service'),
        ('maintenance', 'En maintenance'),
        ('hors_service', 'Hors service'),
    ]

    compagnie = models.ForeignKey(Compagnie, on_delete=models.CASCADE, related_name='bus')
    immatriculation = models.CharField(max_length=20, unique=True)
    marque = models.CharField(max_length=50)
    modele = models.CharField(max_length=50, blank=True)
    capacite = models.IntegerField()
    kilometrage = models.IntegerField(default=0)
    annee = models.IntegerField(null=True, blank=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_service')
    date_visite_technique = models.DateField(null=True, blank=True)
    date_assurance = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.immatriculation} - {self.marque}"

    class Meta:
        verbose_name_plural = "Bus"


class Chauffeur(models.Model):
    STATUT_CHOICES = [
        ('disponible', 'Disponible'),
        ('en_mission', 'En mission'),
        ('repos', 'En repos'),
        ('inactif', 'Inactif'),
    ]

    compagnie = models.ForeignKey(Compagnie, on_delete=models.CASCADE, related_name='chauffeurs')
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20)
    numero_permis = models.CharField(max_length=50, unique=True)
    date_expiration_permis = models.DateField(null=True, blank=True)
    date_embauche = models.DateField(null=True, blank=True)
    annees_experience = models.IntegerField(default=0)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='disponible')
    photo = models.ImageField(upload_to='chauffeurs/', null=True, blank=True)
    actif = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.prenom} {self.nom}"

    class Meta:
        ordering = ['nom', 'prenom']


class Trajet(models.Model):
    compagnie = models.ForeignKey(Compagnie, on_delete=models.CASCADE, related_name='trajets')
    ville_depart = models.CharField(max_length=50)
    ville_arrivee = models.CharField(max_length=50)
    distance_km = models.IntegerField(help_text="Distance en kilomètres")
    duree_estimee_heures = models.FloatField(help_text="Durée estimée en heures")
    prix_base = models.IntegerField(help_text="Prix du billet en FCFA")
    actif = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.ville_depart} → {self.ville_arrivee}"

    class Meta:
        ordering = ['ville_depart', 'ville_arrivee']
        unique_together = ['compagnie', 'ville_depart', 'ville_arrivee']


class Voyage(models.Model):
    STATUT_CHOICES = [
        ('programme', 'Programmé'),
        ('en_cours', 'En cours'),
        ('termine', 'Terminé'),
        ('annule', 'Annulé'),
    ]

    trajet = models.ForeignKey(Trajet, on_delete=models.PROTECT, related_name='voyages')
    bus = models.ForeignKey(Bus, on_delete=models.PROTECT, related_name='voyages')
    chauffeur = models.ForeignKey(Chauffeur, on_delete=models.PROTECT, related_name='voyages')
    date_depart = models.DateField()
    heure_depart = models.TimeField()
    heure_arrivee_prevue = models.TimeField(null=True, blank=True)
    prix = models.IntegerField(help_text="Prix du billet en FCFA")
    places_disponibles = models.IntegerField()
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='programme')
    notes = models.TextField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.trajet} - {self.date_depart} à {self.heure_depart}"

    class Meta:
        ordering = ['-date_depart', '-heure_depart']


class Client(models.Model):
    TYPE_CHOICES = [
        ('particulier', 'Particulier'),
        ('entreprise', 'Entreprise'),
    ]

    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100, blank=True)
    telephone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True)
    type_client = models.CharField(max_length=20, choices=TYPE_CHOICES, default='particulier')
    cni = models.CharField(max_length=50, blank=True, help_text="Numéro de carte d'identité")
    ville_residence = models.CharField(max_length=50, blank=True)
    date_inscription = models.DateTimeField(auto_now_add=True)
    nombre_voyages = models.IntegerField(default=0, help_text="Nombre total de voyages effectués")
    actif = models.BooleanField(default=True)

    def __str__(self):
        if self.prenom:
            return f"{self.prenom} {self.nom} ({self.telephone})"
        return f"{self.nom} ({self.telephone})"

    class Meta:
        ordering = ['nom', 'prenom']


class Reservation(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente de paiement'),
        ('payee', 'Payée'),
        ('annulee', 'Annulée'),
        ('remboursee', 'Remboursée'),
    ]

    MODE_PAIEMENT_CHOICES = [
        ('especes', 'Espèces'),
        ('mobile_money', 'Mobile Money'),
        ('virement', 'Virement bancaire'),
        ('carte', 'Carte bancaire'),
    ]

    numero_reservation = models.CharField(max_length=20, unique=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='reservations')
    voyage = models.ForeignKey(Voyage, on_delete=models.PROTECT, related_name='reservations')
    agence = models.ForeignKey(Agence, on_delete=models.PROTECT, related_name='reservations', null=True, blank=True, help_text="Agence où la réservation a été faite")
    cree_par = models.ForeignKey('Employe', on_delete=models.SET_NULL, null=True, blank=True, related_name='reservations_creees', verbose_name="Créé par")
    nombre_places = models.IntegerField(default=1)
    montant_total = models.IntegerField(default=0, blank=True, help_text="Calculé automatiquement")
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    mode_paiement = models.CharField(max_length=20, choices=MODE_PAIEMENT_CHOICES, blank=True)
    date_reservation = models.DateTimeField(auto_now_add=True)
    date_paiement = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Réservation {self.numero_reservation} - {self.client.nom}"

    def save(self, *args, **kwargs):
        # Si c'est une nouvelle réservation (pas encore en base)
        if not self.pk:
            # 1. Vérifier qu'il y a assez de places disponibles
            if self.nombre_places > self.voyage.places_disponibles:
                raise ValueError(
                    f"Pas assez de places ! Demandé : {self.nombre_places}, "
                    f"Disponible : {self.voyage.places_disponibles}"
                )

            # 2. Générer le numéro de réservation automatiquement
            if not self.numero_reservation:
                from datetime import datetime
                annee = datetime.now().year
                dernier_numero = Reservation.objects.filter(
                    numero_reservation__startswith=f"RES-{annee}-"
                ).count()
                nouveau_numero = dernier_numero + 1
                self.numero_reservation = f"RES-{annee}-{nouveau_numero:04d}"

            # 3. Calculer automatiquement le montant total
            self.montant_total = self.voyage.prix * self.nombre_places

            # 4. Décrémenter les places disponibles du voyage
            self.voyage.places_disponibles -= self.nombre_places
            self.voyage.save()

        # Sauvegarder normalement
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-date_reservation']


class Colis(models.Model):
    STATUT_CHOICES = [
        ('enregistre', 'Enregistré'),
        ('en_transit', 'En transit'),
        ('arrive', 'Arrivé à destination'),
        ('livre', 'Livré'),
        ('retourne', 'Retourné'),
    ]

    code_suivi = models.CharField(max_length=20, unique=True, blank=True)
    compagnie = models.ForeignKey(Compagnie, on_delete=models.PROTECT, related_name='colis')

    expediteur_nom = models.CharField(max_length=100)
    expediteur_telephone = models.CharField(max_length=20)
    destinataire_nom = models.CharField(max_length=100)
    destinataire_telephone = models.CharField(max_length=20)

    agence_depart = models.ForeignKey(Agence, on_delete=models.PROTECT, related_name='colis_envoyes')
    agence_arrivee = models.ForeignKey(Agence, on_delete=models.PROTECT, related_name='colis_recus')
    cree_par = models.ForeignKey('Employe', on_delete=models.SET_NULL, null=True, blank=True, related_name='colis_crees', verbose_name="Créé par")

    description = models.CharField(max_length=200, help_text="Contenu du colis")
    poids_kg = models.FloatField(help_text="Poids en kilogrammes")
    prix = models.IntegerField(help_text="Prix en FCFA")

    voyage = models.ForeignKey(Voyage, on_delete=models.SET_NULL, related_name='colis', null=True, blank=True, help_text="Voyage sur lequel le colis est transporté")

    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='enregistre')
    date_enregistrement = models.DateTimeField(auto_now_add=True)
    date_livraison = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.code_suivi} - {self.expediteur_nom} → {self.destinataire_nom}"

    def save(self, *args, **kwargs):
        if not self.code_suivi:
            from datetime import datetime
            annee = datetime.now().year
            dernier_numero = Colis.objects.filter(
                code_suivi__startswith=f"COL-{annee}-"
            ).count()
            nouveau_numero = dernier_numero + 1
            self.code_suivi = f"COL-{annee}-{nouveau_numero:04d}"
        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = "Colis"
        ordering = ['-date_enregistrement']



# ============================================================
# À AJOUTER À LA FIN DE transport/models.py
# ============================================================


class Employe(models.Model):
    POSTE_CHOICES = [
        ('pdg', 'PDG / Directeur général'),
        ('responsable', "Responsable d'agence"),
        ('guichetier', 'Guichetier / billettiste'),
        ('caissier', 'Caissier'),
        ('agent_colis', 'Agent colis'),
        ('agent_transfert', "Agent transfert d'argent"),
        ('manutentionnaire', 'Manutentionnaire / bagagiste'),
        ('comptable', 'Comptable'),
        ('rh', 'Responsable RH / recrutement'),
        ('resp_maintenance', 'Responsable maintenance'),
        ('securite', 'Agent de sécurité'),
        ('autre', 'Autre'),
    ]

    user = models.OneToOneField('auth.User', on_delete=models.SET_NULL, related_name='employe', null=True, blank=True, help_text="Compte de connexion lié à cet employé")
    compagnie = models.ForeignKey(Compagnie, on_delete=models.CASCADE, related_name='employes')
    agence = models.ForeignKey(Agence, on_delete=models.SET_NULL, related_name='employes', null=True, blank=True, help_text="Laisser vide pour un PDG (toute la compagnie)")
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20)
    poste = models.CharField(max_length=20, choices=POSTE_CHOICES, default='guichetier')
    cni = models.CharField(max_length=50, blank=True, help_text="Numéro de carte d'identité")
    date_embauche = models.DateField(null=True, blank=True)
    salaire = models.IntegerField(null=True, blank=True, help_text="Salaire mensuel en FCFA")
    actif = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.get_poste_display()})"

    class Meta:
        verbose_name_plural = "Employés"
        ordering = ['nom', 'prenom']


class TransfertArgent(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente de retrait'),
        ('retire', 'Retiré'),
        ('annule', 'Annulé'),
        ('rembourse', 'Remboursé'),
    ]

    code_transfert = models.CharField(max_length=20, unique=True, blank=True)
    compagnie = models.ForeignKey(Compagnie, on_delete=models.PROTECT, related_name='transferts')

    expediteur_nom = models.CharField(max_length=100)
    expediteur_telephone = models.CharField(max_length=20)
    beneficiaire_nom = models.CharField(max_length=100)
    beneficiaire_telephone = models.CharField(max_length=20)

    agence_depart = models.ForeignKey(Agence, on_delete=models.PROTECT, related_name='transferts_envoyes')
    agence_retrait = models.ForeignKey(Agence, on_delete=models.PROTECT, related_name='transferts_recus')
    cree_par = models.ForeignKey('Employe', on_delete=models.SET_NULL, null=True, blank=True, related_name='transferts_crees', verbose_name="Créé par")

    montant = models.IntegerField(help_text="Montant envoyé en FCFA")
    frais = models.IntegerField(default=0, help_text="Frais de transfert en FCFA")
    code_retrait = models.CharField(max_length=10, blank=True, help_text="Code secret remis au bénéficiaire")

    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    date_envoi = models.DateTimeField(auto_now_add=True)
    date_retrait = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.code_transfert} - {self.expediteur_nom} → {self.beneficiaire_nom}"

    def save(self, *args, **kwargs):
        if not self.code_transfert:
            from datetime import datetime
            annee = datetime.now().year
            dernier_numero = TransfertArgent.objects.filter(
                code_transfert__startswith=f"TRF-{annee}-"
            ).count()
            nouveau_numero = dernier_numero + 1
            self.code_transfert = f"TRF-{annee}-{nouveau_numero:04d}"

        if not self.code_retrait:
            import random
            self.code_retrait = str(random.randint(10000, 99999))

        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = "Transferts d'argent"
        ordering = ['-date_envoi']

class Entretien(models.Model):
    """Une opération d'entretien/maintenance sur un bus."""

    TYPE_CHOICES = [
        ('vidange', 'Vidange moteur'),
        ('freins', 'Freins'),
        ('pneus', 'Pneus'),
        ('revision', 'Révision générale'),
        ('boite_vitesse', 'Vidange boîte de vitesse'),
        ('courroie', 'Courroie'),
        ('batterie', 'Batterie'),
        ('climatisation', 'Climatisation'),
        ('carrosserie', 'Carrosserie'),
        ('autre', 'Autre'),
    ]

    bus = models.ForeignKey('Bus', on_delete=models.CASCADE, related_name='entretiens', verbose_name="Bus")
    type_entretien = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="Type d'entretien")
    date_entretien = models.DateField(verbose_name="Date de l'entretien")
    kilometrage = models.PositiveIntegerField(default=0, verbose_name="Kilométrage du bus")
    cout = models.PositiveIntegerField(default=0, verbose_name="Coût (FCFA)")
    description = models.TextField(blank=True, verbose_name="Détails / pièces changées")
    prochain_km = models.PositiveIntegerField(null=True, blank=True, verbose_name="Prochaine échéance (km)")
    cree_par = models.ForeignKey('Employe', on_delete=models.SET_NULL, null=True, blank=True, related_name='entretiens_crees', verbose_name="Enregistré par")
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Entretien"
        verbose_name_plural = "Entretiens"
        ordering = ['-date_entretien']

    def __str__(self):
        return f"{self.get_type_entretien_display()} — {self.bus} ({self.date_entretien})"


class PleinCarburant(models.Model):
    """Un plein de carburant, lié à un bus et à un voyage."""

    bus = models.ForeignKey('Bus', on_delete=models.CASCADE, related_name='pleins', verbose_name="Bus")
    voyage = models.ForeignKey('Voyage', on_delete=models.SET_NULL, null=True, blank=True, related_name='pleins', verbose_name="Voyage")
    date_plein = models.DateField(verbose_name="Date du plein")
    litres = models.DecimalField(max_digits=7, decimal_places=2, default=0, verbose_name="Litres")
    montant = models.PositiveIntegerField(default=0, verbose_name="Montant (FCFA)")
    kilometrage = models.PositiveIntegerField(null=True, blank=True, verbose_name="Kilométrage")
    cree_par = models.ForeignKey('Employe', on_delete=models.SET_NULL, null=True, blank=True, related_name='pleins_crees', verbose_name="Enregistré par")
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Plein de carburant"
        verbose_name_plural = "Pleins de carburant"
        ordering = ['-date_plein']

    def __str__(self):
        return f"Plein {self.bus} — {self.montant} FCFA ({self.date_plein})"