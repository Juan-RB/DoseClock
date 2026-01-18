"""
URL configuration for medicamentos app.
"""

from django.urls import path
from . import views

app_name = 'medicamentos'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Medicamentos
    path('medicamentos/', views.medicamentos_list, name='medicamentos_list'),
    path('medicamentos/nuevo/', views.medicamento_create, name='medicamento_create'),
    path('medicamentos/<uuid:pk>/', views.medicamento_detail, name='medicamento_detail'),
    path('medicamentos/<uuid:pk>/editar/', views.medicamento_edit, name='medicamento_edit'),
    path('medicamentos/<uuid:pk>/eliminar/', views.medicamento_delete, name='medicamento_delete'),
    
    # Tratamientos
    path('tratamientos/', views.tratamientos_list, name='tratamientos_list'),
    path('tratamientos/nuevo/', views.tratamiento_create, name='tratamiento_create'),
    path('tratamientos/<uuid:pk>/', views.tratamiento_detail, name='tratamiento_detail'),
    path('tratamientos/<uuid:pk>/editar/', views.tratamiento_edit, name='tratamiento_edit'),
    path('tratamientos/<uuid:pk>/pausar/', views.tratamiento_toggle_pause, name='tratamiento_toggle_pause'),
    path('tratamientos/<uuid:pk>/finalizar/', views.tratamiento_finalizar, name='tratamiento_finalizar'),
    path('tratamientos/<uuid:pk>/eliminar/', views.tratamiento_delete, name='tratamiento_delete'),
    
    # Tomas
    path('tomas/', views.historial_tomas, name='historial_tomas'),
    path('tomas/<uuid:pk>/confirmar/', views.confirmar_toma, name='confirmar_toma'),
    path('tomas/<uuid:tratamiento_pk>/historial/', views.historial_tratamiento, name='historial_tratamiento'),
    
    # Calendario
    path('calendario/', views.calendario, name='calendario'),
    path('calendario/datos/', views.calendario_datos, name='calendario_datos'),
    
    # Configuracion
    path('configuracion/', views.configuracion, name='configuracion'),
    path('telegram/vincular/', views.telegram_vincular, name='telegram_vincular'),
    path('telegram/desvincular/', views.telegram_desvincular, name='telegram_desvincular'),
    path('telegram/test/', views.telegram_test, name='telegram_test'),
    
    # Backups
    path('backups/', views.backup_list, name='backup_list'),
    path('backups/crear/', views.backup_create, name='backup_create'),
    path('backups/restaurar/<str:filename>/', views.backup_restore, name='backup_restore'),
    path('backups/eliminar/<str:filename>/', views.backup_delete, name='backup_delete'),
    path('backups/descargar/<str:filename>/', views.backup_download, name='backup_download'),
    
    # API endpoints (for JavaScript)
    path('api/proximas-tomas/', views.api_proximas_tomas, name='api_proximas_tomas'),
    path('api/confirmar-toma/<uuid:pk>/', views.api_confirmar_toma, name='api_confirmar_toma'),
    path('api/notificaciones-pendientes/', views.api_notificaciones_pendientes, name='api_notificaciones_pendientes'),
    path('api/actualizar-estados/', views.api_actualizar_estados, name='api_actualizar_estados'),
    path('api/telegram/check-reminders/', views.api_telegram_check_reminders, name='api_telegram_check_reminders'),
    
    # Service Worker
    path('sw.js', views.service_worker, name='service_worker'),
]
