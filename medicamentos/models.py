"""
Models for DoseClock medication management system.

Entities:
- Medicamento: Medicine information
- Tratamiento: Treatment schedule for a medicine
- Toma: Individual dose record
- Notificacion: Notification schedule
- ConfiguracionUsuario: User preferences
"""

import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Medicamento(models.Model):
    """
    Represents a medication.
    Each medication can have multiple active treatments.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='medicamentos',
        verbose_name="Usuario",
        null=True,  # Temporarily nullable for migration
        blank=True
    )
    nombre = models.CharField(max_length=200, verbose_name="Nombre del medicamento")
    color = models.CharField(
        max_length=7, 
        blank=True, 
        null=True,
        verbose_name="Color identificador",
        help_text="Código hexadecimal (ej: #FF5733)"
    )
    icono = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name="Icono identificador"
    )
    notas = models.TextField(blank=True, null=True, verbose_name="Notas adicionales")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Medicamento"
        verbose_name_plural = "Medicamentos"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Tratamiento(models.Model):
    """
    Represents a treatment schedule for a medication.
    Includes frequency, duration, and calculation mode.
    """
    MODO_CALCULO_CHOICES = [
        ('programada', 'Desde hora programada'),
        ('confirmacion', 'Desde hora de confirmación'),
    ]
    
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('pausado', 'Pausado'),
        ('finalizado', 'Finalizado'),
    ]
    
    FRECUENCIA_SUGERIDA_CHOICES = [
        (5, '5 horas'),
        (8, '8 horas'),
        (12, '12 horas'),
        (24, '24 horas'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tratamientos',
        verbose_name="Usuario",
        null=True,  # Temporarily nullable for migration
        blank=True
    )
    medicamento = models.ForeignKey(
        Medicamento, 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tratamientos'
    )
    # Campo para preservar nombre si se elimina el medicamento
    medicamento_nombre_historico = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Nombre del medicamento (historico)"
    )
    fecha_hora_inicio = models.DateTimeField(verbose_name="Fecha y hora de inicio")
    duracion_dias = models.PositiveIntegerField(
        blank=True, 
        null=True,
        verbose_name="Duración en días",
        help_text="Dejar vacío para tratamiento indefinido"
    )
    es_indefinido = models.BooleanField(
        default=False, 
        verbose_name="Tratamiento indefinido"
    )
    frecuencia_horas = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        verbose_name="Frecuencia (horas)",
        help_text="Intervalo entre tomas en horas"
    )
    modo_calculo = models.CharField(
        max_length=20,
        choices=MODO_CALCULO_CHOICES,
        default='programada',
        verbose_name="Modo de cálculo",
        help_text="Determina cómo se calcula la siguiente toma"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='activo',
        verbose_name="Estado del tratamiento"
    )
    notas = models.TextField(blank=True, null=True, verbose_name="Notas")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tratamiento"
        verbose_name_plural = "Tratamientos"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.medicamento.nombre} - cada {self.frecuencia_horas}h"

    @property
    def nombre_medicamento(self):
        """Return medication name, using historical if medication deleted."""
        if self.medicamento:
            return self.medicamento.nombre
        return self.medicamento_nombre_historico or "Medicamento eliminado"

    @property
    def fecha_fin(self):
        """Calculate end date if treatment has duration."""
        if self.es_indefinido or not self.duracion_dias:
            return None
        from datetime import timedelta
        return self.fecha_hora_inicio + timedelta(days=self.duracion_dias)


class Toma(models.Model):
    """
    Represents an individual dose/intake record.
    Tracks scheduled vs actual times and status.
    """
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada a tiempo'),
        ('tarde', 'Confirmada tarde'),
        ('no_tomada', 'No tomada'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tratamiento = models.ForeignKey(
        Tratamiento, 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tomas'
    )
    # Campos para preservar datos si se elimina el tratamiento
    medicamento_nombre_historico = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Nombre del medicamento (historico)"
    )
    tratamiento_frecuencia_historica = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Frecuencia del tratamiento (historico)"
    )
    hora_programada = models.DateTimeField(verbose_name="Hora programada")
    hora_confirmada = models.DateTimeField(
        blank=True, 
        null=True,
        verbose_name="Hora de confirmación"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente',
        verbose_name="Estado"
    )
    notas = models.TextField(blank=True, null=True, verbose_name="Notas")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Toma"
        verbose_name_plural = "Tomas"
        ordering = ['-hora_programada']

    def __str__(self):
        nombre = self.nombre_medicamento
        return f"{nombre} - {self.hora_programada}"

    @property
    def nombre_medicamento(self):
        """Return medication name, using historical if deleted."""
        if self.tratamiento and self.tratamiento.medicamento:
            return self.tratamiento.medicamento.nombre
        if self.medicamento_nombre_historico:
            return self.medicamento_nombre_historico
        if self.tratamiento:
            return self.tratamiento.nombre_medicamento
        return "Medicamento eliminado"

    @property
    def color_estado(self):
        """Return color code based on status."""
        colors = {
            'pendiente': '#6c757d',    # Gray
            'confirmada': '#28a745',   # Green
            'tarde': '#fd7e14',        # Orange
            'no_tomada': '#dc3545',    # Red
        }
        return colors.get(self.estado, '#6c757d')


class Notificacion(models.Model):
    """
    Notification schedule for a dose.
    Can be main notification or reminder.
    """
    TIPO_CHOICES = [
        ('principal', 'Notificación principal'),
        ('recordatorio', 'Recordatorio anticipado'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    toma = models.ForeignKey(
        Toma, 
        on_delete=models.CASCADE, 
        related_name='notificaciones'
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='principal',
        verbose_name="Tipo de notificación"
    )
    hora_programada = models.DateTimeField(verbose_name="Hora programada")
    enviada = models.BooleanField(default=False, verbose_name="Enviada")
    fecha_envio = models.DateTimeField(
        blank=True, 
        null=True,
        verbose_name="Fecha de envío"
    )

    class Meta:
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
        ordering = ['-hora_programada']

    def __str__(self):
        return f"{self.tipo} - {self.toma}"


class ConfiguracionUsuario(models.Model):
    """
    User configuration and preferences.
    One configuration per user.
    """
    MODO_VISUAL_CHOICES = [
        ('minimalista', 'Modo Minimalista'),
        ('avanzado', 'Modo Visual Avanzado'),
    ]
    
    TAMANO_TEXTO_CHOICES = [
        ('normal', 'Normal'),
        ('grande', 'Grande'),
        ('muy_grande', 'Muy Grande'),
    ]
    
    PALETA_CHOICES = [
        ('nude', 'Nude (Tonos neutros)'),
        ('azul', 'Azul Sereno'),
        ('verde', 'Verde Natural'),
        ('purpura', 'Púrpura Suave'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='configuracion',
        verbose_name="Usuario",
        null=True,  # Temporarily nullable for migration
        blank=True
    )
    modo_visual = models.CharField(
        max_length=20,
        choices=MODO_VISUAL_CHOICES,
        default='minimalista',
        verbose_name="Modo visual"
    )
    paleta_colores = models.CharField(
        max_length=20,
        choices=PALETA_CHOICES,
        default='nude',
        verbose_name="Paleta de colores"
    )
    tamano_texto = models.CharField(
        max_length=20,
        choices=TAMANO_TEXTO_CHOICES,
        default='normal',
        verbose_name="Tamaño de texto"
    )
    alto_contraste = models.BooleanField(
        default=False, 
        verbose_name="Modo alto contraste"
    )
    recordatorio_anticipado = models.BooleanField(
        default=True,
        verbose_name="Recordatorio 5 minutos antes"
    )
    notificaciones_activas = models.BooleanField(
        default=True,
        verbose_name="Notificaciones activas"
    )
    sonido_notificacion = models.BooleanField(
        default=True,
        verbose_name="Sonido en notificaciones"
    )
    backup_automatico = models.BooleanField(
        default=False,
        verbose_name="Backup automático"
    )
    frecuencia_backup_dias = models.PositiveIntegerField(
        default=7,
        verbose_name="Frecuencia de backup (días)"
    )
    ultimo_backup = models.DateTimeField(
        blank=True, 
        null=True,
        verbose_name="Último backup"
    )
    
    # Telegram Integration
    telegram_chat_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Telegram Chat ID"
    )
    telegram_activo = models.BooleanField(
        default=False,
        verbose_name="Notificaciones por Telegram"
    )
    telegram_vinculado = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Fecha de vinculacion Telegram"
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración de Usuario"
        verbose_name_plural = "Configuraciones de Usuario"

    def __str__(self):
        if self.usuario:
            return f"Configuración de {self.usuario.username}"
        return "Configuración sin usuario"


