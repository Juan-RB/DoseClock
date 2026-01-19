"""
Admin configuration for accounts app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import PerfilUsuario


class PerfilUsuarioInline(admin.StackedInline):
    """Inline admin for user profile."""
    model = PerfilUsuario
    can_delete = False
    verbose_name_plural = 'Perfil'


class CustomUserAdmin(UserAdmin):
    """Extended user admin with profile inline."""
    inlines = [PerfilUsuarioInline]
    list_display = ['username', 'email', 'get_nombre', 'get_edad', 'is_active', 'date_joined']
    
    def get_nombre(self, obj):
        return obj.perfil.nombre_completo if hasattr(obj, 'perfil') else '-'
    get_nombre.short_description = 'Nombre'
    
    def get_edad(self, obj):
        return obj.perfil.edad if hasattr(obj, 'perfil') else '-'
    get_edad.short_description = 'Edad'


# Re-register User with custom admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    """Admin for user profiles."""
    list_display = ['nombre_completo', 'user', 'edad', 'fecha_creacion']
    search_fields = ['nombre_completo', 'user__username', 'user__email']
    list_filter = ['fecha_creacion']
    readonly_fields = ['id', 'fecha_creacion', 'fecha_actualizacion']
