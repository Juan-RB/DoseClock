"""
Validation functions for DoseClock.
Handles state validation and automatic status updates.
"""

from datetime import timedelta
from django.utils import timezone


def validate_and_update_doses():
    """
    Check all pending doses and update their status if needed.
    Marks doses as 'no_tomada' if grace period has passed.

    Returns:
        dict: Update statistics
    """
    from medicamentos.models import Toma
    from django.conf import settings

    grace_minutes = settings.DOSECLOCK_SETTINGS.get('AUTO_MISS_MINUTES', 20)
    cutoff_time = timezone.now() - timedelta(minutes=grace_minutes)

    # Find pending doses past grace period
    overdue_doses = Toma.objects.filter(
        estado='pendiente',
        hora_programada__lt=cutoff_time
    )

    updated_count = overdue_doses.update(estado='no_tomada')

    return {
        'checked': True,
        'updated_count': updated_count,
        'cutoff_time': cutoff_time
    }


def confirm_dose(dose, confirmation_time=None):
    """
    Confirm a dose and determine its status.

    Args:
        dose: Toma model instance
        confirmation_time: datetime of confirmation (defaults to now)

    Returns:
        dict: Confirmation result
    """
    from medicamentos.models import Toma
    from django.conf import settings
    from .calculos_tomas import can_confirm_dose

    if confirmation_time is None:
        confirmation_time = timezone.now()

    grace_minutes = settings.DOSECLOCK_SETTINGS.get('AUTO_MISS_MINUTES', 20)

    # Determine status based on confirmation time
    deadline = dose.hora_programada + timedelta(minutes=grace_minutes)

    if confirmation_time <= deadline:
        new_status = 'confirmada'
    else:
        new_status = 'tarde'

    # Update dose
    dose.hora_confirmada = confirmation_time
    dose.estado = new_status
    dose.save()

    return {
        'success': True,
        'dose_id': str(dose.id),
        'new_status': new_status,
        'confirmation_time': confirmation_time,
        'was_on_time': new_status == 'confirmada'
    }


def validate_treatment_dates(treatment):
    """
    Validate treatment start and end dates.

    Args:
        treatment: Tratamiento model instance

    Returns:
        dict: Validation result
    """
    errors = []

    # Check start date is not in distant past
    if treatment.fecha_hora_inicio < timezone.now() - timedelta(days=365):
        errors.append("La fecha de inicio no puede ser de hace mas de un anno")

    # Check duration makes sense
    if treatment.duracion_dias and treatment.duracion_dias > 365 * 5:
        errors.append("La duracion no puede exceder 5 annos")

    # Check frequency is reasonable
    if treatment.frecuencia_horas < 0.5:
        errors.append("La frecuencia debe ser de al menos 30 minutos")

    if treatment.frecuencia_horas > 168:  # 1 week
        errors.append("La frecuencia no puede exceder una semana")

    return {
        'valid': len(errors) == 0,
        'errors': errors
    }


def validate_medication_name(name):
    """
    Validate medication name.

    Args:
        name: Medication name string

    Returns:
        dict: Validation result
    """
    errors = []

    if not name or len(name.strip()) < 2:
        errors.append("El nombre debe tener al menos 2 caracteres")

    if len(name) > 200:
        errors.append("El nombre no puede exceder 200 caracteres")

    return {
        'valid': len(errors) == 0,
        'errors': errors
    }


def validate_color_code(color):
    """
    Validate hex color code.

    Args:
        color: Color string (should be hex format #RRGGBB)

    Returns:
        dict: Validation result
    """
    if not color:
        return {'valid': True, 'errors': []}

    import re
    hex_pattern = re.compile(r'^#[0-9A-Fa-f]{6}$')

    if not hex_pattern.match(color):
        return {
            'valid': False,
            'errors': ["El color debe estar en formato hexadecimal (#RRGGBB)"]
        }

    return {'valid': True, 'errors': []}


def check_confirmation_window(dose):
    """
    Check if confirmation is currently allowed for a dose.

    Args:
        dose: Toma model instance

    Returns:
        dict: Window status information
    """
    from django.conf import settings

    now = timezone.now()
    window_minutes = settings.DOSECLOCK_SETTINGS.get('CONFIRM_WINDOW_MINUTES', 5)
    grace_minutes = settings.DOSECLOCK_SETTINGS.get('AUTO_MISS_MINUTES', 20)

    window_start = dose.hora_programada - timedelta(minutes=window_minutes)
    grace_end = dose.hora_programada + timedelta(minutes=grace_minutes)

    # Determine current state
    if now < window_start:
        minutes_until = int((window_start - now).total_seconds() / 60)
        return {
            'can_confirm': False,
            'reason': 'too_early',
            'minutes_until_window': minutes_until,
            'message': f"Podras confirmar en {minutes_until} minutos"
        }

    if now <= grace_end:
        if now <= dose.hora_programada:
            return {
                'can_confirm': True,
                'reason': 'in_window',
                'is_on_time': True,
                'message': "Puedes confirmar la toma ahora!"
            }
        else:
            minutes_late = int((now - dose.hora_programada).total_seconds() / 60)
            return {
                'can_confirm': True,
                'reason': 'grace_period',
                'is_on_time': False,
                'minutes_late': minutes_late,
                'message': f"Estas {minutes_late} minutos tarde, pero aun puedes confirmar"
            }

    # Past grace period
    return {
        'can_confirm': True,  # Can still confirm, but will be marked late
        'reason': 'late',
        'is_on_time': False,
        'minutes_late': int((now - dose.hora_programada).total_seconds() / 60),
        'message': "Confirmacion tardia - se registrara como toma tardia"
    }


def get_treatment_status_summary(treatment):
    """
    Get a summary of treatment adherence.

    Args:
        treatment: Tratamiento model instance

    Returns:
        dict: Adherence statistics
    """
    from medicamentos.models import Toma

    doses = Toma.objects.filter(tratamiento=treatment)

    total = doses.count()
    if total == 0:
        return {
            'total_doses': 0,
            'confirmed_on_time': 0,
            'confirmed_late': 0,
            'missed': 0,
            'pending': 0,
            'adherence_rate': 100.0
        }

    confirmed = doses.filter(estado='confirmada').count()
    late = doses.filter(estado='tarde').count()
    missed = doses.filter(estado='no_tomada').count()
    pending = doses.filter(estado='pendiente').count()

    # Calculate adherence (confirmed + late as taken)
    completed = total - pending
    if completed > 0:
        adherence_rate = ((confirmed + late) / completed) * 100
    else:
        adherence_rate = 100.0

    return {
        'total_doses': total,
        'confirmed_on_time': confirmed,
        'confirmed_late': late,
        'missed': missed,
        'pending': pending,
        'adherence_rate': round(adherence_rate, 1)
    }


def validate_first_dose_config(is_now, previous_time=None):
    """
    Validate first dose configuration when creating treatment.

    Args:
        is_now: Boolean - if first dose is right now
        previous_time: datetime - when medication was last taken (if applicable)

    Returns:
        dict: Validation result with computed start time
    """
    now = timezone.now()

    if is_now:
        return {
            'valid': True,
            'start_time': now,
            'errors': []
        }

    if previous_time is None:
        return {
            'valid': False,
            'errors': ["Debe indicar la hora de la ultima toma"]
        }

    if previous_time > now:
        return {
            'valid': False,
            'errors': ["La hora de la ultima toma no puede ser en el futuro"]
        }

    if previous_time < now - timedelta(days=7):
        return {
            'valid': False,
            'errors': ["La ultima toma no puede ser de hace mas de 7 dias"]
        }

    return {
        'valid': True,
        'start_time': previous_time,
        'errors': []
    }
