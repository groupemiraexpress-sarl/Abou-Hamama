"""Tests de la console plateforme (superutilisateur) : creer, reinitialiser, suspendre une entreprise."""
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from .models import Compagnie, Employe
from .tenant import limiter_a_compagnie
from .models import Voyage
from .tests_isolation import construire_monde, creer_employe

H = {'HTTP_HOST': 'localhost'}
DONNEES = {
    'nom': 'Ben Siam', 'code': 'bs', 'siege': 'Moundou', 'telephone': '60000000', 'couleur': '#aa0000',
    'pdg_nom': 'Siam', 'pdg_prenom': 'Ben', 'pdg_telephone': '66554433',
}


@override_settings(ALLOWED_HOSTS=['*'])
class ConsolePlateformeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.A = construire_monde('aa', 'Alpha')
        cls.B = construire_monde('bb', 'Beta')
        cls.su = User.objects.create_superuser('plateforme', password='x')
        cls.pdg_a, _e = creer_employe(cls.A, 'pdg', agence=False)

    def test_reserve_au_superutilisateur(self):
        self.client.force_login(self.pdg_a)
        for url in ('/espace/plateforme/', '/espace/plateforme/nouvelle/'):
            r = self.client.get(url, **H)
            self.assertEqual(r.status_code, 302, url)
        r = self.client.post('/espace/plateforme/nouvelle/', DONNEES, **H)
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Compagnie.objects.filter(code='bs').exists())
        cid = self.B['compagnie'].pk
        self.client.post(f'/espace/plateforme/{cid}/basculer/', **H)
        self.client.post(f'/espace/plateforme/{cid}/reinitialiser-pdg/', **H)
        self.assertTrue(Compagnie.objects.get(pk=cid).actif)

    def test_liste_avec_chiffres_par_entreprise(self):
        self.client.force_login(self.su)
        r = self.client.get('/espace/plateforme/', **H)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Alpha')
        self.assertContains(r, 'Beta')
        self.assertContains(r, 'Reinitialiser le PDG')

    def test_creation_par_formulaire(self):
        self.client.force_login(self.su)
        self.assertEqual(self.client.get('/espace/plateforme/nouvelle/', **H).status_code, 200)
        r = self.client.post('/espace/plateforme/nouvelle/', DONNEES, **H)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'bs.66554433')
        compagnie = Compagnie.objects.get(code='bs')
        self.assertEqual(compagnie.couleur_principale, '#aa0000')
        # le mot de passe affiche permet de se connecter, et le PDG ne voit que sa compagnie
        mot_de_passe = r.context['mot_de_passe']
        pdg = authenticate(username='bs.66554433', password=mot_de_passe)
        self.assertIsNotNone(pdg)
        self.assertEqual(Employe.objects.get(user=pdg).poste, 'pdg')
        self.assertEqual(limiter_a_compagnie(Voyage.objects.all(), pdg).count(), 0)

    def test_erreurs_de_saisie(self):
        self.client.force_login(self.su)
        r = self.client.post('/espace/plateforme/nouvelle/', dict(DONNEES, code='aa'), **H)      # code deja pris
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Compagnie.objects.filter(nom='Ben Siam').exists())
        self.assertIn('code', r.context['erreurs'])
        r = self.client.post('/espace/plateforme/nouvelle/', dict(DONNEES, nom=''), **H)        # champ manquant
        self.assertIn('nom', r.context['erreurs'])
        r = self.client.post('/espace/plateforme/nouvelle/', dict(DONNEES, couleur='rouge'), **H)
        self.assertIn('couleur_principale', r.context['erreurs'])
        self.assertEqual(Compagnie.objects.filter(code='bs').count(), 0)

    def test_reinitialiser_le_pdg(self):
        self.client.force_login(self.su)
        pdg_b, _e = creer_employe(self.B, 'pdg', agence=False)
        pdg_b.set_password('ancien-mot-de-passe')
        pdg_b.save()
        r = self.client.post(f"/espace/plateforme/{self.B['compagnie'].pk}/reinitialiser-pdg/", **H)
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(authenticate(username=pdg_b.username, password='ancien-mot-de-passe'))
        self.assertIsNotNone(authenticate(username=pdg_b.username, password=r.context['mot_de_passe']))
        # entreprise sans PDG : message d'erreur
        sans_pdg = Compagnie.objects.create(code='zz', nom='Zed', siege_social='x', telephone='1')
        r = self.client.post(f'/espace/plateforme/{sans_pdg.pk}/reinitialiser-pdg/', **H, follow=True)
        self.assertContains(r, "pas de PDG")

    def test_suspension_et_reactivation(self):
        pdg_b, _e = creer_employe(self.B, 'pdg', agence=False)
        cid = self.B['compagnie'].pk
        su = self.client_class()
        su.force_login(self.su)
        su.post(f'/espace/plateforme/{cid}/basculer/', **H)
        self.assertFalse(Compagnie.objects.get(pk=cid).actif)
        # l'employe de la compagnie suspendue est renvoye a la connexion
        self.client.force_login(pdg_b)
        r = self.client.get('/admin/', **H)
        self.assertEqual(r.status_code, 302)
        self.assertIn('/admin/login/', r['Location'])
        # l'application mobile ne la voit plus
        self.assertEqual(self.client.get('/api/voyages/', HTTP_X_COMPAGNIE='bb', **H).status_code, 404)
        self.assertNotIn('bb', {c['code'] for c in self.client.get('/api/compagnies/', **H).json()})
        # l'autre compagnie n'est pas touchee
        self.client.force_login(self.pdg_a)
        self.assertEqual(self.client.get('/admin/', **H).status_code, 200)
        # reactivation
        su.post(f'/espace/plateforme/{cid}/basculer/', **H)
        self.assertTrue(Compagnie.objects.get(pk=cid).actif)
        self.client.force_login(pdg_b)
        self.assertEqual(self.client.get('/admin/', **H).status_code, 200)

    def test_impossible_de_suspendre_la_derniere_entreprise_active(self):
        Compagnie.objects.filter(code='bb').update(actif=False)
        self.client.force_login(self.su)
        self.client.post(f"/espace/plateforme/{self.A['compagnie'].pk}/basculer/", **H)
        self.assertTrue(Compagnie.objects.get(code='aa').actif)


@override_settings(ALLOWED_HOSTS=['*'])
class TableauDeBordSuperviseurTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.A = construire_monde('aa', 'Alpha')
        cls.B = construire_monde('bb', 'Beta')
        cls.su = User.objects.create_superuser('plateforme', password='x')
        cls.pdg_a, _e = creer_employe(cls.A, 'pdg', agence=False)

    def test_le_superviseur_voit_la_vue_d_ensemble_pas_les_chiffres_d_une_agence(self):
        self.client.force_login(self.su)
        r = self.client.get('/admin/', **H)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Vue d'ensemble de la plateforme")
        self.assertContains(r, 'Alpha')
        self.assertContains(r, 'Beta')
        self.assertContains(r, 'Creer une entreprise')
        self.assertNotContains(r, '/espace/vendre-billet/')
        self.assertNotContains(r, 'Voyages du jour')
        self.assertEqual(r.context['vue_plateforme']['totaux']['actives'], 2)

    def test_le_pdg_garde_son_tableau_de_bord_d_agence(self):
        self.client.force_login(self.pdg_a)
        r = self.client.get('/admin/', **H)
        self.assertContains(r, 'Voyages du jour')
        self.assertNotContains(r, "Vue d'ensemble de la plateforme")
        self.assertNotContains(r, 'Plateforme (entreprises)')
