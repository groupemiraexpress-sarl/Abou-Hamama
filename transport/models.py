from django.db import models
from django.utils.translation import gettext_lazy as _


class Compagnie(models.Model):
    nom = models.CharField(_("Nom"), max_length=100)
    sigle = models.CharField(_("Sigle"), max_length=20, blank=True)
    siege_social = models.CharField(_("Siege social"), max_length=200)
    telephone = models.CharField(_("Telephone"), max_length=20)
    email = models.EmailField(_("Email"), blank=True)
    date_creation = models.DateField(_("Date de creation"), null=True, blank=True)
    actif = models.BooleanField(_("Actif"), default=True)

    def __str__(self):
        return self.nom

    class Meta:
        verbose_name = _("Compagnie")
        verbose_name_plural = _("Compagnies")


class Agence(models.Model):
    ZONE_CHOICES = [
        ('nord', _('Nord')),
        ('sud', _('Sud')),
    ]

    compagnie = models.ForeignKey(Compagnie, on_delete=models.CASCADE, related_name='agences', verbose_name=_("Compagnie"))
    zone = models.CharField(_("Zone"), max_length=10, choices=ZONE_CHOICES, blank=True, help_text=_("Zone geographique (pour le planning)"))
    nom = models.CharField(_("Nom"), max_length=100)
    ville = models.CharField(_("Ville"), max_length=50)
    adresse = models.CharField(_("Adresse"), max_length=200)
    telephone = models.CharField(_("Telephone"), max_length=20)
    latitude = models.FloatField(_("Latitude"), null=True, blank=True)
    longitude = models.FloatField(_("Longitude"), null=True, blank=True)
    responsable = models.CharField(_("Responsable"), max_length=100, blank=True)
    actif = models.BooleanField(_("Actif"), default=True)

    def __str__(self):
        return f"{self.nom} ({self.ville})"

    class Meta:
        verbose_name = _("Agence")
        verbose_name_plural = _("Agences")


class Bus(models.Model):
    STATUT_CHOICES = [
        ('en_service', _('En service')),
        ('maintenance', _('En maintenance')),
        ('hors_service', _('Hors service')),
    ]

    compagnie = models.ForeignKey(Compagnie, on_delete=models.CASCADE, related_name='bus', verbose_name=_("Compagnie"))
    agence = models.ForeignKey('Agence', on_delete=models.SET_NULL, null=True, blank=True, related_name='bus', verbose_name=_("Agence"), help_text=_("Agence de rattachement du bus"))
    immatriculation = models.CharField(_("Immatriculation"), max_length=20, unique=True)
    marque = models.CharField(_("Marque"), max_length=50)
    modele = models.CharField(_("Modele"), max_length=50, blank=True)
    capacite = models.IntegerField(_("Capacite"))
    kilometrage = models.IntegerField(_("Kilometrage"), default=0)
    annee = models.IntegerField(_("Annee"), null=True, blank=True)
    statut = models.CharField(_("Statut"), max_length=20, choices=STATUT_CHOICES, default='en_service')
    date_visite_technique = models.DateField(_("Date visite technique"), null=True, blank=True)
    date_assurance = models.DateField(_("Date assurance"), null=True, blank=True)

    def __str__(self):
        return f"{self.immatriculation} - {self.marque}"

    class Meta:
        verbose_name = _("Bus")
        verbose_name_plural = _("Bus")


class Chauffeur(models.Model):
    STATUT_CHOICES = [
        ('disponible', _('Disponible')),
        ('en_mission', _('En mission')),
        ('repos', _('En repos')),
        ('inactif', _('Inactif')),
    ]

    user = models.OneToOneField('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='chauffeur', verbose_name=_("Compte de connexion"), help_text=_("Compte de connexion de ce chauffeur (cree par le PDG)"))
    compagnie = models.ForeignKey(Compagnie, on_delete=models.CASCADE, related_name='chauffeurs', verbose_name=_("Compagnie"))
    agence = models.ForeignKey('Agence', on_delete=models.SET_NULL, null=True, blank=True, related_name='chauffeurs', verbose_name=_("Agence"), help_text=_("Agence de rattachement du chauffeur"))
    nom = models.CharField(_("Nom"), max_length=100)
    prenom = models.CharField(_("Prenom"), max_length=100)
    telephone = models.CharField(_("Telephone"), max_length=20)
    numero_permis = models.CharField(_("Numero de permis"), max_length=50, unique=True)
    date_expiration_permis = models.DateField(_("Date d'expiration du permis"), null=True, blank=True)
    date_embauche = models.DateField(_("Date d'embauche"), null=True, blank=True)
    annees_experience = models.IntegerField(_("Annees d'experience"), default=0)
    statut = models.CharField(_("Statut"), max_length=20, choices=STATUT_CHOICES, default='disponible')
    photo = models.ImageField(_("Photo"), upload_to='chauffeurs/', null=True, blank=True)
    actif = models.BooleanField(_("Actif"), default=True)

    def __str__(self):
        return f"{self.prenom} {self.nom}"

    class Meta:
        verbose_name = _("Chauffeur")
        verbose_name_plural = _("Chauffeurs")
        ordering = ['nom', 'prenom']


class Trajet(models.Model):
    compagnie = models.ForeignKey(Compagnie, on_delete=models.CASCADE, related_name='trajets', verbose_name=_("Compagnie"))
    ville_depart = models.CharField(_("Ville de depart"), max_length=50)
    ville_arrivee = models.CharField(_("Ville d'arrivee"), max_length=50)
    distance_km = models.IntegerField(_("Distance (km)"), help_text=_("Distance en kilometres"))
    duree_estimee_heures = models.FloatField(_("Duree estimee (heures)"), help_text=_("Duree estimee en heures"))
    prix_base = models.IntegerField(_("Prix de base"), help_text=_("Prix du billet en FCFA"))
    actif = models.BooleanField(_("Actif"), default=True)

    def __str__(self):
        return f"{self.ville_depart} -> {self.ville_arrivee}"

    class Meta:
        verbose_name = _("Trajet")
        verbose_name_plural = _("Trajets")
        ordering = ['ville_depart', 'ville_arrivee']
        unique_together = ['compagnie', 'ville_depart', 'ville_arrivee']


class Voyage(models.Model):
    STATUT_CHOICES = [
        ('programme', _('Programme')),
        ('en_cours', _('En cours')),
        ('termine', _('Termine')),
        ('annule', _('Annule')),
    ]

    trajet = models.ForeignKey(Trajet, on_delete=models.PROTECT, related_name='voyages', verbose_name=_("Trajet"))
    ligne = models.ForeignKey('Ligne', on_delete=models.PROTECT, related_name='voyages', null=True, blank=True, verbose_name=_("Ligne"), help_text=_("Ligne desservie (si le voyage dessert plusieurs villes)"))
    bus = models.ForeignKey(Bus, on_delete=models.PROTECT, related_name='voyages', verbose_name=_("Bus"))
    chauffeur = models.ForeignKey(Chauffeur, on_delete=models.PROTECT, related_name='voyages', verbose_name=_("Chauffeur"))
    date_depart = models.DateField(_("Date de depart"))
    heure_depart = models.TimeField(_("Heure de depart"))
    heure_arrivee_prevue = models.TimeField(_("Heure d'arrivee prevue"), null=True, blank=True)
    prix = models.IntegerField(_("Prix"), help_text=_("Prix du billet en FCFA"))
    places_disponibles = models.IntegerField(_("Places disponibles"))
    statut = models.CharField(_("Statut"), max_length=20, choices=STATUT_CHOICES, default='programme')
    notes = models.TextField(_("Notes"), blank=True)
    date_creation = models.DateTimeField(_("Date de creation"), auto_now_add=True)

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
        verbose_name = _("Voyage")
        verbose_name_plural = _("Voyages")
        ordering = ['-date_depart', '-heure_depart']


def generer_code_parrainage():
    """Genere un code du type AH-X7K2P9 (sans lettres/chiffres ambigus)."""
    import random
    caracteres = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    return 'AH-' + ''.join(random.choice(caracteres) for _lettre in range(6))


class Client(models.Model):
    TYPE_CHOICES = [
        ('particulier', _('Particulier')),
        ('entreprise', _('Entreprise')),
    ]

    TYPE_PIECE_CHOICES = [
        ('cni', _('Carte nationale d\'identite')),
        ('passeport', _('Passeport')),
        ('acte_naissance', _('Acte de naissance')),
        ('carte_pro', _('Carte professionnelle')),
        ('permis', _('Permis de conduire')),
        ('autre', _('Autre piece')),
    ]

    NIVEAU_CHOICES = [
        ('bronze', _('Bronze')),
        ('argent', _('Argent')),
        ('or', _('Or')),
    ]

    user = models.OneToOneField('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='client', verbose_name=_("Compte de connexion"), help_text=_("Compte de connexion lie a cette fiche client (app mobile)"))
    nom = models.CharField(_("Nom"), max_length=100)
    prenom = models.CharField(_("Prenom"), max_length=100, blank=True)
    telephone = models.CharField(_("Telephone"), max_length=20, unique=True)
    email = models.EmailField(_("Email"), blank=True)
    type_client = models.CharField(_("Type de client"), max_length=20, choices=TYPE_CHOICES, default='particulier')
    type_piece = models.CharField(_("Type de piece"), max_length=20, choices=TYPE_PIECE_CHOICES, blank=True, help_text=_("Type de piece d'identite"))
    cni = models.CharField(_("Numero de piece"), max_length=50, blank=True, help_text=_("Numero de la piece d'identite"))
    ville_residence = models.CharField(_("Ville de residence"), max_length=50, blank=True)
    date_inscription = models.DateTimeField(_("Date d'inscription"), auto_now_add=True)
    nombre_voyages = models.IntegerField(_("Nombre de voyages"), default=0, help_text=_("Nombre total de voyages effectues"))
    points_fidelite = models.IntegerField(_("Points de fidelite"), default=0, help_text=_("1 point par 100 FCFA depense"))
    niveau_fidelite = models.CharField(_("Niveau de fidelite"), max_length=10, choices=NIVEAU_CHOICES, default='bronze')
    code_parrainage = models.CharField(_("Code de parrainage"), max_length=12, unique=True, blank=True, null=True, help_text=_("Code unique que ce client partage a ses amis"))
    parraine_par = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='filleuls', verbose_name=_("Parraine par"), help_text=_("Client qui a parraine ce client"))
    bonus_parrainage_attribue = models.BooleanField(_("Bonus parrainage attribue"), default=False, help_text=_("Vrai si le bonus de parrainage a deja ete donne (au premier billet paye)"))
    photo = models.ImageField(_("Photo de profil"), upload_to='profils_clients/', null=True, blank=True)
    actif = models.BooleanField(_("Actif"), default=True)

    def mettre_a_jour_niveau(self):
        if self.points_fidelite >= 2000:
            self.niveau_fidelite = 'or'
        elif self.points_fidelite >= 500:
            self.niveau_fidelite = 'argent'
        else:
            self.niveau_fidelite = 'bronze'

    def save(self, *args, **kwargs):
        if not self.code_parrainage:
            code = generer_code_parrainage()
            while Client.objects.filter(code_parrainage=code).exists():
                code = generer_code_parrainage()
            self.code_parrainage = code
        super().save(*args, **kwargs)

    def __str__(self):
        if self.prenom:
            return f"{self.prenom} {self.nom} ({self.telephone})"
        return f"{self.nom} ({self.telephone})"

    class Meta:
        verbose_name = _("Client")
        verbose_name_plural = _("Clients")
        ordering = ['nom', 'prenom']


class Reservation(models.Model):
    STATUT_CHOICES = [
        ('en_attente', _('En attente de paiement')),
        ('payee', _('Payee')),
        ('annulee', _('Annulee')),
        ('remboursee', _('Remboursee')),
    ]

    MODE_PAIEMENT_CHOICES = [
        ('especes', _('Especes')),
        ('mobile_money', _('Mobile Money')),
        ('virement', _('Virement bancaire')),
        ('carte', _('Carte bancaire')),
    ]

    numero_reservation = models.CharField(_("Numero de reservation"), max_length=20, unique=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='reservations', verbose_name=_("Client"))
    voyage = models.ForeignKey(Voyage, on_delete=models.PROTECT, related_name='reservations', verbose_name=_("Voyage"))
    agence = models.ForeignKey(Agence, on_delete=models.PROTECT, related_name='reservations', null=True, blank=True, verbose_name=_("Agence"), help_text=_("Agence ou la reservation a ete faite"))
    cree_par = models.ForeignKey('Employe', on_delete=models.SET_NULL, null=True, blank=True, related_name='reservations_creees', verbose_name=_("Cree par"))
    modifie_par = models.ForeignKey('Employe', on_delete=models.SET_NULL, null=True, blank=True, related_name='reservations_modifiees', verbose_name=_("Modifie par"))
    embarque = models.BooleanField(_("Embarque"), default=False, help_text=_("Coche automatiquement quand le billet est scanne au controle"))
    date_embarquement = models.DateTimeField(_("Date d'embarquement"), null=True, blank=True)
    scanne_par = models.ForeignKey('Employe', on_delete=models.SET_NULL, null=True, blank=True, related_name='reservations_scannees', verbose_name=_("Scanne par"))
    points_attribues = models.BooleanField(_("Points attribues"), default=False, help_text=_("Vrai si les points de fidelite ont deja ete comptes pour cette reservation"))
    nombre_places = models.IntegerField(_("Nombre de places"), default=1)
    voyageur_nom = models.CharField(_("Nom du voyageur"), max_length=100, blank=True, help_text=_("Nom du voyageur de ce billet"))
    voyageur_prenom = models.CharField(_("Prenom du voyageur"), max_length=100, blank=True, help_text=_("Prenom du voyageur"))
    voyageur_telephone = models.CharField(_("Telephone du voyageur"), max_length=20, blank=True, help_text=_("Telephone du voyageur"))
    voyageur_type_piece = models.CharField(_("Type de piece du voyageur"), max_length=20, blank=True, help_text=_("Type de piece du voyageur"))
    voyageur_numero_piece = models.CharField(_("Numero de piece du voyageur"), max_length=50, blank=True, help_text=_("Numero de piece du voyageur"))
    voyageur_nationalite = models.CharField(_("Nationalite du voyageur"), max_length=50, blank=True, help_text=_("Nationalite indiquee sur la piece"))
    voyageur_date_emission = models.DateField(_("Date d'emission de la piece"), null=True, blank=True)
    voyageur_date_expiration = models.DateField(_("Date d'expiration de la piece"), null=True, blank=True)
    siege = models.ForeignKey('Siege', on_delete=models.PROTECT, null=True, blank=True, related_name='reservations', verbose_name=_("Siege"), help_text=_("Siege physique reserve"))
    arret_montee = models.ForeignKey('ArretLigne', on_delete=models.SET_NULL, null=True, blank=True, related_name='reservations_montee', verbose_name=_("Arret de montee"), help_text=_("Arret ou le voyageur monte (si ligne multi-arrets)"))
    arret_descente = models.ForeignKey('ArretLigne', on_delete=models.SET_NULL, null=True, blank=True, related_name='reservations_descente', verbose_name=_("Arret de descente"), help_text=_("Arret ou le voyageur descend (si ligne multi-arrets)"))
    montant_total = models.IntegerField(_("Montant total"), default=0, blank=True, help_text=_("Calcule automatiquement"))
    statut = models.CharField(_("Statut"), max_length=20, choices=STATUT_CHOICES, default='en_attente')
    mode_paiement = models.CharField(_("Mode de paiement"), max_length=20, choices=MODE_PAIEMENT_CHOICES, blank=True)
    date_reservation = models.DateTimeField(_("Date de reservation"), auto_now_add=True)
    date_paiement = models.DateTimeField(_("Date de paiement"), null=True, blank=True)
    alerte_expiration_envoyee = models.BooleanField(_("Alerte d'expiration envoyee"), default=False, help_text=_("Vrai si l'avertissement (2h avant l'annulation automatique) a deja ete envoye"))
    notes = models.TextField(_("Notes"), blank=True)

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
            if self.siege_id and self.statut not in ('annulee', 'remboursee'):
                ordre_montee = self.arret_montee.ordre if self.arret_montee_id else 1
                ordre_descente = self.arret_descente.ordre if self.arret_descente_id else 999999
                if not self.siege.est_libre(ordre_montee, ordre_descente):
                    raise ValueError(
                        f"Le siege {self.siege.numero} est deja reserve sur ce trajet (verifiez les reservations existantes)."
                    )
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

        if self.statut == 'payee' and not self.points_attribues and self.client_id:
            self.points_attribues = True
            points_gagnes = int(self.montant_total // 100)
            self.client.points_fidelite += points_gagnes
            self.client.nombre_voyages += 1
            if self.client.parraine_par_id and not self.client.bonus_parrainage_attribue:
                self.client.bonus_parrainage_attribue = True
                self.client.points_fidelite += 25
                parrain = self.client.parraine_par
                parrain.points_fidelite += 50
                parrain.mettre_a_jour_niveau()
                parrain.save()
            self.client.mettre_a_jour_niveau()
            self.client.save()

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Reservation")
        verbose_name_plural = _("Reservations")
        ordering = ['-date_reservation']


class Colis(models.Model):
    STATUT_CHOICES = [
        ('enregistre', _('Enregistre')),
        ('en_transit', _('En transit')),
        ('arrive', _('Arrive a destination')),
        ('livre', _('Livre')),
        ('retourne', _('Retourne')),
    ]

    code_suivi = models.CharField(_("Code de suivi"), max_length=20, unique=True, blank=True)
    compagnie = models.ForeignKey(Compagnie, on_delete=models.PROTECT, related_name='colis', verbose_name=_("Compagnie"))

    expediteur_nom = models.CharField(_("Nom de l'expediteur"), max_length=100)
    expediteur_telephone = models.CharField(_("Telephone de l'expediteur"), max_length=20)
    destinataire_nom = models.CharField(_("Nom du destinataire"), max_length=100)
    destinataire_telephone = models.CharField(_("Telephone du destinataire"), max_length=20)
    expediteur_nationalite = models.CharField(_("Nationalite de l'expediteur"), max_length=50, blank=True)
    expediteur_type_piece = models.CharField(_("Type de piece de l'expediteur"), max_length=20, blank=True)
    expediteur_numero_piece = models.CharField(_("Numero de piece de l'expediteur"), max_length=50, blank=True)
    destinataire_nationalite = models.CharField(_("Nationalite du destinataire"), max_length=50, blank=True)
    destinataire_type_piece = models.CharField(_("Type de piece du destinataire"), max_length=20, blank=True)
    destinataire_numero_piece = models.CharField(_("Numero de piece du destinataire"), max_length=50, blank=True)

    agence_depart = models.ForeignKey(Agence, on_delete=models.PROTECT, related_name='colis_envoyes', verbose_name=_("Agence de depart"))
    agence_arrivee = models.ForeignKey(Agence, on_delete=models.PROTECT, related_name='colis_recus', verbose_name=_("Agence d'arrivee"))
    cree_par = models.ForeignKey('Employe', on_delete=models.SET_NULL, null=True, blank=True, related_name='colis_crees', verbose_name=_("Cree par"))
    modifie_par = models.ForeignKey('Employe', on_delete=models.SET_NULL, null=True, blank=True, related_name='colis_modifies', verbose_name=_("Modifie par"))

    description = models.CharField(_("Description"), max_length=200, help_text=_("Contenu du colis"))
    poids_kg = models.FloatField(_("Poids (kg)"), help_text=_("Poids en kilogrammes"))
    prix = models.IntegerField(_("Prix"), help_text=_("Prix en FCFA"))

    voyage = models.ForeignKey(Voyage, on_delete=models.SET_NULL, related_name='colis', null=True, blank=True, verbose_name=_("Voyage"), help_text=_("Voyage sur lequel le colis est transporte"))

    statut = models.CharField(_("Statut"), max_length=20, choices=STATUT_CHOICES, default='enregistre')
    code_retrait = models.CharField(_("Code de retrait"), max_length=10, blank=True, help_text=_("Code secret remis au destinataire, exige a la remise"))
    date_enregistrement = models.DateTimeField(_("Date d'enregistrement"), auto_now_add=True)
    date_arrivee = models.DateTimeField(_("Date d'arrivee a l'agence"), null=True, blank=True, help_text=_("Renseignee automatiquement quand le colis passe au statut 'Arrive a destination'. Sert de point de depart au delai de 5 jours pour le retrait."))
    date_livraison = models.DateTimeField(_("Date de livraison"), null=True, blank=True)
    alerte_retrait_envoyee = models.BooleanField(_("Alerte de retrait envoyee"), default=False, help_text=_("Vrai si l'avertissement (2h avant le retour automatique) a deja ete envoye"))
    notes = models.TextField(_("Notes"), blank=True)

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

        if not self.code_retrait:
            import random
            self.code_retrait = str(random.randint(10000, 99999))

        if self.statut == 'arrive' and not self.date_arrivee:
            ancien_statut = None
            if self.pk:
                ancien_statut = Colis.objects.filter(pk=self.pk).values_list('statut', flat=True).first()
            if ancien_statut != 'arrive':
                from django.utils import timezone
                self.date_arrivee = timezone.now()

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Colis")
        verbose_name_plural = _("Colis")
        ordering = ['-date_enregistrement']


class Employe(models.Model):
    POSTE_CHOICES = [
        ('pdg', _('PDG / Directeur general')),
        ('responsable', _("Responsable d'agence")),
        ('secretaire', _("Secretaire d'agence")),
        ('resp_planning', _("Responsable planning")),
        ('guichetier', _('Guichetier / billettiste')),
        ('caissier', _('Caissier')),
        ('agent_colis', _('Agent colis')),
        ('agent_transfert', _("Agent transfert d'argent")),
        ('manutentionnaire', _('Manutentionnaire / bagagiste')),
        ('comptable', _('Comptable')),
        ('rh', _('Responsable RH / recrutement')),
        ('resp_maintenance', _('Responsable maintenance')),
        ('securite', _('Agent de securite')),
        ('autre', _('Autre')),
    ]

    user = models.OneToOneField('auth.User', on_delete=models.SET_NULL, related_name='employe', null=True, blank=True, verbose_name=_("Compte de connexion"), help_text=_("Compte de connexion lie a cet employe"))
    compagnie = models.ForeignKey(Compagnie, on_delete=models.CASCADE, related_name='employes', verbose_name=_("Compagnie"))
    agence = models.ForeignKey(Agence, on_delete=models.SET_NULL, related_name='employes', null=True, blank=True, verbose_name=_("Agence"), help_text=_("Laisser vide pour un PDG (toute la compagnie)"))
    zone = models.CharField(_("Zone"), max_length=10, choices=Agence.ZONE_CHOICES, blank=True, help_text=_("Zone geographique geree (uniquement pour Responsable planning)"))
    nom = models.CharField(_("Nom"), max_length=100)
    prenom = models.CharField(_("Prenom"), max_length=100)
    telephone = models.CharField(_("Telephone"), max_length=20)
    poste = models.CharField(_("Poste"), max_length=20, choices=POSTE_CHOICES, default='guichetier')
    cni = models.CharField(_("Numero de piece"), max_length=50, blank=True, help_text=_("Numero de carte d'identite"))
    date_embauche = models.DateField(_("Date d'embauche"), null=True, blank=True)
    salaire = models.IntegerField(_("Salaire"), null=True, blank=True, help_text=_("Salaire mensuel en FCFA"))
    photo = models.ImageField(_("Photo"), upload_to='employes/', null=True, blank=True)
    actif = models.BooleanField(_("Actif"), default=True)

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.get_poste_display()})"

    class Meta:
        verbose_name = _("Employe")
        verbose_name_plural = _("Employes")
        ordering = ['nom', 'prenom']


class TransfertArgent(models.Model):
    STATUT_CHOICES = [
        ('en_attente', _('En attente de retrait')),
        ('retire', _('Retire')),
        ('annule', _('Annule')),
        ('rembourse', _('Rembourse')),
    ]

    code_transfert = models.CharField(_("Code de transfert"), max_length=20, unique=True, blank=True)
    compagnie = models.ForeignKey(Compagnie, on_delete=models.PROTECT, related_name='transferts', verbose_name=_("Compagnie"))

    expediteur_nom = models.CharField(_("Nom de l'expediteur"), max_length=100)
    expediteur_telephone = models.CharField(_("Telephone de l'expediteur"), max_length=20)
    beneficiaire_nom = models.CharField(_("Nom du beneficiaire"), max_length=100)
    beneficiaire_telephone = models.CharField(_("Telephone du beneficiaire"), max_length=20)
    expediteur_nationalite = models.CharField(_("Nationalite de l'expediteur"), max_length=50, blank=True)
    expediteur_type_piece = models.CharField(_("Type de piece de l'expediteur"), max_length=20, blank=True)
    expediteur_numero_piece = models.CharField(_("Numero de piece de l'expediteur"), max_length=50, blank=True)
    beneficiaire_nationalite = models.CharField(_("Nationalite du beneficiaire"), max_length=50, blank=True)
    beneficiaire_type_piece = models.CharField(_("Type de piece du beneficiaire"), max_length=20, blank=True)
    beneficiaire_numero_piece = models.CharField(_("Numero de piece du beneficiaire"), max_length=50, blank=True)

    agence_depart = models.ForeignKey(Agence, on_delete=models.PROTECT, related_name='transferts_envoyes', verbose_name=_("Agence de depart"))
    agence_retrait = models.ForeignKey(Agence, on_delete=models.PROTECT, related_name='transferts_recus', verbose_name=_("Agence de retrait"))
    cree_par = models.ForeignKey('Employe', on_delete=models.SET_NULL, null=True, blank=True, related_name='transferts_crees', verbose_name=_("Cree par"))
    modifie_par = models.ForeignKey('Employe', on_delete=models.SET_NULL, null=True, blank=True, related_name='transferts_modifies', verbose_name=_("Modifie par"))

    montant = models.IntegerField(_("Montant"), help_text=_("Montant envoye en FCFA"))
    frais = models.IntegerField(_("Frais"), default=0, help_text=_("Frais de transfert en FCFA"))
    code_retrait = models.CharField(_("Code de retrait"), max_length=10, blank=True, help_text=_("Code secret remis au beneficiaire"))

    statut = models.CharField(_("Statut"), max_length=20, choices=STATUT_CHOICES, default='en_attente')
    date_envoi = models.DateTimeField(_("Date d'envoi"), auto_now_add=True)
    date_retrait = models.DateTimeField(_("Date de retrait"), null=True, blank=True)
    alerte_retrait_envoyee = models.BooleanField(_("Alerte de retrait envoyee"), default=False, help_text=_("Vrai si l'avertissement (2h avant l'annulation automatique) a deja ete envoye"))
    notes = models.TextField(_("Notes"), blank=True)

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
        verbose_name = _("Transfert d'argent")
        verbose_name_plural = _("Transferts d'argent")
        ordering = ['-date_envoi']


class Entretien(models.Model):
    TYPE_CHOICES = [
        ('vidange', _('Vidange moteur')),
        ('freins', _('Freins')),
        ('pneus', _('Pneus')),
        ('revision', _('Revision generale')),
        ('boite_vitesse', _('Vidange boite de vitesse')),
        ('courroie', _('Courroie')),
        ('batterie', _('Batterie')),
        ('climatisation', _('Climatisation')),
        ('carrosserie', _('Carrosserie')),
        ('autre', _('Autre')),
    ]

    bus = models.ForeignKey('Bus', on_delete=models.CASCADE, related_name='entretiens', verbose_name=_("Bus"))
    type_entretien = models.CharField(_("Type d'entretien"), max_length=20, choices=TYPE_CHOICES)
    date_entretien = models.DateField(_("Date de l'entretien"))
    kilometrage = models.PositiveIntegerField(_("Kilometrage du bus"), default=0)
    cout = models.PositiveIntegerField(_("Cout (FCFA)"), default=0)
    description = models.TextField(_("Details / pieces changees"), blank=True)
    prochain_km = models.PositiveIntegerField(_("Prochaine echeance (km)"), null=True, blank=True)
    cree_par = models.ForeignKey('Employe', on_delete=models.SET_NULL, null=True, blank=True, related_name='entretiens_crees', verbose_name=_("Enregistre par"))
    date_creation = models.DateTimeField(_("Date de creation"), auto_now_add=True)

    class Meta:
        verbose_name = _("Entretien")
        verbose_name_plural = _("Entretiens")
        ordering = ['-date_entretien']

    def __str__(self):
        return f"{self.get_type_entretien_display()} - {self.bus} ({self.date_entretien})"


class PleinCarburant(models.Model):
    bus = models.ForeignKey('Bus', on_delete=models.CASCADE, related_name='pleins', verbose_name=_("Bus"))
    voyage = models.ForeignKey('Voyage', on_delete=models.SET_NULL, null=True, blank=True, related_name='pleins', verbose_name=_("Voyage"))
    date_plein = models.DateField(_("Date du plein"))
    litres = models.DecimalField(_("Litres"), max_digits=7, decimal_places=2, default=0)
    montant = models.PositiveIntegerField(_("Montant (FCFA)"), default=0)
    kilometrage = models.PositiveIntegerField(_("Kilometrage"), null=True, blank=True)
    cree_par = models.ForeignKey('Employe', on_delete=models.SET_NULL, null=True, blank=True, related_name='pleins_crees', verbose_name=_("Enregistre par"))
    date_creation = models.DateTimeField(_("Date de creation"), auto_now_add=True)

    class Meta:
        verbose_name = _("Plein de carburant")
        verbose_name_plural = _("Pleins de carburant")
        ordering = ['-date_plein']

    def __str__(self):
        return f"Plein {self.bus} - {self.montant} FCFA ({self.date_plein})"


class Siege(models.Model):
    voyage = models.ForeignKey('Voyage', on_delete=models.CASCADE, related_name='sieges', verbose_name=_("Voyage"))
    numero = models.IntegerField(_("Numero"), help_text=_("Numero du siege"))

    def __str__(self):
        return f"Siege {self.numero} - {self.voyage}"

    def est_libre(self, ordre_montee, ordre_descente, exclure_reservation_id=None):
        """
        Verifie si ce siege est libre sur le segment [ordre_montee, ordre_descente[.
        Deux segments se chevauchent si depart_A < arrivee_B ET depart_B < arrivee_A.
        """
        reservations_actives = self.reservations.exclude(statut__in=['annulee', 'remboursee'])
        if exclure_reservation_id:
            reservations_actives = reservations_actives.exclude(pk=exclure_reservation_id)

        if not self.voyage.ligne_id:
            return not reservations_actives.exists()

        for resa in reservations_actives:
            depart_existant = resa.arret_montee.ordre if resa.arret_montee else 1
            arrivee_existante = resa.arret_descente.ordre if resa.arret_descente else 999999
            if depart_existant < ordre_descente and ordre_montee < arrivee_existante:
                return False
        return True

    class Meta:
        verbose_name = _("Siege")
        verbose_name_plural = _("Sieges")
        ordering = ['voyage', 'numero']
        unique_together = ['voyage', 'numero']


class Promotion(models.Model):
    SERVICE_CHOICES = [
        ('voyage', _('Reservation de voyage')),
        ('colis', _('Envoi de colis')),
        ('transfert', _("Transfert d'argent")),
        ('aucun', _('Aucun')),
    ]

    titre = models.CharField(_("Titre"), max_length=120, help_text=_("Titre de la promotion"))
    texte = models.TextField(_("Texte"), help_text=_("Description de la promotion"))
    image = models.ImageField(_("Image"), upload_to='promotions/', null=True, blank=True, help_text=_("Image de la promotion"))
    date_debut = models.DateField(_("Date de debut"), help_text=_("Date de debut de validite"))
    date_fin = models.DateField(_("Date de fin"), help_text=_("Date de fin de validite"))
    actif = models.BooleanField(_("Actif"), default=True, help_text=_("Decochez pour masquer"))
    date_creation = models.DateTimeField(_("Date de creation"), auto_now_add=True)
    service = models.CharField(_("Service"), max_length=20, choices=SERVICE_CHOICES, default='aucun', help_text=_("Vers quel service renvoie la promotion"))

    def __str__(self):
        return self.titre

    class Meta:
        verbose_name = _("Promotion")
        verbose_name_plural = _("Promotions")
        ordering = ['-date_creation']


class DemandeColis(models.Model):
    STATUT_CHOICES = [
        ('en_attente', _('En attente de validation')),
        ('validee', _('Validee (colis cree)')),
        ('annulee', _('Annulee')),
    ]
    numero_demande = models.CharField(_("Numero de demande"), max_length=20, unique=True, blank=True)
    client = models.ForeignKey('Client', on_delete=models.SET_NULL, null=True, blank=True, related_name='demandes_colis', verbose_name=_("Client"))
    expediteur_nom = models.CharField(_("Nom de l'expediteur"), max_length=100)
    expediteur_telephone = models.CharField(_("Telephone de l'expediteur"), max_length=20)
    destinataire_nom = models.CharField(_("Nom du destinataire"), max_length=100)
    destinataire_telephone = models.CharField(_("Telephone du destinataire"), max_length=20)
    expediteur_nationalite = models.CharField(_("Nationalite de l'expediteur"), max_length=50, blank=True)
    expediteur_type_piece = models.CharField(_("Type de piece de l'expediteur"), max_length=20, blank=True)
    expediteur_numero_piece = models.CharField(_("Numero de piece de l'expediteur"), max_length=50, blank=True)
    destinataire_nationalite = models.CharField(_("Nationalite du destinataire"), max_length=50, blank=True)
    destinataire_type_piece = models.CharField(_("Type de piece du destinataire"), max_length=20, blank=True)
    destinataire_numero_piece = models.CharField(_("Numero de piece du destinataire"), max_length=50, blank=True)
    agence_depart = models.ForeignKey('Agence', on_delete=models.PROTECT, related_name='demandes_colis_depart', verbose_name=_("Agence de depart"))
    agence_arrivee = models.ForeignKey('Agence', on_delete=models.PROTECT, related_name='demandes_colis_arrivee', verbose_name=_("Agence d'arrivee"))
    description = models.CharField(_("Description"), max_length=200)
    poids_estime = models.FloatField(_("Poids estime"), help_text=_("Poids estime en kg"))
    valeur_declaree = models.IntegerField(_("Valeur declaree"), default=0, help_text=_("Valeur declaree en FCFA"))
    poids_reel = models.FloatField(_("Poids reel"), null=True, blank=True, help_text=_("Poids reel pese a l'agence (kg)"))
    prix = models.IntegerField(_("Prix"), null=True, blank=True, help_text=_("Prix fixe par l'agence (FCFA)"))
    statut = models.CharField(_("Statut"), max_length=20, choices=STATUT_CHOICES, default='en_attente')
    colis = models.ForeignKey('Colis', on_delete=models.SET_NULL, null=True, blank=True, related_name='demande_origine', verbose_name=_("Colis"))
    date_demande = models.DateTimeField(_("Date de demande"), auto_now_add=True)
    alerte_expiration_envoyee = models.BooleanField(_("Alerte d'expiration envoyee"), default=False, help_text=_("Vrai si l'avertissement (2h avant l'annulation automatique) a deja ete envoye"))
    notes = models.TextField(_("Notes"), blank=True)

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
        verbose_name = _("Demande de colis")
        verbose_name_plural = _("Demandes de colis")
        ordering = ['-date_demande']


class DemandeTransfert(models.Model):
    STATUT_CHOICES = [
        ('en_attente', _('En attente de validation')),
        ('validee', _('Validee (transfert cree)')),
        ('annulee', _('Annulee')),
    ]
    numero_demande = models.CharField(_("Numero de demande"), max_length=20, unique=True, blank=True)
    client = models.ForeignKey('Client', on_delete=models.SET_NULL, null=True, blank=True, related_name='demandes_transfert', verbose_name=_("Client"))
    expediteur_nom = models.CharField(_("Nom de l'expediteur"), max_length=100)
    expediteur_telephone = models.CharField(_("Telephone de l'expediteur"), max_length=20)
    beneficiaire_nom = models.CharField(_("Nom du beneficiaire"), max_length=100)
    beneficiaire_telephone = models.CharField(_("Telephone du beneficiaire"), max_length=20)
    expediteur_nationalite = models.CharField(_("Nationalite de l'expediteur"), max_length=50, blank=True)
    expediteur_type_piece = models.CharField(_("Type de piece de l'expediteur"), max_length=20, blank=True)
    expediteur_numero_piece = models.CharField(_("Numero de piece de l'expediteur"), max_length=50, blank=True)
    beneficiaire_nationalite = models.CharField(_("Nationalite du beneficiaire"), max_length=50, blank=True)
    beneficiaire_type_piece = models.CharField(_("Type de piece du beneficiaire"), max_length=20, blank=True)
    beneficiaire_numero_piece = models.CharField(_("Numero de piece du beneficiaire"), max_length=50, blank=True)
    agence_depart = models.ForeignKey('Agence', on_delete=models.PROTECT, related_name='demandes_transfert_depart', verbose_name=_("Agence de depart"))
    agence_retrait = models.ForeignKey('Agence', on_delete=models.PROTECT, related_name='demandes_transfert_retrait', verbose_name=_("Agence de retrait"))
    montant = models.IntegerField(_("Montant"), help_text=_("Montant a envoyer en FCFA"))
    frais = models.IntegerField(_("Frais"), null=True, blank=True, help_text=_("Frais fixes par l'agence"))
    statut = models.CharField(_("Statut"), max_length=20, choices=STATUT_CHOICES, default='en_attente')
    transfert = models.ForeignKey('TransfertArgent', on_delete=models.SET_NULL, null=True, blank=True, related_name='demande_origine', verbose_name=_("Transfert"))
    date_demande = models.DateTimeField(_("Date de demande"), auto_now_add=True)
    alerte_expiration_envoyee = models.BooleanField(_("Alerte d'expiration envoyee"), default=False, help_text=_("Vrai si l'avertissement (2h avant l'annulation automatique) a deja ete envoye"))
    notes = models.TextField(_("Notes"), blank=True)

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
        verbose_name = _("Demande de transfert")
        verbose_name_plural = _("Demandes de transfert")
        ordering = ['-date_demande']


class Ligne(models.Model):
    compagnie = models.ForeignKey('Compagnie', on_delete=models.CASCADE, related_name='lignes', verbose_name=_("Compagnie"))
    nom = models.CharField(_("Nom"), max_length=120, help_text=_("Ex : Ndjamena - Abeche (axe Est)"))
    actif = models.BooleanField(_("Actif"), default=True)
    date_creation = models.DateTimeField(_("Date de creation"), auto_now_add=True)

    def __str__(self):
        return self.nom

    def villes(self):
        return [a.agence.ville for a in self.arrets.all().order_by('ordre')]

    class Meta:
        verbose_name = _("Ligne")
        verbose_name_plural = _("Lignes")
        ordering = ['nom']


class ArretLigne(models.Model):
    ligne = models.ForeignKey('Ligne', on_delete=models.CASCADE, related_name='arrets', verbose_name=_("Ligne"))
    agence = models.ForeignKey('Agence', on_delete=models.PROTECT, related_name='arrets', verbose_name=_("Agence"))
    ordre = models.IntegerField(_("Ordre"), help_text=_("1 = ville de depart, puis 2, 3, 4..."))
    prix_depuis_depart = models.IntegerField(_("Prix depuis le depart"), default=0, help_text=_("Prix en FCFA depuis la ville de depart"))

    def __str__(self):
        return f"{self.ordre}. {self.agence.ville} ({self.prix_depuis_depart} FCFA)"

    class Meta:
        verbose_name = _("Arret de ligne")
        verbose_name_plural = _("Arrets de ligne")
        ordering = ['ligne', 'ordre']
        unique_together = ['ligne', 'ordre']


class PositionBus(models.Model):
    """Position GPS d'un bus en cours de voyage, envoyee par le telephone du chauffeur."""
    voyage = models.ForeignKey('Voyage', on_delete=models.CASCADE, related_name='positions', verbose_name=_("Voyage"))
    chauffeur = models.ForeignKey('Chauffeur', on_delete=models.SET_NULL, null=True, blank=True, related_name='positions', verbose_name=_("Chauffeur"))
    latitude = models.FloatField(_("Latitude"))
    longitude = models.FloatField(_("Longitude"))
    vitesse_kmh = models.FloatField(_("Vitesse (km/h)"), null=True, blank=True, help_text=_("Vitesse en km/h si disponible"))
    horodatage = models.DateTimeField(_("Horodatage"), auto_now_add=True)

    def __str__(self):
        return f"{self.voyage} - {self.horodatage:%d/%m/%Y %H:%M}"

    class Meta:
        verbose_name = _("Position bus")
        verbose_name_plural = _("Positions bus")
        ordering = ['-horodatage']


class AlerteVoyage(models.Model):
    """Alerte automatique quand un bus s'arrete anormalement longtemps hors agence."""
    TYPE_CHOICES = [
        ('arret_anormal', _('Arret anormal')),
    ]

    voyage = models.ForeignKey('Voyage', on_delete=models.CASCADE, related_name='alertes', verbose_name=_("Voyage"))
    type_alerte = models.CharField(_("Type d'alerte"), max_length=20, choices=TYPE_CHOICES, default='arret_anormal')
    message = models.TextField(_("Message"))
    latitude = models.FloatField(_("Latitude"), null=True, blank=True)
    longitude = models.FloatField(_("Longitude"), null=True, blank=True)
    date_creation = models.DateTimeField(_("Date de creation"), auto_now_add=True)
    resolue = models.BooleanField(_("Resolue"), default=False, help_text=_("Cocher une fois verifiee par un responsable"))

    def __str__(self):
        return f"{self.get_type_alerte_display()} - {self.voyage} ({self.date_creation:%d/%m %H:%M})"

    class Meta:
        verbose_name = _("Alerte voyage")
        verbose_name_plural = _("Alertes voyage")
        ordering = ['-date_creation']


class PushToken(models.Model):
    """Jeton de notification push Expo associe a un compte utilisateur de l'app mobile."""
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='push_tokens', verbose_name=_("Utilisateur"))
    token = models.CharField(_("Jeton Expo"), max_length=255, unique=True)
    date_creation = models.DateTimeField(_("Date de creation"), auto_now_add=True)
    date_maj = models.DateTimeField(_("Derniere mise a jour"), auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.token[:20]}..."

    class Meta:
        verbose_name = _("Jeton push")
        verbose_name_plural = _("Jetons push")
        ordering = ['-date_maj']


class AppareilConfirme(models.Model):
    """
    Appareil (telephone) deja confirme par email pour un compte donne.
    Utilise pour la regle "un seul appareil connecte a la fois" : a chaque
    connexion depuis un appareil deja present ici, on deconnecte tous les
    autres appareils (voir transport/appareils.py).
    """
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='appareils_confirmes', verbose_name=_("Compte"))
    identifiant_appareil = models.CharField(_("Identifiant de l'appareil"), max_length=100)
    date_confirmation = models.DateTimeField(_("Date de confirmation"), auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.identifiant_appareil[:16]}"

    class Meta:
        verbose_name = _("Appareil confirme")
        verbose_name_plural = _("Appareils confirmes")
        unique_together = ['user', 'identifiant_appareil']


class DemandeConfirmationAppareil(models.Model):
    """
    Demande de confirmation d'un nouvel appareil, en attente de validation
    via le lien envoye par email. Une fois validee, un AppareilConfirme
    correspondant est cree.
    """
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='demandes_appareil', verbose_name=_("Compte"))
    identifiant_appareil = models.CharField(_("Identifiant de l'appareil"), max_length=100)
    jeton = models.CharField(_("Jeton"), max_length=64, unique=True)
    date_creation = models.DateTimeField(_("Date de creation"), auto_now_add=True)
    utilisee = models.BooleanField(_("Utilisee"), default=False)

    def __str__(self):
        etat = 'confirmee' if self.utilisee else 'en attente'
        return f"{self.user.username} - {self.identifiant_appareil[:16]} ({etat})"

    class Meta:
        verbose_name = _("Demande de confirmation d'appareil")
        verbose_name_plural = _("Demandes de confirmation d'appareil")
        ordering = ['-date_creation']


class AvisVoyage(models.Model):
    """Avis laisse par un client apres un voyage termine (note + criteres detailles)."""
    reservation = models.OneToOneField('Reservation', on_delete=models.CASCADE, related_name='avis', verbose_name=_("Reservation"))
    client = models.ForeignKey('Client', on_delete=models.CASCADE, related_name='avis', verbose_name=_("Client"))
    chauffeur = models.ForeignKey('Chauffeur', on_delete=models.CASCADE, related_name='avis', verbose_name=_("Chauffeur"))
    voyage = models.ForeignKey('Voyage', on_delete=models.CASCADE, related_name='avis', verbose_name=_("Voyage"))
    note = models.IntegerField(_("Note"), help_text=_("Note globale de 1 a 5 etoiles"))
    commentaire = models.TextField(_("Commentaire"), blank=True, help_text=_("Commentaire facultatif du client"))

    bus_propre = models.BooleanField(_("Bus propre"), null=True, blank=True, help_text=_("Le bus etait-il propre ?"))
    climatisation_ok = models.BooleanField(_("Climatisation OK"), null=True, blank=True, help_text=_("La climatisation fonctionnait-elle ?"))
    television_ok = models.BooleanField(_("Television OK"), null=True, blank=True, help_text=_("La television fonctionnait-elle ?"))
    connexion_ok = models.BooleanField(_("Connexion OK"), null=True, blank=True, help_text=_("La connexion Starlink fonctionnait-elle ?"))
    chauffeur_poli = models.BooleanField(_("Chauffeur poli"), null=True, blank=True, help_text=_("Le chauffeur etait-il poli ?"))
    accompagnateur_aimable = models.BooleanField(_("Accompagnateur aimable"), null=True, blank=True, help_text=_("L'accompagnateur etait-il aimable ?"))

    date_creation = models.DateTimeField(_("Date de creation"), auto_now_add=True)

    def __str__(self):
        return f"{self.note}/5 - {self.chauffeur} ({self.voyage})"

    class Meta:
        verbose_name = _("Avis voyage")
        verbose_name_plural = _("Avis voyages")
        ordering = ['-date_creation']


class QuestionFAQ(models.Model):
    """Question frequente affichee dans l'ecran Aide de l'app mobile."""
    question = models.CharField(_("Question"), max_length=200, help_text=_("La question posee"))
    reponse = models.TextField(_("Reponse"), help_text=_("La reponse affichee au client"))
    ordre = models.IntegerField(_("Ordre"), default=0, help_text=_("Ordre d'affichage (petit numero = en haut)"))
    actif = models.BooleanField(_("Actif"), default=True, help_text=_("Decochez pour masquer sans supprimer"))
    date_creation = models.DateTimeField(_("Date de creation"), auto_now_add=True)

    def __str__(self):
        return self.question

    class Meta:
        verbose_name = _("Question FAQ")
        verbose_name_plural = _("Questions FAQ")
        ordering = ['ordre', 'id']


class Plainte(models.Model):
    """Plainte/reclamation soumise par un client depuis l'app mobile."""
    STATUT_CHOICES = [
        ('nouvelle', _('Nouvelle')),
        ('en_cours', _('En cours de traitement')),
        ('traitee', _('Traitee')),
    ]

    client = models.ForeignKey('Client', on_delete=models.SET_NULL, null=True, blank=True, related_name='plaintes', verbose_name=_("Client"))
    sujet = models.CharField(_("Sujet"), max_length=150)
    message = models.TextField(_("Message"))
    statut = models.CharField(_("Statut"), max_length=20, choices=STATUT_CHOICES, default='nouvelle')
    reponse = models.TextField(_("Reponse"), blank=True, help_text=_("Reponse donnee au client, visible dans l'app"))
    traite_par = models.ForeignKey('Employe', on_delete=models.SET_NULL, null=True, blank=True, related_name='plaintes_traitees', verbose_name=_("Traite par"))
    date_creation = models.DateTimeField(_("Date de creation"), auto_now_add=True)
    date_reponse = models.DateTimeField(_("Date de reponse"), null=True, blank=True)

    def __str__(self):
        return f"{self.sujet} - {self.client}"

    class Meta:
        verbose_name = _("Plainte")
        verbose_name_plural = _("Plaintes")
        ordering = ['-date_creation']
