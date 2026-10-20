"""Tests de l'interface : menu lateral selon le poste, couleurs et logo propres a chaque entreprise."""
from django.contrib.auth.models import Permission, User
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from .models import Compagnie, Employe
from .tests_isolation import construire_monde, creer_employe

H = {'HTTP_HOST': 'localhost'}


@override_settings(ALLOWED_HOSTS=['*'])
class MenuLateralTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.A = construire_monde('aa', 'Alpha')
        cls.B = construire_monde('bb', 'Beta')
        Compagnie.objects.filter(pk=cls.A['compagnie'].pk).update(couleur_principale='#123456', couleur_secondaire='#abcdef')
        Compagnie.objects.filter(pk=cls.B['compagnie'].pk).update(couleur_principale='#654321', couleur_secondaire='#fedcba')
        cls.pdg_a, _e = creer_employe(cls.A, 'pdg', agence=False)
        cls.pdg_b, _e = creer_employe(cls.B, 'pdg', agence=False)
        cls.guichetier_a, _e = creer_employe(cls.A, 'guichetier')
        cls.su = User.objects.create_superuser('plateforme', password='x')

    def page(self, user, url='/admin/'):
        self.client.force_login(user)
        return self.client.get(url, **H)

    # ---------- couleurs et logo propres a chaque entreprise
    def test_chaque_entreprise_a_ses_couleurs(self):
        r = self.page(self.pdg_a)
        self.assertContains(r, '--c-principale: #123456')
        self.assertContains(r, '--c-accent: #abcdef')
        self.assertNotContains(r, '#654321')
        r = self.page(self.pdg_b)
        self.assertContains(r, '--c-principale: #654321')
        self.assertContains(r, '--c-accent: #fedcba')
        self.assertNotContains(r, '#123456')

    def test_nom_de_l_entreprise_dans_le_menu_et_l_accueil(self):
        r = self.page(self.pdg_a)
        self.assertContains(r, 'id="menu-lateral"')
        self.assertContains(r, 'Alpha')
        self.assertNotContains(r, 'Beta')
        self.assertContains(r, 'class="hero-logo"')

    def test_la_couleur_d_accent_doit_etre_valide(self):
        c = self.A['compagnie']
        c.couleur_secondaire = 'rouge'
        with self.assertRaises(ValidationError):
            c.full_clean()

    # ---------- contenu du menu selon le poste
    def test_menu_du_superviseur(self):
        r = self.page(self.su)
        self.assertContains(r, 'href="/espace/plateforme/"')
        self.assertContains(r, 'href="/espace/plateforme/facturation/"')
        self.assertContains(r, 'href="/espace/plateforme/nouvelle/"')
        self.assertContains(r, 'Administration')
        self.assertNotContains(r, 'href="/espace/vendre-billet')                      # pas de raccourcis d'agence

    def test_menu_du_guichetier_et_du_pdg(self):
        r = self.page(self.guichetier_a)
        self.assertContains(r, 'href="/espace/vendre-billet')
        self.assertNotContains(r, 'href="/espace/plateforme/')
        self.assertNotContains(r, 'href="/espace/abonnement/')                  # reserve au PDG
        r = self.page(self.pdg_a)
        self.assertContains(r, 'href="/espace/abonnement/"')
        self.assertContains(r, 'Vue d&#x27;ensemble PDG')
        self.assertNotContains(r, 'href="/espace/plateforme/')

    def test_le_menu_suit_les_droits_django(self):
        u = User.objects.create_user('limite', password='x', is_staff=True)
        Employe.objects.create(user=u, compagnie=self.A['compagnie'], agence=self.A['agence'], nom='L', prenom='L', telephone='9', poste='autre')
        u.user_permissions.set(Permission.objects.filter(codename='view_client'))
        r = self.page(u)
        self.assertContains(r, 'href="/admin/transport/client/"')
        self.assertNotContains(r, 'href="/admin/transport/employe/"')
        self.assertNotContains(r, 'href="/admin/transport/bus/"')

    def test_element_actif_du_menu(self):
        r = self.page(self.pdg_a, '/admin/transport/client/')
        self.assertContains(r, 'href="/admin/transport/client/" class="menu-lien actif"')
        r = self.page(self.pdg_a)
        self.assertContains(r, 'href="/admin/" class="menu-lien actif"')

    def test_pas_de_menu_sur_la_page_de_connexion(self):
        self.client.logout()
        r = self.client.get('/admin/login/', **H)
        self.assertNotContains(r, 'id="menu-lateral"')

    def test_creation_d_entreprise_avec_couleurs(self):
        donnees = {'nom': 'Ben Siam', 'code': 'bs', 'siege': 'Moundou', 'telephone': '60000000', 'couleur': '#aa0000', 'accent': '#00bb00',
                   'pdg_nom': 'Siam', 'pdg_prenom': 'Ben', 'pdg_telephone': '66554433'}
        self.client.force_login(self.su)
        self.client.post('/espace/plateforme/nouvelle/', donnees, **H)
        c = Compagnie.objects.get(code='bs')
        self.assertEqual((c.couleur_principale, c.couleur_secondaire), ('#aa0000', '#00bb00'))
        r = self.client.post('/espace/plateforme/nouvelle/', dict(donnees, code='bt', pdg_telephone='1', accent='vert'), **H)
        self.assertIn('couleur_secondaire', r.context['erreurs'])
        self.assertFalse(Compagnie.objects.filter(code='bt').exists())
