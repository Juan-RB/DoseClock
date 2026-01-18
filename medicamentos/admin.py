"""
Admin configuration for DoseClock.
"""
from django.contrib import admin
from .models import (
    Medicamento, 
    Tratamiento, 
    Toma, 
    Notificacion, 
    ConfiguracionUsuario
)


@admin.register(Medicamento)
class MedicamentoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'color', 'activo', 'fecha_creacion']
    list_filter = ['activo', 'fecha_creacion']
    search_fields = ['nombre']


@admin.register(Tratamiento)
class TratamientoAdmin(admin.ModelAdmin):
    list_display = [
        'medicamento', 
        'frecuencia_horas', 
        'estado', 
        'fecha_hora_inicio',
        'es_indefinido'
    ]
    list_filter = ['estado', 'es_indefinido', 'modo_calculo']
    search_fields = ['medicamento__nombre']


@admin.register(Toma)
class TomaAdmin(admin.ModelAdmin):
    list_display = [
        'tratamiento', 
        'hora_programada', 
        'hora_confirmada', 
        'estado'
    ]
    list_filter = ['estado', 'hora_programada']
    search_fields = ['tratamiento__medicamento__nombre']


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ['toma', 'tipo', 'hora_programada', 'enviada']
    list_filter = ['tipo', 'enviada']


@admin.register(ConfiguracionUsuario)
class ConfiguracionUsuarioAdmin(admin.ModelAdmin):
    list_display = [
        'modo_visual', 
        'tamano_texto', 
        'alto_contraste',
        'backup_automatico'
    ]
