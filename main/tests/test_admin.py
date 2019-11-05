from django.test import TestCase
from django.urls import reverse
from main import factories
from main import models
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

class TestAdminView(TestCase):
    def test_most_bought_products(self):
        products = [
            factories.ProductFactory(name='A', active=True),
            factories.ProductFactory(name='B', active=True),
            factories.ProductFactory(name='C', active=True),
        ]
        orders = factories.OrderFactory.create_batch(3)
        factories.OrderLineFactory.create_batch(
            2, order=orders[0], product=products[0]
        )
        factories.OrderLineFactory.create_batch(
            2, order=orders[0], product=products[1]
        )
        factories.OrderLineFactory.create_batch(
            2, order=orders[1], product=products[0]
        )
        factories.OrderLineFactory.create_batch(
            2, order=orders[1], product=products[2]
        )
        factories.OrderLineFactory.create_batch(
            2, order=orders[2], product=products[0]
        )
        factories.OrderLineFactory.create_batch(
            1, order=orders[2], product=products[1]
        )
        user = models.User.objects.create_superuser(
            'user2', 'topsecret'
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse('admin:most_bought_products'),
            {'period': '90'},
        )
        self.assertEqual(response.status_code, 200)

        data = dict(
            zip(
                response.context['labels'],
                response.context['values'],
            )
        )

        self.assertEqual(data, {'B': 3, 'C': 2, 'A': 6})

    def test_invoice_renders_exactly_as_expected(self):
        products = [
            factories.ProductFactory(
                name='Backgammon for dummies',
                active=True,
                price=Decimal('13.00')
            ),
            factories.ProductFactory(
                name='The cathedral and the bazaar ',
                active=True,
                price=Decimal('10.00')
            ),
        ]

        with patch('django.utils.timezone.now') as mock_now:
            mock_now.return_value = datetime(
                2019, 11, 5, 00, 00
            )

            order = factories.OrderFactory(
                id=4,
                billing_name='ForTest',
                billing_address1='ForTest',
                billing_address2='ForTest',
                billing_zip_code='ForTest',
                billing_city='ForTest',
                billing_country='ua',
            )

            factories.OrderLineFactory.create_batch(
                2, order=order, product=products[0]
            )
            factories.OrderLineFactory.create_batch(
                2, order=order, product=products[1]
            )
            user = models.User.objects.create_superuser(
                'user', 'newone'
            )
            self.client.force_login(user)

            response = self.client.get(
                reverse(
                    'admin:invoice', kwargs={'order_id': order.id}
                )
            )
            self.assertEqual(response.status_code, 200)
            content = response.content.decode('utf8')

            with open(
                'main/fixtures/invoice_test_order.html'
            ) as fixture:
                expected_content = fixture.read()

            self.assertHTMLEqual(content, expected_content)

