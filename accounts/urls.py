"""
URL configuration for accounts app.
"""

from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('registro/', views.registro_view, name='registro'),
    path('logout/', views.logout_view, name='logout'),
    path('perfil/', views.perfil_view, name='perfil'),
    
    # AJAX validation endpoints
    path('validar-username/', views.validar_username, name='validar_username'),
    path('validar-email/', views.validar_email, name='validar_email'),
]
