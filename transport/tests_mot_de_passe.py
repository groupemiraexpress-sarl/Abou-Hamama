"""Tests du "mot de passe oublie" (API + page de reinitialisation)."""
import re
from unittest import mock

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Client
from .tests_isolation import construire_monde, creer_employe


class MotDePasseOublieTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.A = construire_monde('aa', 'Alpha')
        cls.voyageur = User.objects.create_user('voy', email='voy@test.td', password='ancien1')
        Client.objects.create(compagnie=cls.A['compagnie'], user=cls.voyageur, nom='Voy', telephone='66000099')
        cls.staff, _e = creer_employe(cls.A, 'guichetier')
        cls.staff.email = 'staff@test.td'
        cls.staff.save()

    def setUp(self):
        cache.clear()

    tearDown = setUp

    def demander(self, email):
        with mock.patch('transport.email_brevo.envoyer_email') as envoi:
            r = APIClient().post('/api/mot-de-passe-oublie/', {'email': email}, format='json', HTTP_X_COMPAGNIE='aa')
        return r, envoi

    def test_reponse_identique_et_mail_seulement_pour_un_voyageur(self):
        r1, envoi1 = self.demander('voy@test.td')
        r2, envoi2 = self.demander('inconnu@test.td')
        r3, envoi3 = self.demander('staff@test.td')       # compte employe : pas de reinitialisation par ce moyen
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json(), r2.json())
        self.assertEqual(r1.json(), r3.json())
        self.assertEqual(envoi1.call_count, 1)
        self.assertEqual(envoi2.call_count, 0)
        self.assertEqual(envoi3.call_count, 0)
        self.assertEqual(envoi1.call_args.kwargs.get('nom_expediteur'), 'Alpha')

    def lien(self):
        r, envoi = self.demander('voy@test.td')
        corps = envoi.call_args.args[2]
        return re.search(r'(/mot-de-passe/reinitialiser/\S+/)', corps).group(1)

    def test_changement_du_mot_de_passe_par_le_lien(self):
        lien = self.lien()
        self.assertContains(self.client.get(lien), 'name="mot_de_passe"')
        r = self.client.post(lien, {'mot_de_passe': 'abc', 'confirmation': 'abc'})
        self.assertContains(r, 'au moins 6 caracteres')
        r = self.client.post(lien, {'mot_de_passe': 'nouveau1', 'confirmation': 'autre'})
        self.assertContains(r, 'pas identiques')
        self.assertIsNotNone(authenticate(username='voy', password='ancien1'))
        r = self.client.post(lien, {'mot_de_passe': 'nouveau1', 'confirmation': 'nouveau1'})
        self.assertContains(r, 'Mot de passe modifie')
        self.assertIsNotNone(authenticate(username='voy', password='nouveau1'))
        self.assertIsNone(authenticate(username='voy', password='ancien1'))
        # le lien ne marche qu'une fois
        self.assertContains(self.client.get(lien), 'Lien invalide')

    def test_lien_falsifie_refuse(self):
        self.assertContains(self.client.get('/mot-de-passe/reinitialiser/MQ/token-bidon/'), 'Lien invalide')

    def test_limite_de_demandes(self):
        statuts = [self.demander('voy@test.td')[0].status_code for _ in range(7)]
        self.assertEqual(statuts[:5], [200] * 5)
        self.assertEqual(statuts[-1], 429)
