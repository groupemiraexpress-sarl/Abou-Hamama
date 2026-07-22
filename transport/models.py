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
    distance_km = models.IntegerField(help_text="Distance en kilometres")
    duree_estimee_heures = models.FloatField(help_text="Duree estimee en heures")
    prix_base = models.IntegerField(help_text="Prix du billet en FCFA")
    actif = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.ville_depart} -> {self.ville_arrivee}"

    class Meta:
        ordering = ['ville_depart', 'ville_arrivee']
        unique_together = ['compagnie', 'ville_depart', 'ville_arrivee']


class Voyage(models.Model):
    STATUT_CHOICES = [
        ('programme', 'Programme'),
        ('en_cours', 'En cours'),
        ('termine', 'Termine'),
        ('annule', 'Annule'),
    ]

    trajet = models.ForeignKey(Trajet, on_delete=models.PROTECT, related_name='voyages')
    ligne = models.ForeignKey('Ligne', on_delete=models.PROTECT, related_name='voyages', null=True, blank=True, help_text="Ligne desservie (si le voyage dessert plusieurs villes)")
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
        return f"{self.trajet} - {self.date_depart} a {self.heure_depart}"

    def save(self, *args, **kwargs):
        nouveau_voyage = self.pk is None
        super().save(*args, **kwargs)
        if nouveau_voyage:
            capacite = self.bus.capacite
            sieges = [Siege(voyage=self, numero=n) for n in range(1, capacite + 1)]
            Siege.objects.bulk_create(sieges)

    class Meta:
        ordering = ['-date_depart', '-heure_depart']


class Client(models.Model):
    TYPE_CHOICES = [
        ('particulier', 'Particulier'),
        ('entreprise', 'Entreprise'),
    ]

    TYPE_PIECE_CHOICES = [
        ('cni', 'Carte nationale d\'identite'),
        ('passeport', 'Passeport'),
        ('acte_naissance', 'Acte de naissance'),
        ('carte_pro', 'Carte professionnelle'),
        ('permis', 'Permis de conduire'),
        ('autre', 'Autre piece'),
    ]

    user = models.OneToOneField('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='client', help_text="Compte de connexion lie a cette fiche client (app mobile)")
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100, blank=True)
    telephone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True)
    type_client = models.CharField(max_length=20, choices=TYPE_CHOICES, default='particulier')
    type_piece = models.CharField(max_length=20, choices=TYPE_PIECE_CHOICES, blank=True, help_text="Type de piece d'identite")
    cni = models.CharField(max_length=50, blank=True, help_text="Numero de la piece d'identite")
    ville_residence = models.CharField(max_length=50, blank=True)
    date_inscription = models.DateTimeField(auto_now_add=True)
    nombre_voyages = models.IntegerField(default=0, help_text="Nombre total de voyages effectues")
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
        ('payee', 'Payee'),
        ('annulee', 'Annulee'),
        ('remboursee', 'Remboursee'),
    ]

    MODE_PAIEMENT_CHOICES = [
        ('especes', 'Especes'),
        ('mobile_money', 'Mobile Money'),
        ('virement', 'Virement bancaire'),
        ('carte', 'Carte bancaire'),
    ]

    numero_reservation = models.CharField(max_length=20, unique=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='reservations')
    voyage = models.ForeignKey(Voyage, on_delete=models.PROTECT, related_name='reservations')
    agence = models.ForeignKey(Agence, on_delete=models.PROTECT, related_name='reservations', null=True, blank=True, help_text="Agence ou la reservation a ete faite")
    cree_par = models.ForeignKey('Employe', on_delete=models.SET_NULL, null=True, blank=True, related_name='reservations_creees', verbose_name="Cree par")
    nombre_places = models.IntegerField(default=1)
    voyageur_nom = models.CharField(max_length=100, blank=True, help_text="Nom du voyageur de ce billet")
    voyageur_prenom = models.CharField(max_length=100, blank=True, help_text="Prenom du voyageur")
    voyageur_telephone = models.CharField(max_length=20, blank=True, help_text="Telephone du voyageur")
    voyageur_type_piece = models.CharField(max_length=20, blank=True, help_text="Type de piece du voyageur")
    voyageur_numero_piece = models.CharField(max_length=50, blank=True, help_text="Numero de piece du voyageur")
    siege = models.ForeignKey('Siege', on_delete=models.PROTECT, null=True, blank=True, related_name='reservations', help_text="Siege physique reserve")
    arret_montee = models.ForeignKey('ArretLigne', on_delete=models.SET_NULL, null=True, blank=True, related_name='reservations_montee', help_text="Arret ou le voyageur monte (si ligne multi-arrets)")
    arret_descente = models.ForeignKey('ArretLigne', on_delete=models.SET_NULL, null=True, blank=True, related_name='reservations_descente', help_text="Arret ou le voyageur descend (si ligne multi-arrets)")
    montant_total = models.IntegerField(default=0, blank=True, help_text="Calcule automatiquement")
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    mode_paiement = models.CharField(max_length=20, choices=MODE_PAIEMENT_CHOICES, blank=True)
    date_reservation = models.DateTimeField(auto_now_add=True)
    date_paiement = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Reservation {self.numero_reservation} - {self.client.nom}"

    def save(self, *args, **kwargs):
        if not self.pk:
            if not self.numero_reservation:
                from datetime import datetime
                annee = datetime.now().year
                dernier_numero = Reservation.objects.filter(
                    numero_reservation__startswith=f"RES-{annee}-"
                ).count()
                nouveau_numero = dernier_numero + 1
                self.numero_reservation = f"RES-{annee}-{nouveau_numero:04d}"

            if self.arret_montee and self.arret_descente:
                self.montant_total = self.arret_descente.prix_depuis_depart - self.arret_montee.prix_depuis_depart
            else:
                self.montant_total = self.voyage.prix * self.nombre_places

            if not self.voyage.ligne_id:
                if self.nombre_places > self.voyage.places_disponibles:
                    raise ValueError(
                        f"Pas assez de places ! Demande : {self.nombre_places}, "
                        f"Disponible : {self.voyage.places_disponibles}"
                    )
                self.voyage.places_disponibles -= self.nombre_places
                self.voyage.save()

        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-date_reservation']


class Colis(models.Model):
    STATUT_CHOICES = [
        ('enregistre', 'Enregistre'),
        ('en_transit', 'En transit'),
        ('arrive', 'Arrive a destination'),
        ('livre', 'Livre'),
        ('retourne', 'Retourne'),
    ]

    code_suivi = models.CharField(max_length=20, unique=True, blank=True)
    compagnie = models.ForeignKey(Compagnie, on_delete=models.PROTECT, related_name='colis')

    expediteur_nom = models.CharField(max_length=100)
    expediteur_telephone = models.CharField(max_length=20)
    destinataire_nom = models.CharField(max_length=100)
    destinataire_telephone = models.CharField(max_length=20)

    agence_depart = models.ForeignKey(Agence, on_delete=models.PROTECT, related_name='colis_envoyes')
    agence_arrivee = models.ForeignKey(Agence, on_delete=models.PROTECT, related_name='colis_recus')
    cree_par = models.ForeignKey('Employe', on_delete=models.SET_NULL, null=True, blank=True, related_name='colis_crees', verbose_name="Cree par")

    description = models.CharField(max_length=200, help_text="Contenu du colis")
    poids_kg = models.FloatField(help_text="Poids en kilogrammes")
    prix = models.IntegerField(help_text="Prix en FCFA")

    voyage = models.ForeignKey(Voyage, on_delete=models.SET_NULL, related_name='colis', null=True, blank=True, help_text="Voyage sur lequel le colis est transporte")

    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='enregistre')
    date_enregistrement = models.DateTimeField(auto_now_add=True)
    date_livraison = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.code_suivi} - {self.expediteur_nom} -> {self.destinataire_nom}"

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


class Employe(models.Model):
    POSTE_CHOICES = [
        ('pdg', 'PDG / Directeur general'),
        ('responsable', "Responsable d'agence"),
        ('guichetier', 'Guichetier / billettiste'),
        ('caissier', 'Caissier'),
        ('agent_colis', 'Agent colis'),
        ('agent_transfert', "Agent transfert d'argent"),
        ('manutentionnaire', 'Manutentionnaire / bagagiste'),
        ('comptable', 'Comptable'),
        ('rh', 'Responsable RH / recrutement'),
        ('resp_maintenance', 'Responsable maintenance'),
        ('securite', 'Agent de securite'),
        ('autre', 'Autre'),
    ]

    user = models.OneToOneField('auth.User', on_delete=models.SET_NULL, related_name='employe', null=True, blank=True, help_text="Compte de connexion lie a cet employe")
    compagnie = models.ForeignKey(Compagnie, on_delete=models.CASCADE, related_name='employes')
    agence = models.ForeignKey(Agence, on_delete=models.SET_NULL, related_name='employes', null=True, blank=True, help_text="Laisser vide pour un PDG (toute la compagnie)")
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20)
    poste = models.CharField(max_length=20, choices=POSTE_CHOICES, default='guichetier')
    cni = models.CharField(max_length=50, blank=True, help_text="Numero de carte d'identite")
    date_embauche = models.DateField(null=True, blank=True)
    salaire = models.IntegerField(null=True, blank=True, help_text="Salaire mensuel en FCFA")
    actif = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.get_poste_display()})"

    class Meta:
        verbose_name_plural = "Employes"
        ordering = ['nom', 'prenom']


class TransfertArgent(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente de retrait'),
        ('retire', 'Retire'),
        ('annule', 'Annule'),
        ('rembourse', 'Rembourse'),
    ]

    code_transfert = models.CharField(max_length=20, unique=True, blank=True)
    compagnie = models.ForeignKey(Compagnie, on_delete=models.PROTECT, related_name='transferts')

    expediteur_nom = models.CharField(max_length=100)
    expediteur_telephone = models.CharField(max_length=20)
    beneficiaire_nom = models.CharField(max_length=100)
    beneficiaire_telephone = models.CharField(max_length=20)

    agence_depart = models.ForeignKey(Agence, on_delete=models.PROTECT, related_name='transferts_envoyes')
    agence_retrait = models.ForeignKey(Agence, on_delete=models.PROTECT, related_name='transferts_recus')
    cree_par = models.ForeignKey('Employe', on_delete=models.SET_NULL, null=True, blank=True, related_name='transferts_crees', verbose_name="Cree par")

    montant = models.IntegerField(help_text="Montant envoye en FCFA")
    frais = models.IntegerField(default=0, help_text="Frais de transfert en FCFA")
    code_retrait = models.CharField(max_length=10, blank=True, help_text="Code secret remis au beneficiaire")

    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    date_envoi = models.DateTimeField(auto_now_add=True)
    date_retrait = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.code_transfert} - {self.expediteur_nom} -> {self.beneficiaire_nom}"

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
    TYPE_CHOICES = [
        ('vidange', 'Vidange moteur'),
        ('freins', 'Freins'),
        ('pneus', 'Pneus'),
        ('revision', 'Revision generale'),
        ('boite_vitesse', 'Vidange boite de vitesse'),
        ('courroie', 'Courroie'),
        ('batterie', 'Batterie'),
        ('climatisation', 'Climatisation'),
        ('carrosserie', 'Carrosserie'),
        ('autre', 'Autre'),
    ]

    bus = models.ForeignKey('Bus', on_delete=models.CASCADE, related_name='entretiens', verbose_name="Bus")
    type_entretien = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="Type d'entretien")
    date_entretien = models.DateField(verbose_name="Date de l'entretien")
    kilometrage = models.PositiveIntegerField(default=0, verbose_name="Kilometrage du bus")
    cout = models.PositiveIntegerField(default=0, verbose_name="Cout (FCFA)")
    description = models.TextField(blank=True, verbose_name="Details / pieces changees")
    prochain_km = models.PositiveIntegerField(null=True, blank=True, verbose_name="Prochaine echeance (km)")
    cree_par = models.ForeignKey('Employe', on_delete=models.SET_NULL, null=True, blank=True, related_name='entretiens_crees', verbose_name="Enregistre par")
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Entretien"
        verbose_name_plural = "Entretiens"
        ordering = ['-date_entretien']

    def __str__(self):
        return f"{self.get_type_entretien_display()} - {self.bus} ({self.date_entretien})"


class PleinCarburant(models.Model):
    bus = models.ForeignKey('Bus', on_delete=models.CASCADE, related_name='pleins', verbose_name="Bus")
    voyage = models.ForeignKey('Voyage', on_delete=models.SET_NULL, null=True, blank=True, related_name='pleins', verbose_name="Voyage")
    date_plein = models.DateField(verbose_name="Date du plein")
    litres = models.DecimalField(max_digits=7, decimal_places=2, default=0, verbose_name="Litres")
    montant = models.PositiveIntegerField(default=0, verbose_name="Montant (FCFA)")
    kilometrage = models.PositiveIntegerField(null=True, blank=True, verbose_name="Kilometrage")
    cree_par = models.ForeignKey('Employe', on_delete=models.SET_NULL, null=True, blank=True, related_name='pleins_crees', verbose_name="Enregistre par")
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Plein de carburant"
        verbose_name_plural = "Pleins de carburant"
        ordering = ['-date_plein']

    def __str__(self):
        return f"Plein {self.bus} - {self.montant} FCFA ({self.date_plein})"


class Siege(models.Model):
    voyage = models.ForeignKey('Voyage', on_delete=models.CASCADE, related_name='sieges')
    numero = models.IntegerField(help_text="Numero du siege")

    def __str__(self):
        return f"Siege {self.numero} - {self.voyage}"

    def est_libre(self, ordre_montee, ordre_descente):
        """
        Verifie si ce siege est libre sur le segment [ordre_montee, ordre_descente[.
        Deux segments se chevauchent si depart_A < arrivee_B ET depart_B < arrivee_A.
        """
        reservations_actives = self.reservations.exclude(statut__in=['annulee', 'remboursee'])

        if not self.voyage.ligne_id:
            return not reservations_actives.exists()

        for resa in reservations_actives:
            depart_existant = resa.arret_montee.ordre if resa.arret_montee else 1
            arrivee_existante = resa.arret_descente.ordre if resa.arret_descente else 999999
            if depart_existant < ordre_descente and ordre_montee < arrivee_existante:
                return False
        return True

    class Meta:
        ordering = ['voyage', 'numero']
        unique_together = ['voyage', 'numero']

class Promotion(models.Model):
    titre = models.CharField(max_length=120, help_text="Titre de la promotion")
    texte = models.TextField(help_text="Description de la promotion")
    image = models.ImageField(upload_to='promotions/', null=True, blank=True, help_text="Image de la promotion")
    date_debut = models.DateField(help_text="Date de debut de validite")
    date_fin = models.DateField(help_text="Date de fin de validite")
    actif = models.BooleanField(default=True, help_text="Decochez pour masquer")
    date_creation = models.DateTimeField(auto_now_add=True)
    service = models.CharField(max_length=20, choices=[('voyage', 'Reservation de voyage'), ('colis', 'Envoi de colis'), ('transfert', "Transfert d'argent"), ('aucun', 'Aucun')], default='aucun', help_text="Vers quel service renvoie la promotion")

    def __str__(self):
        return self.titre

    class Meta:
        verbose_name = "Promotion"
        verbose_name_plural = "Promotions"
        ordering = ['-date_creation']

    
class DemandeColis(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente de validation'),
        ('validee', 'Validee (colis cree)'),
        ('annulee', 'Annulee'),
    ]
    numero_demande = models.CharField(max_length=20, unique=True, blank=True)
    client = models.ForeignKey('Client', on_delete=models.SET_NULL, null=True, blank=True, related_name='demandes_colis')
    expediteur_nom = models.CharField(max_length=100)
    expediteur_telephone = models.CharField(max_length=20)
    destinataire_nom = models.CharField(max_length=100)
    destinataire_telephone = models.CharField(max_length=20)
    agence_depart = models.ForeignKey('Agence', on_delete=models.PROTECT, related_name='demandes_colis_depart')
    agence_arrivee = models.ForeignKey('Agence', on_delete=models.PROTECT, related_name='demandes_colis_arrivee')
    description = models.CharField(max_length=200)
    poids_estime = models.FloatField(help_text="Poids estime en kg")
    valeur_declaree = models.IntegerField(default=0, help_text="Valeur declaree en FCFA")
    poids_reel = models.FloatField(null=True, blank=True, help_text="Poids reel pese a l'agence (kg)")
    prix = models.IntegerField(null=True, blank=True, help_text="Prix fixe par l'agence (FCFA)")
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    colis = models.ForeignKey('Colis', on_delete=models.SET_NULL, null=True, blank=True, related_name='demande_origine')
    date_demande = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.numero_demande} - {self.expediteur_nom}"

    def save(self, *args, **kwargs):
        if not self.numero_demande:
            from datetime import datetime
            annee = datetime.now().year
            dernier = DemandeColis.objects.filter(numero_demande__startswith=f"DC-{annee}-").count()
            self.numero_demande = f"DC-{annee}-{dernier + 1:04d}"
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Demande de colis"
        verbose_name_plural = "Demandes de colis"
        ordering = ['-date_demande']


class DemandeTransfert(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente de validation'),
        ('validee', 'Validee (transfert cree)'),
        ('annulee', 'Annulee'),
    ]
    numero_demande = models.CharField(max_length=20, unique=True, blank=True)
    client = models.ForeignKey('Client', on_delete=models.SET_NULL, null=True, blank=True, related_name='demandes_transfert')
    expediteur_nom = models.CharField(max_length=100)
    expediteur_telephone = models.CharField(max_length=20)
    beneficiaire_nom = models.CharField(max_length=100)
    beneficiaire_telephone = models.CharField(max_length=20)
    agence_depart = models.ForeignKey('Agence', on_delete=models.PROTECT, related_name='demandes_transfert_depart')
    agence_retrait = models.ForeignKey('Agence', on_delete=models.PROTECT, related_name='demandes_transfert_retrait')
    montant = models.IntegerField(help_text="Montant a envoyer en FCFA")
    frais = models.IntegerField(null=True, blank=True, help_text="Frais fixes par l'agence")
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    transfert = models.ForeignKey('TransfertArgent', on_delete=models.SET_NULL, null=True, blank=True, related_name='demande_origine')
    date_demande = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.numero_demande} - {self.expediteur_nom}"

    def save(self, *args, **kwargs):
        if not self.numero_demande:
            from datetime import datetime
            annee = datetime.now().year
            dernier = DemandeTransfert.objects.filter(numero_demande__startswith=f"DT-{annee}-").count()
            self.numero_demande = f"DT-{annee}-{dernier + 1:04d}"
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Demande de transfert"
        verbose_name_plural = "Demandes de transfert"
        ordering = ['-date_demande']


        
class Ligne(models.Model):
    compagnie = models.ForeignKey('Compagnie', on_delete=models.CASCADE, related_name='lignes')
    nom = models.CharField(max_length=120, help_text="Ex : Ndjamena - Abeche (axe Est)")
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nom

    def villes(self):
        return [a.agence.ville for a in self.arrets.all().order_by('ordre')]

    class Meta:
        verbose_name = "Ligne"
        verbose_name_plural = "Lignes"
        ordering = ['nom']


class ArretLigne(models.Model):
    ligne = models.ForeignKey('Ligne', on_delete=models.CASCADE, related_name='arrets')
    agence = models.ForeignKey('Agence', on_delete=models.PROTECT, related_name='arrets')
    ordre = models.IntegerField(help_text="1 = ville de depart, puis 2, 3, 4...")
    prix_depuis_depart = models.IntegerField(default=0, help_text="Prix en FCFA depuis la ville de depart")

    def __str__(self):
        return f"{self.ordre}. {self.agence.ville} ({self.prix_depuis_depart} FCFA)"

    class Meta:
        verbose_name = "Arret de ligne"
        verbose_name_plural = "Arrets de ligne"
        ordering = ['ligne', 'ordre']
        unique_together = ['ligne', 'ordre']