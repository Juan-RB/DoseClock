"""
Models for user authentication and profiles.
Extends Django's built-in User model with additional fields.
"""

import uuid
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import MinValueValidator, MaxValueValidator


class PerfilUsuario(models.Model):
    """
    Extended user profile with additional information.
    One-to-one relationship with Django's User model.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='perfil'
    )
    nombre_completo = models.CharField(
        max_length=150,
        verbose_name="Nombre completo"
    )
    edad = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(120)],
        verbose_name="Edad"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"

    def __str__(self):
        return f"{self.nombre_completo} ({self.user.username})"


@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    """
    Signal to create user profile when a new user is created.
    Only creates if profile doesn't exist.
    """
    if created and not hasattr(instance, 'perfil'):
        # Default values - should be updated after registration
        PerfilUsuario.objects.create(
            user=instance,
            nombre_completo=instance.username,
            edad=18
        )
