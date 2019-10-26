from decimal import Decimal
from django.test import TestCase
from main import models

class TestModel(TestCase):
    def test_active_manager_works(self):
        models.Product.objects.create(
            name='Joker',
            price=Decimal('5.00'))
        
        models.Product.objects.create(
            name='Batman',
            price=Decimal('7.00'))
        
        models.Product.objects.create(
            name='Harley Quinn',
            price=Decimal('10.00'),
            active=False)

        self.assertEqual(len(models.Product.objects.active()), 2)

    def test_create_order_works(self):
        p1 = models.Product.objects.create(
            name='Joker',
            price=Decimal('10.00')
        )
        p2 = models.Product.objects.create(
            name='Batman',
            price=Decimal('15.00')
        )
        user1 = models.User.objects.create_user(
            'newuser', 'topsecret'
        )
        billing = models.Address.objects.create(
            user=user1,
            name='My home',
            address1='High street 12',
            city='London',
            country='uk',
        )
        shipping = models.Address.objects.create(
            user=user1,
            name='My home',
            address1='High street 25',
            city='London',
            country='uk',
        )
        basket = models.Basket.objects.create(user=user1)
        models.Basketline.objects.create(
            basket=basket, product=p1
        )
        models.Basketline.objects.create(
            basket=basket, product=p2
        )

        with self.assertLogs('main.models', level='INFO') as cm:
            order = basket.create_order(billing, shipping)

        self.assertGreaterEqual(len(cm.output), 1)

        order.refresh_from_db()

        self.assertEqual(order.user, user1)
        self.assertEqual(
            order.billing_address1, 'High street 12'
        )
        self.assertEqual(
            order.shipping_address1, 'High street 25'
        )

        self.assertEqual(order.lines.all().count(), 2)
        lines = order.lines.all()
        self.assertEqual(lines[0].product, p1)
        self.assertEqual(lines[1].product, p2)

