from decimal import Decimal
from unittest.mock import patch

from django.contrib import auth
from django.test import TestCase
from django.urls import reverse

from main import forms, models


# Create your tests here.
class TestPage(TestCase):
    def test_home_page_works(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')
        self.assertContains(response, 'BookTime')

    def test_about_us_page_works(self):
        response = self.client.get(reverse('about_us'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'about_us.html')
        self.assertContains(response, 'BookTime')

    def test_contact_us_page_works(self):
        response = self.client.get(reverse('contact_us'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'contact_form.html')
        self.assertContains(response, 'BookTime')
        self.assertIsInstance(response.context['form'], forms.ContactForm)

    def test_products_page_returns_acive(self):
        models.Product.objects.create(
            name='Joker',
            slug='joker',
            price=Decimal('8.00'),
        )
        models.Product.objects.create(
            name='Batman',
            slug='batman',
            price=Decimal('7.00'),
            active=False,
        )
        response = self.client.get(
            reverse('products', kwargs={'tag': 'all'})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'BookTime')

        product_list = models.Product.objects.active().order_by('name')
        self.assertEqual(
            list(response.context['object_list']),
            list(product_list),
        )

    def test_products_page_filters_by_tags_and_active(self):
        joker = models.Product.objects.create(
            name='Joker',
            slug='joker',
            price=Decimal('8.00'),
        )
        joker.tags.create(name='Open Source', slug='opensource')
        models.Product.objects.create(
            name='Batman',
            slug='batman',
            price=Decimal('15.00')
        )
        response = self.client.get(
            reverse('products', kwargs={'tag': 'opensource'})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'BookTime')

        product_list = (
            models.Product.objects.active()
                .filter(tags__slug='opensource')
                .order_by('name')
        )

        self.assertEqual(
            list(response.context['object_list']),
            list(product_list),
        )

    def test_user_signup_page_loads_correctly(self):
        response = self.client.get(reverse('signup'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'signup.html')
        self.assertContains(response, 'BookTime')
        self.assertIsInstance(
            response.context['form'], forms.UserCreationForm
        )

    def test_user_signup_page_submission_works(self):
        post_data = {
            'email': 'test@domain.com',
            'password1': '123123123qwe',
            'password2': '123123123qwe',
        }
        with patch.object(
                forms.UserCreationForm, 'send_mail'
        ) as mock_send:
            response = self.client.post(
                reverse('signup'), post_data
            )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            models.User.objects.filter(
                email='test@domain.com'
            ).exists()
        )
        self.assertTrue(
            auth.get_user(self.client).is_authenticated
        )
        mock_send.assert_called_once()

    def test_user_signup_page_bad_submission(self):
        post_data = {
            'email': 'test@domain.com',
            'password1': '123123123qwe',
            'password2': 'notthesame',
        }
        response = self.client.post(reverse('signup'), post_data)
        self.assertEqual(response.status_code, 200)
        # Escaping single quotation mark
        self.assertContains(response, "The two password fields didn&#39;t match.")

    def test_user_login_page_loads_correctly(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')
        self.assertContains(response, 'BookTime')
        self.assertIsInstance(
            response.context['form'], forms.AuthenticationForm
        )

    def test_user_login_page_submission_works(self):
        #  creating test user
        post_data = {
            'email': 'test@domain.com',
            'password1': '123123123qwe',
            'password2': '123123123qwe',
        }
        response = self.client.post(reverse('signup'), post_data)

        post_data = {
            'email': 'test@domain.com',
            'password1': '123123123qwe',
        }

        # trying to log in
        response = self.client.post(reverse('login'), post_data)

        self.assertEqual(response.status_code, 200)

        self.assertTrue(
            auth.get_user(self.client).is_authenticated
        )

    def test_user_login_page_bad_submission(self):
        #  creating test user

        post_data = {
            'email': 'never@ever.com',
            'password1': 'doesntexist',
        }

        # trying to log in
        response = self.client.post(reverse('login'), post_data)

        self.assertEqual(response.status_code, 200)

        self.assertFalse(
            auth.get_user(self.client).is_authenticated
        )

    def test_address_list_page_returns_only_owned(self):
        user1 = models.User.objects.create_user(
            'user1', 'topsecret'
        )
        user2 = models.User.objects.create_user(
            'user2', 'loremipsum'
        )
        models.Address.objects.create(
            user=user1,
            name='home',
            address1='str',
            address2='second str',
            city='Gotham',
            country='us',
        )
        models.Address.objects.create(
            user=user2,
            name='home 2',
            address1='user2 str',
            address2='user2 second str',
            city='Piltover',
            country='uk',
        )

        self.client.force_login(user2)
        response = self.client.get(reverse('address_list'))
        self.assertEqual(response.status_code, 200)

        address_list = models.Address.objects.filter(user=user2)

        self.assertEqual(
            list(response.context['object_list']),
            list(address_list),
        )

    def test_address_create_stores_user(self):
        user1 = models.User.objects.create_user(
            'user1', 'topsecret'
        )
        post_data = {
            'name': 'home sweet home',
            'address1': 'my street',
            'address2': 'my street 2',
            'zip_code': '534534',
            'city': 'Gotham',
            'country': 'us',
        }
        self.client.force_login(user1)
        self.client.post(
            reverse('address_create'), post_data
        )
        self.assertTrue(
            models.Address.objects.filter(user=user1).exists()
        )

    def test_add_to_basket_loggedin_works(self):
        user1 = models.User.objects.create_user(
            'user1@a.com', 'topsecret'
        )

        j = models.Product.objects.create(
            name='Joker',
            slug='joker',
            price=Decimal('10.00'),
        )

        b = models.Product.objects.create(
            name='Batman',
            slug='batman',
            price=Decimal('15.00'),
        )

        self.client.force_login(user1)
        response = self.client.get(
            reverse('add_to_basket'), {'product_id': j.id}
        )
        response = self.client.get(
            reverse('add_to_basket'), {'product_id': j.id}
        )

        self.assertTrue(
            models.Basket.objects.filter(user=user1).exists()
        )
        self.assertEqual(
            models.Basketline.objects.filter(
                basket__user=user1
            ).count(),
            1,
        )

        response = self.client.get(
            reverse('add_to_basket'), {'product_id': b.id}
        )
        self.assertEqual(
            models.Basketline.objects.filter(
                basket__user=user1
            ).count(),
            2,
        )

    def test_add_to_basket_login_merge_works(self):
        user1 = models.User.objects.create_user(
            'user1@a.com', 'topsecret'
        )

        j = models.Product.objects.create(
            name='Joker',
            slug='joker',
            price=Decimal('10.00'),
        )

        b = models.Product.objects.create(
            name='Batman',
            slug='batman',
            price=Decimal('15.00'),
        )

        basket = models.Basket.objects.create(user=user1)
        models.Basketline.objects.create(
            basket=basket, product=j, quantity=2
        )
        response = self.client.get(
            reverse('add_to_basket'), {'product_id': b.id}
        )
        response = self.client.post(
            reverse('login'),
            {'email': 'user1@a.com', 'password': 'topsecret'},
        )

        self.assertTrue(
            auth.get_user(self.client).is_authenticated
        )

        self.assertTrue(
            models.Basket.objects.filter(user=user1).exists()
        )
        basket = models.Basket.objects.get(user=user1)
        self.assertEqual(basket.count(), 3)