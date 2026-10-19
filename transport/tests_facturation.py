"""Tests de la facturation SaaS : factures mensuelles, paiements, retards, rappels, acces et etancheite."""
import datetime
from io import StringIO
from unittest import mock

from django.contrib.admin.sites import site as admin_site
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings

from .models import Compagnie, FactureAbonnement, PaiementAbonnement
from .services_facturation import (
    enregistrer_paiement, envoyer_rappel, factures_impayees, generer_factures_du_mois, resume_facturation,
)
from .tenant import portee
from .tests_isolation import construire_monde, creer_employe

H = {'HTTP_HOST': 'localhost'}
AUJOURD_HUI = datetime.date.today()


@override_settings(ALLOWED_HOSTS=['*'])
class FacturationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.A = construire_monde('aa', 'Alpha')
        cls.B = construire_monde('bb', 'Beta')
        cls.ca, cls.cb = cls.A['compagnie'], cls.B['compagnie']
        Compagnie.objects.filter(pk=cls.ca.pk).update(abonnement_montant=50000, email='alpha@example.com')
        Compagnie.objects.filter(pk=cls.cb.pk).update(abonnement_montant=30000)
        cls.ca.refresh_from_db()
        cls.cb.refresh_from_db()
        cls.pdg_a, _e = creer_employe(cls.A, 'pdg', agence=False)
        cls.pdg_b, _e = creer_employe(cls.B, 'pdg', agence=False)
        cls.resp_a, _e = creer_employe(cls.A, 'responsable')
        cls.su = User.objects.create_superuser('plateforme', password='x')

    def facture(self, compagnie, jours_avant_echeance=10, montant=None):
        return FactureAbonnement.objects.create(
            compagnie=compagnie, periode=AUJOURD_HUI.replace(day=1) - datetime.timedelta(days=60 * (compagnie.pk % 7)),
            montant=montant or compagnie.abonnement_montant,
            date_echeance=AUJOURD_HUI + datetime.timedelta(days=jours_avant_echeance))

    # ---------- generation
    def test_generation_une_facture_par_entreprise_et_par_mois(self):
        creees = generer_factures_du_mois()
        self.assertEqual(len(creees), 2)
        f = FactureAbonnement.objects.get(compagnie=self.ca)
        self.assertEqual(f.montant, 50000)
        self.assertEqual(f.periode, AUJOURD_HUI.replace(day=1))
        self.assertEqual(f.date_echeance, AUJOURD_HUI + datetime.timedelta(days=15))
        self.assertTrue(f.numero.startswith(f'FAC-AA-{AUJOURD_HUI.year}-'))
        self.assertEqual(generer_factures_du_mois(), [])            # relancer ne cree rien de plus
        self.assertEqual(FactureAbonnement.objects.count(), 2)

    def test_generation_ignore_suspendues_et_sans_abonnement(self):
        Compagnie.objects.filter(pk=self.cb.pk).update(actif=False)
        Compagnie.objects.filter(pk=self.ca.pk).update(abonnement_montant=0)
        self.assertEqual(generer_factures_du_mois(), [])

    def test_commande_mensuelle(self):
        sortie = StringIO()
        call_command('facturer_abonnements', stdout=sortie)
        self.assertIn('2 facture(s) creee(s)', sortie.getvalue())
        sortie = StringIO()
        call_command('facturer_abonnements', stdout=sortie)
        self.assertIn('0 facture(s) creee(s)', sortie.getvalue())

    # ---------- paiements
    def test_paiement_partiel_puis_total(self):
        f = self.facture(self.ca)
        self.assertEqual(f.statut, 'a_payer')
        enregistrer_paiement(f, 20000, 'mobile_money', 'TX1')
        f = FactureAbonnement.objects.get(pk=f.pk)
        self.assertEqual((f.paye, f.reste, f.statut), (20000, 30000, 'partielle'))
        enregistrer_paiement(f, 30000)
        f = FactureAbonnement.objects.get(pk=f.pk)
        self.assertEqual((f.reste, f.statut), (0, 'payee'))
        self.assertEqual(factures_impayees(self.ca), [])

    def test_paiement_refuse_si_invalide(self):
        f = self.facture(self.ca)
        for montant in (0, -5, 'abc', 50001):
            with self.assertRaises(ValidationError, msg=str(montant)):
                enregistrer_paiement(f, montant)
        with self.assertRaises(ValidationError):
            enregistrer_paiement(f, 100, mode='bitcoin')
        self.assertEqual(PaiementAbonnement.objects.count(), 0)

    def test_retard_et_resume(self):
        en_retard = self.facture(self.ca, jours_avant_echeance=-3)
        normale = self.facture(self.cb, jours_avant_echeance=5)
        self.assertEqual(en_retard.statut, 'retard')
        self.assertEqual(normale.statut, 'a_payer')
        enregistrer_paiement(en_retard, 10000)
        r = resume_facturation()
        self.assertEqual(r['a_encaisser'], 40000 + 30000)
        self.assertEqual((r['nb_en_retard'], r['en_retard']), (1, 40000))
        self.assertEqual(r['encaisse_mois'], 10000)
        self.assertEqual(r['compagnies_en_retard'], {self.ca.pk})
        # payee entierement : plus en retard
        enregistrer_paiement(en_retard, 40000)
        self.assertEqual(resume_facturation()['nb_en_retard'], 0)

    # ---------- etancheite et acces
    def test_ecrans_du_superviseur_interdits_aux_autres(self):
        f = self.facture(self.ca)
        self.client.force_login(self.pdg_a)
        for url in ('/espace/plateforme/facturation/',):
            self.assertEqual(self.client.get(url, **H).status_code, 302, url)
        self.client.post('/espace/plateforme/facturation/generer/', **H)
        self.assertEqual(FactureAbonnement.objects.count(), 1)
        self.client.post(f'/espace/plateforme/facturation/{f.pk}/paiement/', {'montant': 100, 'mode': 'especes'}, **H)
        self.assertEqual(PaiementAbonnement.objects.count(), 0)
        with mock.patch('transport.email_brevo.envoyer_email') as envoi:
            self.client.post(f'/espace/plateforme/{self.ca.pk}/rappel/', **H)
            envoi.assert_not_called()

    def test_pdg_ne_voit_que_ses_factures(self):
        fa, fb = self.facture(self.ca), self.facture(self.cb)
        self.assertEqual(list(portee(self.pdg_a, FactureAbonnement)), [fa])
        self.client.force_login(self.pdg_a)
        r = self.client.get('/espace/abonnement/', **H)
        self.assertContains(r, fa.numero)
        self.assertNotContains(r, fb.numero)
        self.assertEqual(self.client.get(f'/espace/abonnement/facture/{fa.pk}/', **H).status_code, 200)
        self.assertEqual(self.client.get(f'/espace/abonnement/facture/{fb.pk}/', **H).status_code, 404)

    def test_employe_non_pdg_sans_acces_aux_factures(self):
        f = self.facture(self.ca)
        self.client.force_login(self.resp_a)
        self.assertEqual(self.client.get('/espace/abonnement/', **H).status_code, 302)
        self.assertEqual(self.client.get(f'/espace/abonnement/facture/{f.pk}/', **H).status_code, 302)
        self.assertEqual(self.client.get('/admin/transport/factureabonnement/', **H).status_code, 403)

    def test_prix_de_l_abonnement_reserve_au_superviseur(self):
        admin_compagnie = admin_site._registry[Compagnie]
        requete = mock.Mock(user=self.pdg_a)
        self.assertIn('abonnement_montant', admin_compagnie.get_readonly_fields(requete))
        requete = mock.Mock(user=self.su)
        self.assertNotIn('abonnement_montant', admin_compagnie.get_readonly_fields(requete))

    # ---------- ecrans
    def test_ecran_facturation_et_paiement(self):
        f = self.facture(self.ca, jours_avant_echeance=-2)
        self.client.force_login(self.su)
        r = self.client.get('/espace/plateforme/facturation/', **H)
        self.assertContains(r, f.numero)
        self.assertContains(r, 'Envoyer un rappel par e-mail')
        r = self.client.post(f'/espace/plateforme/facturation/{f.pk}/paiement/', {'montant': 20000, 'mode': 'virement', 'reference': 'V9'}, **H)
        self.assertEqual(r.status_code, 302)
        p = PaiementAbonnement.objects.get()
        self.assertEqual((p.montant, p.mode, p.reference), (20000, 'virement', 'V9'))
        # montant trop grand : refuse, rien d'enregistre
        self.client.post(f'/espace/plateforme/facturation/{f.pk}/paiement/', {'montant': 999999, 'mode': 'especes'}, **H)
        self.assertEqual(PaiementAbonnement.objects.count(), 1)
        # filtre "en retard"
        self.assertContains(self.client.get('/espace/plateforme/facturation/?statut=retard', **H), f.numero)
        self.assertNotContains(self.client.get('/espace/plateforme/facturation/?statut=payees', **H), f.numero)

    def test_generation_par_l_ecran(self):
        self.client.force_login(self.su)
        self.client.post('/espace/plateforme/facturation/generer/', **H)
        self.assertEqual(FactureAbonnement.objects.count(), 2)
        self.client.post('/espace/plateforme/facturation/generer/', **H)
        self.assertEqual(FactureAbonnement.objects.count(), 2)

    def test_facture_imprimable(self):
        f = self.facture(self.ca)
        enregistrer_paiement(f, 50000)
        self.client.force_login(self.su)
        r = self.client.get(f'/espace/abonnement/facture/{f.pk}/', **H)
        self.assertContains(r, f.numero)
        self.assertContains(r, 'PAYEE')

    def test_rappel_par_email(self):
        self.facture(self.ca, jours_avant_echeance=-1)
        self.facture(self.cb, jours_avant_echeance=-1)                # Beta n'a pas d'adresse e-mail
        self.client.force_login(self.su)
        with mock.patch('transport.email_brevo.envoyer_email', return_value=True) as envoi:
            self.client.post(f'/espace/plateforme/{self.ca.pk}/rappel/', **H)
            self.assertEqual(envoi.call_count, 1)
            self.assertEqual(envoi.call_args[0][0], 'alpha@example.com')
            self.assertIn('50000', envoi.call_args[0][2])
            self.client.post(f'/espace/plateforme/{self.cb.pk}/rappel/', **H)
            self.assertEqual(envoi.call_count, 1)                      # pas d'adresse : rien envoye

    def test_rappel_sans_facture_a_payer(self):
        f = self.facture(self.ca)
        enregistrer_paiement(f, 50000)
        with mock.patch('transport.email_brevo.envoyer_email') as envoi:
            self.assertFalse(envoyer_rappel(self.ca))
            envoi.assert_not_called()

    # ---------- tableaux de bord
    def test_tableau_de_bord_du_superviseur(self):
        self.facture(self.ca, jours_avant_echeance=-4)
        self.client.force_login(self.su)
        r = self.client.get('/admin/', **H)
        self.assertContains(r, 'Factures en retard')
        self.assertContains(r, 'Paiement en retard')
        self.assertContains(r, '/espace/plateforme/facturation/')

    def test_le_pdg_est_prevenu_d_un_retard(self):
        self.client.force_login(self.pdg_a)
        self.assertNotContains(self.client.get('/admin/', **H), 'retard de paiement')
        self.facture(self.ca, jours_avant_echeance=-4)
        r = self.client.get('/admin/', **H)
        self.assertContains(r, 'retard de paiement')
        self.assertContains(r, '/espace/abonnement/')
        # le PDG de l'autre entreprise n'est pas concerne
        self.client.force_login(self.pdg_b)
        self.assertNotContains(self.client.get('/admin/', **H), 'retard de paiement')

    # ---------- creation d'une entreprise avec son prix
    def test_creation_avec_abonnement(self):
        donnees = {'nom': 'Ben Siam', 'code': 'bs', 'siege': 'Moundou', 'telephone': '60000000', 'couleur': '#aa0000',
                   'pdg_nom': 'Siam', 'pdg_prenom': 'Ben', 'pdg_telephone': '66554433', 'abonnement': '45000'}
        self.client.force_login(self.su)
        self.client.post('/espace/plateforme/nouvelle/', donnees, **H)
        self.assertEqual(Compagnie.objects.get(code='bs').abonnement_montant, 45000)
        r = self.client.post('/espace/plateforme/nouvelle/', dict(donnees, code='bt', pdg_telephone='1', abonnement='-3'), **H)
        self.assertIn('abonnement', r.context['erreurs'])
        self.assertFalse(Compagnie.objects.filter(code='bt').exists())
