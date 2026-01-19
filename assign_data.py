"""
Script to reassign all data to a specific user.
Run with: python assign_data.py
"""

import os
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'doseclock.settings')

import django
django.setup()

from django.contrib.auth.models import User
from medicamentos.models import Medicamento, Tratamiento, ConfiguracionUsuario

def main():
    # Get user juan_1
    try:
        juan = User.objects.get(username='juan_1')
        print(f"Usuario encontrado: {juan.username} (ID: {juan.id})")
    except User.DoesNotExist:
        print("Error: Usuario 'juan_1' no encontrado")
        return
    
    # Reassign all medications
    meds = Medicamento.objects.all().update(usuario=juan)
    print(f"✅ Medicamentos asignados: {meds}")
    
    # Reassign all treatments  
    treats = Tratamiento.objects.all().update(usuario=juan)
    print(f"✅ Tratamientos asignados: {treats}")
    
    # Handle configuration
    ConfiguracionUsuario.objects.filter(usuario__isnull=True).delete()
    config, created = ConfiguracionUsuario.objects.get_or_create(
        usuario=juan,
        defaults={
            'modo_visual': 'minimalista',
            'paleta_colores': 'nude'
        }
    )
    print(f"✅ Configuración: {'creada' if created else 'ya existía'}")
    
    print(f"\n🎉 ¡Todos los datos han sido asignados a {juan.username}!")

if __name__ == '__main__':
    main()
