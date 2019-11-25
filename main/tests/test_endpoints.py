from django.urls import reverse
from rest_framework.test import APITestCase
from main import models
from rest_framework.authtoken.models import Token
from rest_framework import status
from main import factories


class TestEndpoints(APITestCase):
    def test_mobile_login_works(self):
        user = models.User.objects.create_user(
            'user1', 'abcabcabc'
        )

        response = self.client.post(
            reverse('mobile_token'),
            {'username': 'user1', 'password': 'abcabcabc'},
        )
        json = response.json()
        self.assertIn('token', json)

    def test_mobile_flow(self):
        user = factories.UserFactory(email='muser@mail.com')
        token = Token.objects.get(user=user)
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + token.key
        )

        orders = factories.OrderFactory.create_batch(
            2, user=user
        )
        a = factories.ProductFactory(
            name='Yet another book', active=True, price=18.00
        )
        b = factories.ProductFactory(
            name='Masterpiece', active=True, price=12.00
        )
        factories.OrderLineFactory.create_batch(
            2, order=orders[0], product=a
        )
        factories.OrderLineFactory.create_batch(
            2, order=orders[1], product=b
        )

        response = self.client.get(reverse('mobile_my_orders'))
        self.assertEqual(
            response.status_code, status.HTTP_200_OK
        )

        expected = [
            {
                'id': orders[1].id,
                'image': None,
                'summary': '2 x Masterpiece',
                'price': 24.0,
            },
            {
                'id': orders[0].id,
                'image': None,
                'summary': '2 x Yet another book',
                'price': 36.0,
            },
        ]
        self.assertEqual(response.json(), expected)
