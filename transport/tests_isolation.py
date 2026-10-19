"""
Tests d'ETANCHEITE entre entreprises : une compagnie ne doit JAMAIS voir, modifier
ni supprimer les donnees d'une autre, ni dans l'admin, ni dans les pages, ni dans l'API.

Lancer :  python manage.py test transport.tests_isolation
"""
import datetime

from django.contrib import admin
from django.contrib.auth.models import Permission, User
from django.test import TestCase

from .models import (
    Agence, AlerteVoyage, ArticleStock, AvisVoyage, Bus, Chauffeur, Client, Colis, Commissionnaire,
    Compagnie, Depense, DemandeColis, DemandeMateriel, DemandeTransfert, Employe, Entretien, Ligne,
    MouvementCaisse, PleinCarburant, Plainte, PositionBus, Promotion, QuestionFAQ, Reservation,
    SessionCaisse, Siege, TransfertArgent, Trajet, Voyage, ArretLigne,
)
from .tenant import CHEMINS_COMPAGNIE

H = {'HTTP_HOST': 'localhost'}


def construire_monde(code, nom):
    """Cree une compagnie complete avec des donnees dans (presque) chaque table. Renvoie un dict d'objets."""
    comp = Compagnie.objects.create(code=code, nom=nom, siege_social='Siege ' + nom, telephone='1')
    mt = {}
    mt['compagnie'] = comp
    ag = Agence.objects.create(compagnie=comp, nom='Agence ' + nom, ville='Ville' + code, adresse='a', telephone='1')
    ag2 = Agence.objects.create(compagnie=comp, nom='Agence 2 ' + nom, ville='Ville2' + code, adresse='a', telephone='1')
    bus = Bus.objects.create(compagnie=comp, agence=ag, immatriculation='BUS-' + code, marque='M', capacite=10)
    ch = Chauffeur.objects.create(compagnie=comp, agence=ag, nom='Ch' + code, prenom='P', telephone='1', numero_permis='PERMIS-' + code)
    tr = Trajet.objects.create(compagnie=comp, ville_depart='A' + code, ville_arrivee='B' + code, distance_km=100, duree_estimee_heures=2, prix_base=1000)
    voy = Voyage.objects.create(trajet=tr, bus=bus, chauffeur=ch, date_depart=datetime.date.today() + datetime.timedelta(days=2),
                                heure_depart=datetime.time(8, 0), prix=1000, places_disponibles=10)
    cl = Client.objects.create(compagnie=comp, nom='Client' + code, telephone='600')   # MEME telephone dans les 2 compagnies
    res = Reservation.objects.create(client=cl, voyage=voy, siege=Siege.objects.get(voyage=voy, numero=1), agence=ag,
                                     voyageur_nom='V' + code, voyageur_telephone='600', voyageur_type_piece='cni',
                                     voyageur_numero_piece='1234567890', statut='payee', mode_paiement='especes')
    colis = Colis.objects.create(compagnie=comp, expediteur_nom='E' + code, expediteur_telephone='1', destinataire_nom='D',
                                 destinataire_telephone='2', agence_depart=ag, agence_arrivee=ag2, description='x', poids_kg=1, prix=5)
    tf = TransfertArgent.objects.create(compagnie=comp, expediteur_nom='E' + code, expediteur_telephone='1', beneficiaire_nom='B',
                                        beneficiaire_telephone='2', agence_depart=ag, agence_retrait=ag2, montant=10)
    art = ArticleStock.objects.create(compagnie=comp, nom='Huile', quantite_stock=10, prix_unitaire=100)   # MEME nom dans les 2 compagnies
    mt.update(agence=ag, agence2=ag2, bus=bus, chauffeur=ch, trajet=tr, voyage=voy, client=cl, reservation=res, colis=colis,
              transfert=tf, article=art)
    mt['demande_materiel'] = DemandeMateriel.objects.create(bus=bus, article=art, quantite=1)
    mt['entretien'] = Entretien.objects.create(bus=bus, type_entretien='vidange', date_entretien=datetime.date.today())
    mt['plein'] = PleinCarburant.objects.create(bus=bus, date_plein=datetime.date.today(), montant=100)
    mt['promotion'] = Promotion.objects.create(compagnie=comp, titre='Promo' + code, texte='t', date_debut=datetime.date.today(), date_fin=datetime.date.today())
    mt['faq'] = QuestionFAQ.objects.create(compagnie=comp, question='Q' + code, reponse='R')
    mt['plainte'] = Plainte.objects.create(compagnie=comp, client=cl, sujet='S', message='M')
    mt['commissionnaire'] = Commissionnaire.objects.create(agence=ag, nom='Comm' + code)
    mt['depense'] = Depense.objects.create(voyage=voy, libelle='Eau', montant=10)
    session = SessionCaisse.objects.create(agence=ag, fond_initial=0)
    mt['session'] = session
    mt['mouvement'] = MouvementCaisse.objects.create(session=session, type_mouvement='encaissement', montant=5, motif='m')
    mt['demande_colis'] = DemandeColis.objects.create(expediteur_nom='E', expediteur_telephone='1', destinataire_nom='D', destinataire_telephone='2',
                                                      agence_depart=ag, agence_arrivee=ag2, description='x', poids_estime=1)
    mt['demande_transfert'] = DemandeTransfert.objects.create(expediteur_nom='E', expediteur_telephone='1', beneficiaire_nom='B',
                                                              beneficiaire_telephone='2', agence_depart=ag, agence_retrait=ag2, montant=10)
    mt['alerte'] = AlerteVoyage.objects.create(voyage=voy, message='m')
    mt['position'] = PositionBus.objects.create(voyage=voy, latitude=1, longitude=1)
    mt['avis'] = AvisVoyage.objects.create(reservation=res, client=cl, chauffeur=ch, voyage=voy, note=5)
    ligne = Ligne.objects.create(compagnie=comp, nom='Ligne' + code)
    mt['ligne'] = ligne
    mt['arret'] = ArretLigne.objects.create(ligne=ligne, agence=ag, ordre=1)
    return mt


def creer_employe(mt, poste, agence=True):
    comp = mt['compagnie']
    u = User.objects.create_user(f"{comp.code}.{poste}", password='x', is_staff=True)
    e = Employe.objects.create(user=u, compagnie=comp, agence=mt['agence'] if agence else None, nom='N', prenom=poste,
                               telephone='1', poste=poste)
    u.user_permissions.set(Permission.objects.filter(content_type__app_label='transport'))
    return u, e


class IsolationAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.A = construire_monde('aa', 'Alpha')
        cls.B = construire_monde('bb', 'Beta')
        cls.pdg_a, _e = creer_employe(cls.A, 'pdg', agence=False)
        cls.pdg_b, _e = creer_employe(cls.B, 'pdg', agence=False)
        cls.resp_a, _e = creer_employe(cls.A, 'responsable')
        cls.magasinier_a, _e = creer_employe(cls.A, 'magasinier', agence=False)
        cls.superuser = User.objects.create_superuser('plateforme', password='x')

    def client_de(self, user):
        self.client.force_login(user)
        return self.client

    # --- 1) listes de l'admin : jamais d'objet d'une autre compagnie
    def test_listes_admin_ne_montrent_que_sa_compagnie(self):
        for modele, ma in admin.site._registry.items():
            label = modele._meta.label_lower
            if label not in CHEMINS_COMPAGNIE or label in ('transport.compagnie', 'auth.user'):
                continue
            for user in (self.pdg_a, self.resp_a):
                req = type('R', (), {'user': user})()
                visibles = set(ma.get_queryset(req).values_list('pk', flat=True))
                autres = set(modele._default_manager.exclude(
                    pk__in=__import__('transport.tenant', fromlist=['x']).limiter_a_compagnie(modele._default_manager.all(), user)
                ).values_list('pk', flat=True))
                self.assertFalse(visibles & autres, f"{label} : {user.username} voit des objets d'une autre compagnie")

    # --- 2) comptage direct : B n'apparait jamais pour A
    def test_objets_de_b_invisibles_pour_a(self):
        from .tenant import limiter_a_compagnie
        B = self.B
        for cle, obj in B.items():
            if cle == 'compagnie':
                continue
            qs = limiter_a_compagnie(type(obj)._default_manager.all(), self.pdg_a)
            self.assertFalse(qs.filter(pk=obj.pk).exists(), f"{cle} de B visible par le PDG de A")
        # et inversement ceux de A sont visibles par A
        for cle, obj in self.A.items():
            if cle == 'compagnie':
                continue
            qs = limiter_a_compagnie(type(obj)._default_manager.all(), self.pdg_a)
            self.assertTrue(qs.filter(pk=obj.pk).exists(), f"{cle} de A introuvable par le PDG de A")

    # --- 3) acces direct par adresse a une fiche de B
    def test_acces_direct_fiche_autre_compagnie_refuse(self):
        c = self.client_de(self.pdg_a)
        for cle, obj in self.B.items():
            if cle == 'compagnie':
                continue
            m = type(obj)._meta
            if m.label_lower not in CHEMINS_COMPAGNIE:
                continue
            url = f"/admin/{m.app_label}/{m.model_name}/{obj.pk}/change/"
            r = c.get(url, **H)
            self.assertNotEqual(r.status_code, 200, f"PDG de A ouvre {url} (fiche de B)")
            r = c.post(f"/admin/{m.app_label}/{m.model_name}/{obj.pk}/delete/", {'post': 'yes'}, **H)
            self.assertTrue(type(obj)._default_manager.filter(pk=obj.pk).exists(), f"PDG de A a supprime {cle} de B")

    # --- 4) listes deroulantes (formulaires d'ajout) : pas d'options de B
    def test_listes_deroulantes_sans_donnees_de_b(self):
        c = self.client_de(self.pdg_a)
        interdits = {
            '/admin/transport/voyage/add/': [('voyage', 'trajet', self.B['trajet']), ('voyage', 'bus', self.B['bus']), ('voyage', 'chauffeur', self.B['chauffeur'])],
            '/admin/transport/reservation/add/': [('reservation', 'voyage', self.B['voyage']), ('reservation', 'client', self.B['client']), ('reservation', 'agence', self.B['agence'])],
            '/admin/transport/colis/add/': [('colis', 'agence_arrivee', self.B['agence2']), ('colis', 'agence_depart', self.B['agence'])],
            '/admin/transport/transfertargent/add/': [('t', 'agence_retrait', self.B['agence2'])],
            '/admin/transport/employe/add/': [('e', 'agence', self.B['agence']), ('e', 'compagnie', self.B['compagnie'])],
            '/admin/transport/demandemateriel/add/': [('d', 'bus', self.B['bus']), ('d', 'article', self.B['article'])],
        }
        import re
        for url, cas in interdits.items():
            r = c.get(url, **H)
            self.assertEqual(r.status_code, 200, url)
            html = r.content.decode()
            for _x, champ, obj in cas:
                m = re.search(r'<select name="%s"[^>]*>(.*?)</select>' % champ, html, re.S)
                if not m:
                    continue
                valeurs = re.findall(r'<option value="(\d+)"', m.group(1))
                self.assertNotIn(str(obj.pk), valeurs, f"{url} : la liste '{champ}' propose un objet de la compagnie B")

    # --- 5) creation : la compagnie est imposee cote serveur
    def test_creation_force_la_compagnie_de_l_utilisateur(self):
        c = self.client_de(self.pdg_a)
        donnees = {'nom': 'Pneu', 'unite': 'piece', 'quantite_stock': 5, 'seuil_alerte': 1, 'prix_unitaire': 10, 'actif': 'on'}
        # tentative de se rattacher a la compagnie B : refusee ou ramenee a A, jamais creee chez B
        c.post('/admin/transport/articlestock/add/', dict(donnees, compagnie=self.B['compagnie'].pk), **H)
        self.assertFalse(ArticleStock.objects.filter(nom='Pneu', compagnie=self.B['compagnie']).exists(), "article cree chez B par le PDG de A")
        # creation normale (sans rien indiquer) : rattachee a la compagnie de l'utilisateur
        c.post('/admin/transport/articlestock/add/', donnees, **H)
        article = ArticleStock.objects.filter(nom='Pneu').first()
        self.assertIsNotNone(article)
        self.assertEqual(article.compagnie_id, self.A['compagnie'].pk)

    # --- 6) le superutilisateur voit tout (administrateur de la plateforme)
    def test_superutilisateur_voit_toutes_les_compagnies(self):
        from .tenant import limiter_a_compagnie
        total = Voyage.objects.count()
        self.assertEqual(limiter_a_compagnie(Voyage.objects.all(), self.superuser).count(), total)
        self.assertGreaterEqual(total, 2)

    # --- 7) le meme telephone / meme nom d'article peut exister dans deux compagnies
    def test_doublons_autorises_entre_compagnies(self):
        self.assertEqual(Client.objects.filter(telephone='600').count(), 2)
        self.assertEqual(ArticleStock.objects.filter(nom='Huile').count(), 2)

    # --- 8) un PDG par compagnie
    def test_un_pdg_par_compagnie(self):
        self.assertEqual(Employe.objects.filter(poste='pdg').count(), 2)

    # --- 9) un employe sans fiche employe ne voit rien
    def test_compte_sans_fiche_employe_ne_voit_rien(self):
        from .tenant import limiter_a_compagnie
        orphelin = User.objects.create_user('orphelin', password='x', is_staff=True)
        for cle, obj in self.A.items():
            if cle == 'compagnie':
                continue
            self.assertFalse(limiter_a_compagnie(type(obj)._default_manager.all(), orphelin).exists(), cle)


class IsolationPagesTests(TestCase):
    """Pages personnalisees (hors admin) : le PDG de A ne voit rien de B, meme en devinant les numeros."""

    @classmethod
    def setUpTestData(cls):
        cls.A = construire_monde('aa', 'Alpha')
        cls.B = construire_monde('bb', 'Beta')
        cls.pdg_a, _e = creer_employe(cls.A, 'pdg', agence=False)
        cls.guichet_a, _e = creer_employe(cls.A, 'guichetier')
        cls.mag_a, _e = creer_employe(cls.A, 'magasinier', agence=False)

    def get(self, user, url):
        self.client.force_login(user)
        return self.client.get(url, **H)

    def test_pages_par_numero_ne_montrent_rien_de_b(self):
        B = self.B
        urls = [
            f"/espace/billet/{B['reservation'].pk}/", f"/espace/billets-confirmes/?ids={B['reservation'].pk}",
            f"/espace/billet/{B['reservation'].pk}/modifier/", f"/espace/recu-colis/{B['colis'].pk}/",
            f"/espace/recu-transfert/{B['transfert'].pk}/", f"/espace/recu-demande-materiel/{B['demande_materiel'].pk}/",
            f"/espace/voyage/{B['voyage'].pk}/plan/", f"/espace/voyage/{B['voyage'].pk}/depenses/",
            f"/espace/voyage/{B['voyage'].pk}/changer-bus/", f"/espace/voyage/{B['voyage'].pk}/feuille-chauffeur/",
            f"/espace/rapport-agence/?agence={B['agence'].pk}", f"/espace/rapport-finances/?agence={B['agence'].pk}",
            f"/espace/rapport-maintenance/?agence={B['agence'].pk}", f"/espace/rapport-mon-agence/?agence={B['agence'].pk}",
            f"/espace/caisse/?agence={B['agence'].pk}", f"/espace/manifeste-bord/?voyage={B['voyage'].pk}",
            f"/espace/historique-employe/?employe={B['agence'].pk}",
        ]
        secrets = ['Vbb', 'Ebb', 'Alpha' if False else 'Beta', 'BUS-bb', 'Chbb', 'Clientbb', 'Commbb', 'Agence Beta', 'Abb', 'Bbb', 'PERMIS-bb']
        for user in (self.pdg_a, self.guichet_a, self.mag_a):
            for url in urls:
                r = self.get(user, url)
                contenu = r.content.decode(errors='ignore')
                for mot in secrets:
                    self.assertNotIn(mot, contenu, f"{user.username} voit '{mot}' (donnee de B) sur {url}")

    def test_pages_donnent_les_donnees_de_a(self):
        A = self.A
        r = self.get(self.pdg_a, f"/espace/billets-confirmes/?ids={A['reservation'].pk}")
        self.assertContains(r, 'Vaa')
        r = self.get(self.pdg_a, f"/espace/recu-colis/{A['colis'].pk}/")
        self.assertContains(r, 'Eaa')

    def test_listes_json_et_pages_sans_donnees_de_b(self):
        for url in ('/espace/liste-billets/', '/espace/dettes/', '/espace/caisse/', '/espace/vendre-billet/', '/espace/etat-stock/',
                    '/espace/tableau-pdg/', '/espace/carte-bus/', '/espace/historique-employe/', '/espace/manifeste-bord/',
                    '/espace/rapport-agence/', '/espace/rapport-finances/', '/espace/rapport-maintenance/', '/espace/rapport-mon-agence/'):
            r = self.get(self.pdg_a, url)
            self.assertIn(r.status_code, (200, 302), url)
            contenu = r.content.decode(errors='ignore')
            for mot in ('Vbb', 'BUS-bb', 'Agence Beta', 'Clientbb', 'Commbb'):
                self.assertNotIn(mot, contenu, f"{url} montre '{mot}'")

    def test_statistiques_tableau_de_bord_par_compagnie(self):
        from .admin_stats import statistiques_tableau_bord
        # chaque compagnie a : 1 client, 1 article ; le PDG de A ne compte que les siens
        stats = statistiques_tableau_bord(self.pdg_a)
        self.assertEqual(stats['total_clients'], 1)
        self.assertEqual(stats['total_articles_stock'], 1)
        self.assertEqual(stats['bus_service'], 1)

    def test_actions_sur_donnees_de_b_refusees(self):
        B = self.B
        # encaisser une dette de B
        Reservation.objects.filter(pk=B['reservation'].pk).update(statut='en_attente')
        self.client.force_login(self.pdg_a)
        self.client.post('/espace/dettes/', {'action': 'encaisser', 'id': B['reservation'].pk, 'mode_paiement': 'especes'}, **H)
        self.assertEqual(Reservation.objects.get(pk=B['reservation'].pk).statut, 'en_attente')
        # ajouter une depense a un voyage de B
        r = self.client.post(f"/espace/voyage/{B['voyage'].pk}/depenses/", {'action': 'ajouter', 'libelle': 'x', 'montant': 5}, **H)
        self.assertEqual(r.status_code, 404)
        self.assertEqual(Depense.objects.filter(voyage=B['voyage']).count(), 1)
        # changer le bus d'un voyage de B
        r = self.client.post(f"/espace/voyage/{B['voyage'].pk}/changer-bus/", {'bus_id': self.A['bus'].pk}, **H)
        self.assertNotEqual(r.status_code, 200)
        self.assertEqual(Voyage.objects.get(pk=B['voyage'].pk).bus_id, B['bus'].pk)


class NumerotationTests(TestCase):
    """Les numeros de billet, colis, transfert et demande ne se melangent pas entre compagnies."""

    def test_compteurs_independants_et_prefixes_par_compagnie(self):
        A = construire_monde('aa', 'Alpha')
        B = construire_monde('bb', 'Beta')
        self.assertTrue(A['reservation'].numero_reservation.startswith('RES-AA-'), A['reservation'].numero_reservation)
        self.assertTrue(B['reservation'].numero_reservation.startswith('RES-BB-'), B['reservation'].numero_reservation)
        # chacun commence a 0001 : B ne devine rien du volume de A
        self.assertTrue(A['reservation'].numero_reservation.endswith('-0001'))
        self.assertTrue(B['reservation'].numero_reservation.endswith('-0001'))
        self.assertTrue(B['colis'].code_suivi.startswith('COL-BB-') and B['colis'].code_suivi.endswith('-0001'))
        self.assertTrue(B['transfert'].code_transfert.startswith('TRF-BB-') and B['transfert'].code_transfert.endswith('-0001'))
        self.assertTrue(B['demande_colis'].numero_demande.startswith('DC-BB-'))
        self.assertTrue(B['demande_transfert'].numero_demande.startswith('DT-BB-'))
