"""
Tests d'etancheite de l'API mobile : un voyageur a UN compte et une fiche par compagnie ;
une compagnie ne voit jamais les donnees d'une autre.

Lancer :  python manage.py test transport.tests_api_isolation
"""
import datetime

from django.contrib.auth.models import User
from rest_framework.test import APIClient
from django.test import TestCase

from .models import Client, Employe, Plainte, Reservation, Siege
from .tests_isolation import construire_monde


class ApiIsolationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.A = construire_monde('aa', 'Alpha')
        cls.B = construire_monde('bb', 'Beta')

    def api(self, user=None, compagnie=None):
        c = APIClient()
        if user is not None:
            c.force_authenticate(user)
        if compagnie is not None:
            c.credentials(HTTP_X_COMPAGNIE=compagnie)
        return c

    def voyageur(self, nom='voyageur1'):
        return User.objects.create_user(nom, email=nom + '@test.td', password='secret1')

    # --- listes publiques : chaque compagnie voit les siennes
    def test_listes_publiques_par_compagnie(self):
        for code, mon, autre in (('aa', self.A, self.B), ('bb', self.B, self.A)):
            c = self.api(compagnie=code)
            ids = {v['id'] for v in c.get('/api/voyages/').json()}
            self.assertEqual(ids, {mon['voyage'].pk}, f"/api/voyages/ pour {code}")
            noms = {a['nom'] for a in c.get('/api/agences/').json()}
            self.assertTrue(noms.issuperset({mon['agence'].nom}) and autre['agence'].nom not in noms)
            titres = {p['titre'] for p in c.get('/api/promotions/').json()}
            self.assertEqual(titres, {mon['promotion'].titre})
            questions = {q['question'] for q in c.get('/api/faq/').json()}
            self.assertEqual(questions, {mon['faq'].question})

    def test_sans_en_tete_premiere_compagnie_et_code_inconnu(self):
        c = self.api()
        ids = {v['id'] for v in c.get('/api/voyages/').json()}
        self.assertEqual(ids, {self.A['voyage'].pk})            # ancienne application : premiere compagnie
        self.assertEqual(self.api(compagnie='nexiste-pas').get('/api/voyages/').status_code, 404)

    def test_liste_des_compagnies(self):
        codes = {c['code'] for c in self.api().get('/api/compagnies/').json()}
        self.assertTrue({'aa', 'bb'} <= codes)

    # --- un compte, une fiche par compagnie
    def test_compte_unique_une_fiche_par_compagnie(self):
        u = self.voyageur()
        self.assertEqual(self.api(u, 'aa').post('/api/rejoindre-compagnie/').status_code, 201)
        self.assertEqual(self.api(u, 'bb').post('/api/rejoindre-compagnie/').status_code, 201)
        self.api(u, 'aa').post('/api/rejoindre-compagnie/')      # idempotent
        fiches = Client.objects.filter(user=u)
        self.assertEqual(fiches.count(), 2)
        self.assertEqual({f.compagnie.code for f in fiches}, {'aa', 'bb'})
        codes = {c['code'] for c in self.api(u).get('/api/mes-compagnies/').json()}
        self.assertEqual(codes, {'aa', 'bb'})

    def test_billets_separes_par_compagnie(self):
        u = self.voyageur()
        piece = {'type_piece': 'cni', 'numero_piece': '1234567890', 'nom': 'Moi', 'telephone': '66000000'}
        r = self.api(u, 'aa').post('/api/reserver-siege/', {'voyage_id': self.A['voyage'].pk, 'numero_siege': 2, **piece}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(len(self.api(u, 'aa').get('/api/mes-billets/').json()), 1)
        self.assertEqual(len(self.api(u, 'bb').get('/api/mes-billets/').json()), 0)      # invisible chez B
        # reserver un voyage de B en se declarant chez A : refuse
        r = self.api(u, 'aa').post('/api/reserver-siege/', {'voyage_id': self.B['voyage'].pk, 'numero_siege': 2, **piece}, format='json')
        self.assertEqual(r.status_code, 404)
        self.assertFalse(Reservation.objects.filter(voyage=self.B['voyage'], voyageur_nom='Moi').exists())
        # le billet cree appartient bien a la compagnie A
        self.assertEqual(Reservation.objects.get(voyageur_nom='Moi').client.compagnie_id, self.A['compagnie'].pk)

    def test_sieges_suivi_et_positions_de_l_autre_compagnie_refuses(self):
        c = self.api(compagnie='aa')
        B = self.B
        self.assertEqual(c.get(f"/api/voyage/{B['voyage'].pk}/sieges/").status_code, 404)
        self.assertEqual(c.get(f"/api/voyage/{B['voyage'].pk}/positions/").status_code, 404)
        self.assertEqual(c.get(f"/api/voyage/{B['voyage'].pk}/historique-positions/").status_code, 404)
        self.assertEqual(c.get(f"/api/colis/{B['colis'].code_suivi}/").status_code, 404)
        self.assertEqual(c.get(f"/api/transfert/{B['transfert'].code_transfert}/").status_code, 404)
        # et chez soi, ca marche
        self.assertEqual(c.get(f"/api/voyage/{self.A['voyage'].pk}/sieges/").status_code, 200)

    def test_inscription_dans_une_compagnie_meme_telephone_autorise_ailleurs(self):
        donnees = {'username': 'nouveau1', 'email': 'nouveau1@test.td', 'telephone': '66112233', 'password': 'secret1'}
        r = self.api(compagnie='aa').post('/api/inscription/', donnees, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        fiche = Client.objects.get(user__username='nouveau1')
        self.assertEqual(fiche.compagnie.code, 'aa')
        # meme numero dans la meme compagnie : refuse ; chez B (autre compte) : accepte
        r = self.api(compagnie='aa').post('/api/inscription/', dict(donnees, username='nouveau2', email='n2@test.td'), format='json')
        self.assertEqual(r.status_code, 400)
        r = self.api(compagnie='bb').post('/api/inscription/', dict(donnees, username='nouveau3', email='n3@test.td'), format='json')
        self.assertEqual(r.status_code, 201, r.content)

    def test_demande_colis_avec_agences_d_une_autre_compagnie_refusee(self):
        u = self.voyageur()
        donnees = {
            'expediteur_nom': 'E', 'expediteur_telephone': '66000001', 'destinataire_nom': 'D', 'destinataire_telephone': '66000002',
            'expediteur_type_piece': 'cni', 'expediteur_numero_piece': '1', 'destinataire_type_piece': 'cni', 'destinataire_numero_piece': '2',
            'agence_depart': self.B['agence'].pk, 'agence_arrivee': self.B['agence2'].pk, 'description': 'x', 'poids_estime': 1,
        }
        r = self.api(u, 'aa').post('/api/demande-colis/', donnees, format='json')
        self.assertEqual(r.status_code, 404)

    def test_plainte_rattachee_a_la_bonne_compagnie(self):
        u = self.voyageur()
        self.api(u, 'bb').post('/api/rejoindre-compagnie/')
        r = self.api(u, 'bb').post('/api/plainte/', {'sujet': 's', 'message': 'm'}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        p = Plainte.objects.get(pk=r.json()['id'])
        self.assertEqual(p.compagnie.code, 'bb')
        self.assertEqual(len(self.api(u, 'aa').get('/api/mes-plaintes/').json()), 0)

    def test_scan_securite_limite_a_sa_compagnie(self):
        user = User.objects.create_user('secu_a', password='x')
        Employe.objects.create(user=user, compagnie=self.A['compagnie'], agence=self.A['agence'], nom='S', prenom='A', telephone='1', poste='securite')
        numero = self.B['reservation'].numero_reservation
        r = self.api(user).post('/api/securite/scanner-billet/', {'numero_reservation': numero}, format='json')
        self.assertEqual(r.status_code, 404)
        self.assertFalse(Reservation.objects.get(pk=self.B['reservation'].pk).embarque)
