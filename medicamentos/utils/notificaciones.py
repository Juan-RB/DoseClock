"""
Notification management functions for DoseClock.
Handles scheduling and sending notifications.
"""

from datetime import timedelta
from django.utils import timezone


def create_dose_notifications(dose, reminder_minutes=5):
    """
    Create notification records for a dose.
    
    Args:
        dose: Toma model instance
        reminder_minutes: Minutes before dose for reminder notification
    
    Returns:
        list: Created Notificacion instances
    """
    from medicamentos.models import Notificacion, ConfiguracionUsuario
    
    notifications = []
    
    # Main notification at dose time
    main_notification = Notificacion.objects.create(
        toma=dose,
        tipo='principal',
        hora_programada=dose.hora_programada,
        enviada=False
    )
    notifications.append(main_notification)
    
    # Check if reminder is enabled in configuration
    config = get_user_config()
    if config and config.recordatorio_anticipado:
        reminder_time = dose.hora_programada - timedelta(minutes=reminder_minutes)
        
        # Only create reminder if it's in the future
        if reminder_time > timezone.now():
            reminder_notification = Notificacion.objects.create(
                toma=dose,
                tipo='recordatorio',
                hora_programada=reminder_time,
                enviada=False
            )
            notifications.append(reminder_notification)
    
    return notifications


def get_pending_notifications():
    """
    Get all pending notifications that should be sent.
    
    Returns:
        QuerySet: Notificacion instances that are due
    """
    from medicamentos.models import Notificacion
    
    now = timezone.now()
    
    return Notificacion.objects.filter(
        enviada=False,
        hora_programada__lte=now,
        toma__tratamiento__estado='activo'
    ).select_related('toma', 'toma__tratamiento', 'toma__tratamiento__medicamento')


def mark_notification_sent(notification):
    """
    Mark a notification as sent.
    
    Args:
        notification: Notificacion model instance
    
    Returns:
        Notificacion: Updated instance
    """
    notification.enviada = True
    notification.fecha_envio = timezone.now()
    notification.save()
    return notification


def get_notification_data(notification):
    """
    Get formatted data for displaying a notification.
    
    Args:
        notification: Notificacion model instance
    
    Returns:
        dict: Notification display data
    """
    dose = notification.toma
    treatment = dose.tratamiento
    medication = treatment.medicamento
    
    if notification.tipo == 'principal':
        title = f"¡Es hora de tomar {medication.nombre}!"
        body = "Toca para confirmar la toma."
    else:
        title = f"Recordatorio: {medication.nombre}"
        body = f"Tu medicamento estó¡ programado en 5 minutos."
    
    return {
        'title': title,
        'body': body,
        'icon': medication.icono or 'pill',
        'color': medication.color or '#007bff',
        'dose_id': str(dose.id),
        'medication_name': medication.nombre,
        'scheduled_time': dose.hora_programada.isoformat(),
        'notification_type': notification.tipo,
        'tag': f"dose-{dose.id}",
        'requireInteraction': True,
        'actions': [
            {'action': 'confirm', 'title': 'Confirmar toma'},
            {'action': 'dismiss', 'title': 'Descartar'}
        ]
    }


def get_user_config():
    """
    Get or create user configuration.
    
    Returns:
        ConfiguracionUsuario: User configuration instance
    """
    from medicamentos.models import ConfiguracionUsuario
    
    config = ConfiguracionUsuario.objects.first()
    if not config:
        config = ConfiguracionUsuario.objects.create()
    return config


def should_send_notification(notification):
    """
    Check if a notification should be sent based on configuration.
    
    Args:
        notification: Notificacion model instance
    
    Returns:
        bool: True if notification should be sent
    """
    config = get_user_config()
    
    # Check if notifications are enabled
    if not config.notificaciones_activas:
        return False
    
    # Check if treatment is active
    if notification.toma.tratamiento.estado != 'activo':
        return False
    
    # Check if already sent
    if notification.enviada:
        return False
    
    # Check if it's time
    if notification.hora_programada > timezone.now():
        return False
    
    return True


def cancel_dose_notifications(dose):
    """
    Cancel all pending notifications for a dose.
    
    Args:
        dose: Toma model instance
    
    Returns:
        int: Number of cancelled notifications
    """
    from medicamentos.models import Notificacion
    
    count = Notificacion.objects.filter(
        toma=dose,
        enviada=False
    ).delete()[0]
    
    return count


def get_notification_schedule():
    """
    Get upcoming notification schedule for display.
    
    Returns:
        list: Upcoming notifications with timing info
    """
    from medicamentos.models import Notificacion
    
    now = timezone.now()
    future_limit = now + timedelta(hours=24)
    
    notifications = Notificacion.objects.filter(
        enviada=False,
        hora_programada__range=(now, future_limit),
        toma__tratamiento__estado='activo'
    ).select_related(
        'toma', 
        'toma__tratamiento', 
        'toma__tratamiento__medicamento'
    ).order_by('hora_programada')
    
    schedule = []
    for notification in notifications:
        delta = notification.hora_programada - now
        schedule.append({
            'notification': notification,
            'medication': notification.toma.tratamiento.medicamento,
            'scheduled_time': notification.hora_programada,
            'minutes_until': int(delta.total_seconds() / 60),
            'type': notification.tipo
        })
    
    return schedule
