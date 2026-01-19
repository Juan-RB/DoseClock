"""
Backup management functions for DoseClock.
Handles local database backups.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from django.conf import settings
from django.utils import timezone
from django.core.serializers import serialize
from django.core.serializers.json import DjangoJSONEncoder


def get_backup_directory():
    """
    Get or create the backup directory.
    
    Returns:
        Path: Backup directory path
    """
    backup_dir = Path(settings.BASE_DIR) / 'backups'
    backup_dir.mkdir(exist_ok=True)
    return backup_dir


def create_backup(backup_name=None):
    """
    Create a complete backup of all data.
    
    Args:
        backup_name: Optional custom name for backup file
    
    Returns:
        dict: Backup result with file path and stats
    """
    from medicamentos.models import (
        Medicamento, 
        Tratamiento, 
        Toma, 
        Notificacion, 
        ConfiguracionUsuario
    )
    
    backup_dir = get_backup_directory()
    
    # Generate backup filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = backup_name or f"doseclock_backup_{timestamp}.json"
    filepath = backup_dir / filename
    
    # Collect all data
    backup_data = {
        'version': '1.0',
        'created_at': timezone.now().isoformat(),
        'data': {
            'medicamentos': json.loads(serialize('json', Medicamento.objects.all())),
            'tratamientos': json.loads(serialize('json', Tratamiento.objects.all())),
            'tomas': json.loads(serialize('json', Toma.objects.all())),
            'notificaciones': json.loads(serialize('json', Notificacion.objects.all())),
            'configuracion': json.loads(serialize('json', ConfiguracionUsuario.objects.all())),
        },
        'stats': {
            'medicamentos_count': Medicamento.objects.count(),
            'tratamientos_count': Tratamiento.objects.count(),
            'tomas_count': Toma.objects.count(),
        }
    }
    
    # Write backup file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, cls=DjangoJSONEncoder, indent=2, ensure_ascii=False)
    
    # Update last backup time in configuration
    update_last_backup_time()
    
    return {
        'success': True,
        'filepath': str(filepath),
        'filename': filename,
        'size_bytes': os.path.getsize(filepath),
        'stats': backup_data['stats']
    }


def restore_backup(filepath):
    """
    Restore data from a backup file.
    
    Args:
        filepath: Path to backup file
    
    Returns:
        dict: Restore result with stats
    """
    from django.core.serializers import deserialize
    from medicamentos.models import (
        Medicamento, 
        Tratamiento, 
        Toma, 
        Notificacion, 
        ConfiguracionUsuario
    )
    
    # Validate backup file
    validation = validate_backup(filepath)
    if not validation['valid']:
        return {
            'success': False,
            'error': validation['error']
        }
    
    # Load backup data
    with open(filepath, 'r', encoding='utf-8') as f:
        backup_data = json.load(f)
    
    # Clear existing data (in correct order for foreign keys)
    Notificacion.objects.all().delete()
    Toma.objects.all().delete()
    Tratamiento.objects.all().delete()
    Medicamento.objects.all().delete()
    ConfiguracionUsuario.objects.all().delete()
    
    # Restore data in correct order
    restored_counts = {
        'medicamentos': 0,
        'tratamientos': 0,
        'tomas': 0,
        'notificaciones': 0,
        'configuracion': 0
    }
    
    # Restore medicamentos
    for obj in deserialize('json', json.dumps(backup_data['data']['medicamentos'])):
        obj.save()
        restored_counts['medicamentos'] += 1
    
    # Restore tratamientos
    for obj in deserialize('json', json.dumps(backup_data['data']['tratamientos'])):
        obj.save()
        restored_counts['tratamientos'] += 1
    
    # Restore tomas
    for obj in deserialize('json', json.dumps(backup_data['data']['tomas'])):
        obj.save()
        restored_counts['tomas'] += 1
    
    # Restore notificaciones
    for obj in deserialize('json', json.dumps(backup_data['data']['notificaciones'])):
        obj.save()
        restored_counts['notificaciones'] += 1
    
    # Restore configuracion
    for obj in deserialize('json', json.dumps(backup_data['data']['configuracion'])):
        obj.save()
        restored_counts['configuracion'] += 1
    
    return {
        'success': True,
        'restored_counts': restored_counts,
        'backup_date': backup_data['created_at']
    }


def validate_backup(filepath):
    """
    Validate a backup file before restoration.
    
    Args:
        filepath: Path to backup file
    
    Returns:
        dict: Validation result
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        # Check required fields
        required_fields = ['version', 'created_at', 'data']
        for field in required_fields:
            if field not in backup_data:
                return {
                    'valid': False,
                    'error': f"Campo requerido '{field}' no encontrado"
                }
        
        # Check data structure
        required_data = ['medicamentos', 'tratamientos', 'tomas', 'notificaciones', 'configuracion']
        for data_type in required_data:
            if data_type not in backup_data['data']:
                return {
                    'valid': False,
                    'error': f"Datos de '{data_type}' no encontrados"
                }
        
        return {
            'valid': True,
            'version': backup_data['version'],
            'created_at': backup_data['created_at'],
            'stats': backup_data.get('stats', {})
        }
        
    except json.JSONDecodeError:
        return {
            'valid': False,
            'error': "Archivo JSON invalido"
        }
    except FileNotFoundError:
        return {
            'valid': False,
            'error': "Archivo no encontrado"
        }
    except Exception as e:
        return {
            'valid': False,
            'error': str(e)
        }


def list_backups():
    """
    List all available backup files.
    
    Returns:
        list: Backup file information
    """
    backup_dir = get_backup_directory()
    backups = []
    
    for filepath in backup_dir.glob('*.json'):
        validation = validate_backup(filepath)
        
        backups.append({
            'filename': filepath.name,
            'filepath': str(filepath),
            'size_bytes': os.path.getsize(filepath),
            'modified': datetime.fromtimestamp(os.path.getmtime(filepath)),
            'valid': validation['valid'],
            'created_at': validation.get('created_at'),
            'stats': validation.get('stats', {})
        })
    
    # Sort by modification date (newest first)
    backups.sort(key=lambda x: x['modified'], reverse=True)
    
    return backups


def delete_backup(filepath):
    """
    Delete a backup file.
    
    Args:
        filepath: Path to backup file
    
    Returns:
        dict: Deletion result
    """
    try:
        os.remove(filepath)
        return {
            'success': True,
            'message': 'Backup eliminado correctamente'
        }
    except FileNotFoundError:
        return {
            'success': False,
            'error': 'Archivo no encontrado'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def should_run_auto_backup():
    """
    Check if automatic backup should run based on configuration.
    
    Returns:
        bool: True if auto backup should run
    """
    from medicamentos.models import ConfiguracionUsuario
    
    config = ConfiguracionUsuario.objects.first()
    if not config or not config.backup_automatico:
        return False
    
    if not config.ultimo_backup:
        return True
    
    from datetime import timedelta
    days_since_backup = (timezone.now() - config.ultimo_backup).days
    
    return days_since_backup >= config.frecuencia_backup_dias


def update_last_backup_time():
    """
    Update the last backup timestamp in configuration.
    """
    from medicamentos.models import ConfiguracionUsuario
    
    config = ConfiguracionUsuario.objects.first()
    if config:
        config.ultimo_backup = timezone.now()
        config.save()


def cleanup_old_backups(keep_count=10):
    """
    Remove old backup files, keeping only the most recent ones.
    
    Args:
        keep_count: Number of backups to keep
    
    Returns:
        int: Number of deleted backups
    """
    backups = list_backups()
    
    if len(backups) <= keep_count:
        return 0
    
    # Delete older backups
    deleted_count = 0
    for backup in backups[keep_count:]:
        result = delete_backup(backup['filepath'])
        if result['success']:
            deleted_count += 1
    
    return deleted_count
