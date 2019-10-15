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
        