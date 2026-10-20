"""
Tests de la marque par compagnie, des adresses web par compagnie et de la creation d'une compagnie.

Lancer :  python manage.py test transport.tests_marque
"""
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings

from .models import Compagnie, Employe
from .tests_isolation import construire_monde, creer_employe

REGLAGES = dict(PLATEFORME_DOMAINE='plateforme.test', ALLOWED_HOSTS=['*'])


@override_settings(**REGLAGES)
class MarqueEtDomaineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.A = construire_monde('aa', 'Alpha')
        cls.B = construire_monde('bb', 'Beta')
        Compagnie.objects.filter(code='bb').update(nom_affiche='Beta Voyages Express', couleur_principale='#112233', domaine='gestion.beta.test',
                                                    slogan='Le voyage Beta', pied_de_page='Siege Beta')

    def page(self, hote, url='/admin/login/'):
        return self.client.get(url, HTTP_HOST=hote)

    def test_marque_selon_le_sous_domaine(self):
        beta = self.page('bb.plateforme.test').content.decode()
        self.assertIn('Beta Voyages Express', beta)
        self.assertIn('#112233', beta)
        self.assertNotIn('Alpha', beta)
        alpha = self.page('aa.plateforme.test').content.decode()
        self.assertIn('Alpha', alpha)
        self.assertNotIn('Beta Voyages Express', alpha)
        self.assertNotIn('#112233', alpha)

    def test_marque_selon_le_domaine_propre(self):
        self.assertIn('Beta Voyages Express', self.page('gestion.beta.test').content.decode())

    def test_logo_par_defaut_initiales_et_logo_historique(self):
        beta = self.page('bb.plateforme.test').content.decode()
        self.assertIn('data:image/svg+xml', beta)          # pastille avec les initiales (pas de logo envoye)
        alpha = self.page('aa.plateforme.test').content.decode()
        self.assertIn('logo_abou_hamama', alpha)           # premiere compagnie : logo d'origine

    def test_employe_deconnecte_s_il_visite_le_site_d_une_autre_compagnie(self):
        pdg_a, _e = creer_employe(self.A, 'pdg', agence=False)
        self.client.force_login(pdg_a)
        # sur son propre site : connecte
        self.assertEqual(self.client.get('/admin/', HTTP_HOST='aa.plateforme.test').status_code, 200)
        # sur le site de B : deconnecte et renvoye a la connexion
        r = self.client.get('/admin/', HTTP_HOST='bb.plateforme.test')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/admin/login/', r['Location'])
        self.assertEqual(self.client.get('/admin/', HTTP_HOST='aa.plateforme.test').status_code, 302)   # plus connecte

    def test_superutilisateur_peut_se_connecter_partout(self):
        su = User.objects.create_superuser('plateforme', password='x')
        self.client.force_login(su)
        self.assertEqual(self.client.get('/admin/', HTTP_HOST='bb.plateforme.test').status_code, 200)

    def test_api_sans_en_tete_utilise_l_adresse_web(self):
        r = self.client.get('/api/voyages/', HTTP_HOST='bb.plateforme.test')
        self.assertEqual({v['id'] for v in r.json()}, {self.B['voyage'].pk})
        r = self.client.get('/api/voyages/', HTTP_HOST='aa.plateforme.test')
        self.assertEqual({v['id'] for v in r.json()}, {self.A['voyage'].pk})
        # l'en-tete explicite reste prioritaire
        r = self.client.get('/api/voyages/', HTTP_HOST='aa.plateforme.test', HTTP_X_COMPAGNIE='bb')
        self.assertEqual({v['id'] for v in r.json()}, {self.B['voyage'].pk})

    def test_adresse_inconnue_avec_plusieurs_compagnies_marque_neutre(self):
        page = self.page('localhost').content.decode()
        self.assertNotIn('Alpha', page)
        self.assertNotIn('Beta', page)
        self.assertIn('MIRA Transport Platform', page)
        self.assertIn('transport/logo_mira_embleme.png', page)
        self.assertNotIn('logo_abou_hamama', page)

    def test_adresse_inconnue_avec_une_seule_compagnie_garde_sa_marque(self):
        Compagnie.objects.filter(code='bb').update(actif=False)
        self.assertIn('Alpha', self.page('localhost').content.decode())


@override_settings(**REGLAGES)
class AdministrationCompagnieTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.A = construire_monde('aa', 'Alpha')
        cls.B = construire_monde('bb', 'Beta')
        cls.pdg_a, _e = creer_employe(cls.A, 'pdg', agence=False)
        cls.su = User.objects.create_superuser('plateforme', password='x')

    def test_le_pdg_ne_voit_que_sa_compagnie_et_ne_peut_ni_creer_ni_supprimer(self):
        self.client.force_login(self.pdg_a)
        r = self.client.get('/admin/transport/compagnie/', HTTP_HOST='localhost')
        contenu = r.content.decode()
        self.assertIn('Alpha', contenu)
        self.assertNotIn('Beta', contenu)
        self.assertNotEqual(self.client.get('/admin/transport/compagnie/add/', HTTP_HOST='localhost').status_code, 200)
        self.client.post(f"/admin/transport/compagnie/{self.A['compagnie'].pk}/delete/", {'post': 'yes'}, HTTP_HOST='localhost')
        self.assertTrue(Compagnie.objects.filter(pk=self.A['compagnie'].pk).exists())

    def test_le_pdg_ne_change_ni_le_code_ni_l_adresse_web(self):
        self.client.force_login(self.pdg_a)
        r = self.client.get(f"/admin/transport/compagnie/{self.A['compagnie'].pk}/change/", HTTP_HOST='localhost')
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('name="code"', r.content.decode())
        self.assertNotIn('name="domaine"', r.content.decode())
        self.assertNotEqual(self.client.get(f"/admin/transport/compagnie/{self.B['compagnie'].pk}/change/", HTTP_HOST='localhost').status_code, 200)

    def test_commande_creer_compagnie(self):
        sortie = StringIO()
        call_command('creer_compagnie', nom='Ben Siam', code='bs', siege='Moundou', telephone='60000000', pdg_nom='Siam',
                     pdg_prenom='Ben', pdg_telephone='66554433', couleur='#aa0000', stdout=sortie)
        c = Compagnie.objects.get(code='bs')
        pdg = Employe.objects.get(compagnie=c, poste='pdg')
        self.assertEqual(pdg.user.username, 'bs.66554433')
        self.assertIn('mot de passe temporaire', sortie.getvalue())
        # le PDG de la nouvelle compagnie ne voit rien des autres
        from .tenant import limiter_a_compagnie
        from .models import Voyage
        self.assertEqual(limiter_a_compagnie(Voyage.objects.all(), pdg.user).count(), 0)
        # le meme code ne peut pas etre reutilise
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            call_command('creer_compagnie', nom='Autre', code='bs', siege='x', telephone='1', pdg_nom='a', pdg_prenom='b', pdg_telephone='66554434')


@override_settings(**REGLAGES)
class MarqueApresConnexionTests(TestCase):
    def test_l_employe_connecte_voit_la_marque_de_sa_compagnie_meme_sans_adresse_propre(self):
        A = construire_monde('aa', 'Alpha')
        B = construire_monde('bb', 'Beta')
        Compagnie.objects.filter(code='bb').update(nom_affiche='Beta Voyages Express', couleur_principale='#0a7d4b')
        pdg_b, _e = creer_employe(B, 'pdg', agence=False)
        self.client.force_login(pdg_b)
        page = self.client.get('/admin/', HTTP_HOST='localhost').content.decode()
        self.assertIn('Beta Voyages Express', page)
        self.assertIn('#0a7d4b', page)
        self.assertNotIn('Alpha', page)
