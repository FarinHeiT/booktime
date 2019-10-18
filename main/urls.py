from django.urls import path
from django.views.generic import DetailView, TemplateView
from main import views, models


urlpatterns = [
    path('about-us/', TemplateView.as_view(template_name='about_us.html'), name='about_us'),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('contact-us/', views.ContactUsView.as_view(), name='contact_us'),
    path(
        'products/<slug:tag>/',
        views.ProductListView.as_view(),
        name = 'products',
    ),
    path(
        'product/<slug:slug>/',
        DetailView.as_view(model=models.Product),
        name='product'
    ),
    path('signup/', views.SignupView.as_view(), name='signup')
]