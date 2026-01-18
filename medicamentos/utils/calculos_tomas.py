"""
Calculation functions for dose scheduling.
All functions are modular and use functional programming approach.
"""

from datetime import timedelta
from django.utils import timezone
from decimal import Decimal


def calculate_next_dose(treatment, last_dose=None):
    """
    Calculate the next scheduled dose time based on treatment settings.
    
    Args:
        treatment: Tratamiento model instance
        last_dose: Toma model instance (optional, last registered dose)
    
    Returns:
        datetime: Next scheduled dose time
    """
    frequency_hours = float(treatment.frecuencia_horas)
    
    if last_dose is None:
        # First dose - use treatment start time
        return treatment.fecha_hora_inicio
    
    if treatment.modo_calculo == 'programada':
        # Calculate from scheduled time
        base_time = last_dose.hora_programada
    else:
        # Calculate from confirmation time (or scheduled if not confirmed)
        base_time = last_dose.hora_confirmada or last_dose.hora_programada
    
    return base_time + timedelta(hours=frequency_hours)


def calculate_all_future_doses(treatment, count=10):
    """
    Calculate multiple future doses for a treatment.
    
    Args:
        treatment: Tratamiento model instance
        count: Number of future doses to calculate
    
    Returns:
        list: List of datetime objects for scheduled doses
    """
    doses = []
    frequency_hours = float(treatment.frecuencia_horas)
    
    # Get last confirmed dose or start from treatment beginning
    from medicamentos.models import Toma
    last_dose = Toma.objects.filter(
        tratamiento=treatment
    ).order_by('-hora_programada').first()
    
    if last_dose:
        if treatment.modo_calculo == 'programada':
            base_time = last_dose.hora_programada
        else:
            base_time = last_dose.hora_confirmada or last_dose.hora_programada
    else:
        base_time = treatment.fecha_hora_inicio
    
    # Generate future doses
    current_time = timezone.now()
    next_time = base_time
    
    # Find next dose after current time
    while next_time <= current_time:
        next_time += timedelta(hours=frequency_hours)
    
    # Generate requested number of doses
    for _ in range(count):
        # Check if dose is within treatment duration
        if not is_dose_within_treatment(treatment, next_time):
            break
        doses.append(next_time)
        next_time += timedelta(hours=frequency_hours)
    
    return doses


def is_dose_within_treatment(treatment, dose_time):
    """
    Check if a dose time falls within the treatment duration.
    
    Args:
        treatment: Tratamiento model instance
        dose_time: datetime to check
    
    Returns:
        bool: True if dose is within treatment period
    """
    if treatment.es_indefinido:
        return True
    
    if treatment.duracion_dias is None:
        return True
    
    end_time = treatment.fecha_hora_inicio + timedelta(days=treatment.duracion_dias)
    return dose_time <= end_time


def get_time_until_dose(dose_time):
    """
    Calculate time remaining until a scheduled dose.
    
    Args:
        dose_time: datetime of scheduled dose
    
    Returns:
        dict: Contains hours, minutes, seconds, and total_seconds
    """
    now = timezone.now()
    delta = dose_time - now
    
    if delta.total_seconds() < 0:
        return {
            'hours': 0,
            'minutes': 0,
            'seconds': 0,
            'total_seconds': 0,
            'is_past': True
        }
    
    total_seconds = int(delta.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    return {
        'hours': hours,
        'minutes': minutes,
        'seconds': seconds,
        'total_seconds': total_seconds,
        'is_past': False
    }


def can_confirm_dose(dose_time, window_minutes=5):
    """
    Check if a dose can be confirmed (within confirmation window).
    
    Args:
        dose_time: datetime of scheduled dose
        window_minutes: Minutes before dose time when confirmation is allowed
    
    Returns:
        bool: True if confirmation is allowed
    """
    now = timezone.now()
    window_start = dose_time - timedelta(minutes=window_minutes)
    
    # Can confirm from window_start onwards (including late confirmations)
    return now >= window_start


def should_auto_mark_missed(dose_time, grace_minutes=20):
    """
    Check if a dose should be automatically marked as missed.
    
    Args:
        dose_time: datetime of scheduled dose
        grace_minutes: Minutes after dose time before auto-marking as missed
    
    Returns:
        bool: True if dose should be marked as missed
    """
    now = timezone.now()
    deadline = dose_time + timedelta(minutes=grace_minutes)
    
    return now > deadline


def determine_dose_status(scheduled_time, confirmed_time=None, grace_minutes=20):
    """
    Determine the status of a dose based on times.
    
    Args:
        scheduled_time: datetime when dose was scheduled
        confirmed_time: datetime when dose was confirmed (or None)
        grace_minutes: Minutes allowed for on-time confirmation
    
    Returns:
        str: Status code ('pendiente', 'confirmada', 'tarde', 'no_tomada')
    """
    now = timezone.now()
    
    if confirmed_time is None:
        # Not confirmed yet
        if now > scheduled_time + timedelta(minutes=grace_minutes):
            return 'no_tomada'
        return 'pendiente'
    
    # Was confirmed - check if on time
    if confirmed_time <= scheduled_time + timedelta(minutes=grace_minutes):
        return 'confirmada'
    
    return 'tarde'


def format_countdown(total_seconds):
    """
    Format seconds into human-readable countdown string.
    
    Args:
        total_seconds: Total seconds remaining
    
    Returns:
        str: Formatted string (e.g., "2h 30m 15s")
    """
    if total_seconds <= 0:
        return "¡Ahora!"
    
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")
    
    return " ".join(parts)


def get_doses_for_date(treatment, target_date):
    """
    Get all scheduled doses for a specific date.
    
    Args:
        treatment: Tratamiento model instance
        target_date: date object to get doses for
    
    Returns:
        list: List of datetime objects for doses on that date
    """
    from datetime import datetime, time
    
    # Define start and end of the target date
    day_start = timezone.make_aware(
        datetime.combine(target_date, time.min)
    )
    day_end = timezone.make_aware(
        datetime.combine(target_date, time.max)
    )
    
    # Calculate all doses
    frequency_hours = float(treatment.frecuencia_horas)
    doses = []
    
    # Start from treatment beginning
    current_time = treatment.fecha_hora_inicio
    
    # Advance to the target date range
    while current_time < day_start:
        current_time += timedelta(hours=frequency_hours)
    
    # Collect doses within the day
    while current_time <= day_end:
        if is_dose_within_treatment(treatment, current_time):
            doses.append(current_time)
        current_time += timedelta(hours=frequency_hours)
    
    return doses
