"""
Views for DoseClock application.
All views use functional approach as per project requirements.
"""

import json
from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, FileResponse
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt

from .models import Medicamento, Tratamiento, Toma, Notificacion, ConfiguracionUsuario
from .forms import MedicamentoForm, TratamientoForm, ConfiguracionForm, ConfirmarTomaForm
from .utils.calculos_tomas import (
    calculate_next_dose,
    calculate_all_future_doses,
    get_time_until_dose,
    format_countdown,
    can_confirm_dose,
    get_doses_for_date
)
from .utils.notificaciones import (
    create_dose_notifications,
    get_user_config,
    get_notification_schedule
)
from .utils.backup import (
    create_backup,
    restore_backup,
    list_backups,
    delete_backup as delete_backup_file,
    get_backup_directory
)
from .utils.validaciones import (
    validate_and_update_doses,
    confirm_dose as confirm_dose_util,
    check_confirmation_window,
    get_treatment_status_summary
)


def get_context_base():
    """Get base context with user configuration."""
    config = get_user_config()
    return {
        'config': config,
        'modo_visual': config.modo_visual if config else 'minimalista',
        'paleta': config.paleta_colores if config else 'nude',
        'tamano_texto': config.tamano_texto if config else 'normal',
        'alto_contraste': config.alto_contraste if config else False,
    }


# ==================== DASHBOARD ====================

def dashboard(request):
    """Main dashboard view showing active treatments and upcoming doses."""
    # Update pending doses status
    validate_and_update_doses()
    
    context = get_context_base()
    
    # Get active treatments
    treatments = Tratamiento.objects.filter(
        estado='activo'
    ).select_related('medicamento')
    
    # Build dashboard cards
    cards = []
    for treatment in treatments:
        # Get next scheduled dose
        future_doses = calculate_all_future_doses(treatment, count=1)
        next_dose_time = future_doses[0] if future_doses else None
        
        # Get or create pending dose
        if next_dose_time:
            dose, created = Toma.objects.get_or_create(
                tratamiento=treatment,
                hora_programada=next_dose_time,
                defaults={'estado': 'pendiente'}
            )
            
            # Create notifications if new dose
            if created:
                create_dose_notifications(dose)
            
            time_info = get_time_until_dose(next_dose_time)
            window_status = check_confirmation_window(dose)
            
            cards.append({
                'treatment': treatment,
                'medication': treatment.medicamento,
                'next_dose': next_dose_time,
                'dose': dose,
                'countdown': format_countdown(time_info['total_seconds']),
                'time_info': time_info,
                'can_confirm': window_status['can_confirm'],
                'window_message': window_status['message'],
                'status_summary': get_treatment_status_summary(treatment)
            })
    
    # Sort by next dose time
    cards.sort(key=lambda x: x['next_dose'] if x['next_dose'] else timezone.now() + timedelta(days=365))
    
    context['cards'] = cards
    context['total_active'] = len(cards)
    
    return render(request, 'medicamentos/dashboard.html', context)


# ==================== MEDICAMENTOS ====================

def medicamentos_list(request):
    """List all medications."""
    context = get_context_base()
    context['medicamentos'] = Medicamento.objects.filter(activo=True)
    return render(request, 'medicamentos/medicamentos_list.html', context)


def medicamento_create(request):
    """Create new medication."""
    context = get_context_base()
    
    if request.method == 'POST':
        form = MedicamentoForm(request.POST)
        if form.is_valid():
            medicamento = form.save()
            messages.success(request, f'Medicamento "{medicamento.nombre}" creado correctamente.')
            return redirect('medicamentos:medicamentos_list')
    else:
        form = MedicamentoForm()
    
    context['form'] = form
    context['title'] = 'Nuevo Medicamento'
    return render(request, 'medicamentos/medicamento_form.html', context)


def medicamento_detail(request, pk):
    """View medication details."""
    context = get_context_base()
    medicamento = get_object_or_404(Medicamento, pk=pk)
    
    context['medicamento'] = medicamento
    context['tratamientos'] = medicamento.tratamientos.all()
    
    return render(request, 'medicamentos/medicamento_detail.html', context)


def medicamento_edit(request, pk):
    """Edit medication."""
    context = get_context_base()
    medicamento = get_object_or_404(Medicamento, pk=pk)
    
    if request.method == 'POST':
        form = MedicamentoForm(request.POST, instance=medicamento)
        if form.is_valid():
            form.save()
            messages.success(request, 'Medicamento actualizado correctamente.')
            return redirect('medicamentos:medicamento_detail', pk=pk)
    else:
        form = MedicamentoForm(instance=medicamento)
    
    context['form'] = form
    context['medicamento'] = medicamento
    context['title'] = 'Editar Medicamento'
    return render(request, 'medicamentos/medicamento_form.html', context)


def medicamento_delete(request, pk):
    """Delete medication preserving history."""
    medicamento = get_object_or_404(Medicamento, pk=pk)
    
    if request.method == 'POST':
        nombre = medicamento.nombre
        
        # Preserve historical data in treatments
        for tratamiento in medicamento.tratamientos.all():
            tratamiento.medicamento_nombre_historico = nombre
            tratamiento.save()
            
            # Preserve in doses too
            for toma in tratamiento.tomas.all():
                toma.medicamento_nombre_historico = nombre
                toma.save()
        
        # Soft delete - mark as inactive
        medicamento.activo = False
        medicamento.save()
        
        messages.success(request, f'Medicamento "{nombre}" eliminado. El historial se mantiene.')
        return redirect('medicamentos:medicamentos_list')
    
    context = get_context_base()
    context['medicamento'] = medicamento
    context['tratamientos_activos'] = medicamento.tratamientos.filter(estado='activo').count()
    context['total_tomas'] = Toma.objects.filter(tratamiento__medicamento=medicamento).count()
    return render(request, 'medicamentos/medicamento_confirm_delete.html', context)


# ==================== TRATAMIENTOS ====================

def tratamientos_list(request):
    """List all treatments."""
    context = get_context_base()
    context['tratamientos'] = Tratamiento.objects.select_related('medicamento').all()
    return render(request, 'medicamentos/tratamientos_list.html', context)


def tratamiento_create(request):
    """Create new treatment."""
    context = get_context_base()
    
    if request.method == 'POST':
        form = TratamientoForm(request.POST)
        if form.is_valid():
            tratamiento = form.save(commit=False)
            
            # Handle first dose configuration
            primera_toma_ahora = request.POST.get('primera_toma_ahora') == 'on'
            hora_ultima_toma = request.POST.get('hora_ultima_toma')
            
            if primera_toma_ahora:
                tratamiento.fecha_hora_inicio = timezone.now()
            elif hora_ultima_toma:
                tratamiento.fecha_hora_inicio = timezone.make_aware(
                    datetime.fromisoformat(hora_ultima_toma)
                )
            else:
                tratamiento.fecha_hora_inicio = timezone.now()
            
            tratamiento.save()
            
            # Create first dose
            first_dose = Toma.objects.create(
                tratamiento=tratamiento,
                hora_programada=tratamiento.fecha_hora_inicio,
                estado='pendiente'
            )
            create_dose_notifications(first_dose)
            
            messages.success(request, 'Tratamiento creado correctamente.')
            return redirect('medicamentos:dashboard')
    else:
        form = TratamientoForm()
    
    context['form'] = form
    context['title'] = 'Nuevo Tratamiento'
    return render(request, 'medicamentos/tratamiento_form.html', context)


def tratamiento_detail(request, pk):
    """View treatment details."""
    context = get_context_base()
    tratamiento = get_object_or_404(Tratamiento, pk=pk)
    
    context['tratamiento'] = tratamiento
    context['status_summary'] = get_treatment_status_summary(tratamiento)
    context['future_doses'] = calculate_all_future_doses(tratamiento, count=10)
    context['recent_doses'] = Toma.objects.filter(
        tratamiento=tratamiento
    ).order_by('-hora_programada')[:20]
    
    return render(request, 'medicamentos/tratamiento_detail.html', context)


def tratamiento_edit(request, pk):
    """Edit treatment."""
    context = get_context_base()
    tratamiento = get_object_or_404(Tratamiento, pk=pk)
    
    if request.method == 'POST':
        form = TratamientoForm(request.POST, instance=tratamiento)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tratamiento actualizado correctamente.')
            return redirect('medicamentos:tratamiento_detail', pk=pk)
    else:
        form = TratamientoForm(instance=tratamiento)
    
    context['form'] = form
    context['tratamiento'] = tratamiento
    context['title'] = 'Editar Tratamiento'
    return render(request, 'medicamentos/tratamiento_form.html', context)


def tratamiento_toggle_pause(request, pk):
    """Toggle treatment pause status."""
    tratamiento = get_object_or_404(Tratamiento, pk=pk)
    
    if tratamiento.estado == 'activo':
        tratamiento.estado = 'pausado'
        messages.info(request, 'Tratamiento pausado.')
    else:
        tratamiento.estado = 'activo'
        messages.success(request, 'Tratamiento reanudado.')
    
    tratamiento.save()
    return redirect('medicamentos:tratamiento_detail', pk=pk)


def tratamiento_finalizar(request, pk):
    """End a treatment."""
    tratamiento = get_object_or_404(Tratamiento, pk=pk)
    
    if request.method == 'POST':
        tratamiento.estado = 'finalizado'
        tratamiento.save()
        messages.success(request, 'Tratamiento finalizado.')
        return redirect('medicamentos:dashboard')
    
    context = get_context_base()
    context['tratamiento'] = tratamiento
    return render(request, 'medicamentos/tratamiento_confirm_end.html', context)


def tratamiento_delete(request, pk):
    """Delete treatment preserving history."""
    tratamiento = get_object_or_404(Tratamiento, pk=pk)
    
    if request.method == 'POST':
        # Get medication name before potential deletion
        nombre_medicamento = tratamiento.nombre_medicamento
        frecuencia = tratamiento.frecuencia_horas
        
        # Preserve historical data in all doses
        for toma in tratamiento.tomas.all():
            toma.medicamento_nombre_historico = nombre_medicamento
            toma.tratamiento_frecuencia_historica = frecuencia
            toma.tratamiento = None  # Unlink but preserve
            toma.save()
        
        # Delete the treatment (doses are preserved)
        tratamiento.delete()
        
        messages.success(request, f'Tratamiento de "{nombre_medicamento}" eliminado. El historial de tomas se mantiene.')
        return redirect('medicamentos:tratamientos_list')
    
    context = get_context_base()
    context['tratamiento'] = tratamiento
    context['total_tomas'] = tratamiento.tomas.count()
    context['tomas_confirmadas'] = tratamiento.tomas.filter(estado__in=['confirmada', 'tarde']).count()
    return render(request, 'medicamentos/tratamiento_confirm_delete.html', context)
    return render(request, 'medicamentos/tratamiento_confirm_end.html', context)


# ==================== TOMAS ====================

def historial_tomas(request):
    """View all dose history."""
    context = get_context_base()
    
    # Filter options
    estado_filter = request.GET.get('estado', '')
    medicamento_filter = request.GET.get('medicamento', '')
    
    tomas = Toma.objects.select_related(
        'tratamiento', 'tratamiento__medicamento'
    ).order_by('-hora_programada')
    
    if estado_filter:
        tomas = tomas.filter(estado=estado_filter)
    
    if medicamento_filter:
        tomas = tomas.filter(tratamiento__medicamento_id=medicamento_filter)
    
    context['tomas'] = tomas[:100]  # Limit to 100 most recent
    context['medicamentos'] = Medicamento.objects.filter(activo=True)
    context['estado_filter'] = estado_filter
    context['medicamento_filter'] = medicamento_filter
    
    return render(request, 'medicamentos/historial_tomas.html', context)


def historial_tratamiento(request, tratamiento_pk):
    """View dose history for specific treatment."""
    context = get_context_base()
    tratamiento = get_object_or_404(Tratamiento, pk=tratamiento_pk)
    
    context['tratamiento'] = tratamiento
    context['tomas'] = Toma.objects.filter(
        tratamiento=tratamiento
    ).order_by('-hora_programada')
    context['status_summary'] = get_treatment_status_summary(tratamiento)
    
    return render(request, 'medicamentos/historial_tratamiento.html', context)


def confirmar_toma(request, pk):
    """Confirm a dose."""
    toma = get_object_or_404(Toma, pk=pk)
    
    if request.method == 'POST':
        result = confirm_dose_util(toma)
        
        if result['was_on_time']:
            messages.success(request, '?Toma confirmada a tiempo!')
        else:
            messages.warning(request, 'Toma confirmada (tard??a).')
        
        return redirect('medicamentos:dashboard')
    
    context = get_context_base()
    context['toma'] = toma
    context['window_status'] = check_confirmation_window(toma)
    
    return render(request, 'medicamentos/confirmar_toma.html', context)


# ==================== CALENDARIO ====================

def calendario(request):
    """Calendar view."""
    context = get_context_base()
    return render(request, 'medicamentos/calendario.html', context)


def calendario_datos(request):
    """API endpoint for calendar data."""
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')
    
    try:
        start_date = datetime.fromisoformat(start_str.replace('Z', '+00:00')).date()
        end_date = datetime.fromisoformat(end_str.replace('Z', '+00:00')).date()
    except (ValueError, AttributeError):
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=30)
    
    events = []
    
    # Get registered doses
    tomas = Toma.objects.filter(
        hora_programada__date__range=(start_date, end_date)
    ).select_related('tratamiento', 'tratamiento__medicamento')
    
    for toma in tomas:
        events.append({
            'id': str(toma.id),
            'title': toma.tratamiento.medicamento.nombre,
            'start': toma.hora_programada.isoformat(),
            'backgroundColor': toma.color_estado,
            'borderColor': toma.color_estado,
            'extendedProps': {
                'status': toma.estado,
                'medication': toma.tratamiento.medicamento.nombre,
                'treatment_id': str(toma.tratamiento.id)
            }
        })
    
    return JsonResponse(events, safe=False)


# ==================== CONFIGURACI??N ====================

def configuracion(request):
    """User configuration view."""
    context = get_context_base()
    config = get_user_config()
    
    if request.method == 'POST':
        form = ConfiguracionForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuraci??n guardada.')
            return redirect('medicamentos:configuracion')
    else:
        form = ConfiguracionForm(instance=config)
    
    context['form'] = form
    return render(request, 'medicamentos/configuracion.html', context)


# ==================== TELEGRAM ====================

def telegram_vincular(request):
    """Link Telegram account."""
    from .utils.telegram_bot import get_bot_updates, send_welcome_message, verify_bot_token
    
    context = get_context_base()
    config = get_user_config()
    
    # Verify bot is working
    bot_info = verify_bot_token()
    context['bot_info'] = bot_info
    context['bot_username'] = bot_info.get('bot_username', 'DoseClock_bot')
    
    if request.method == 'POST':
        # Get recent messages to find chat_id
        updates = get_bot_updates()
        
        if updates:
            # Get the most recent message
            for update in reversed(updates):
                message = update.get('message', {})
                chat = message.get('chat', {})
                chat_id = chat.get('id')
                user_name = chat.get('first_name', '')
                
                if chat_id:
                    # Save chat_id
                    config.telegram_chat_id = str(chat_id)
                    config.telegram_activo = True
                    config.telegram_vinculado = timezone.now()
                    config.save()
                    
                    # Send welcome message
                    send_welcome_message(chat_id, user_name)
                    
                    messages.success(request, f'Telegram vinculado correctamente! Chat ID: {chat_id}')
                    return redirect('medicamentos:configuracion')
            
            messages.warning(request, 'No se encontro ningun mensaje. Envia un mensaje al bot primero.')
        else:
            messages.error(request, 'No se encontraron mensajes. Asegurate de enviar un mensaje al bot.')
    
    return render(request, 'medicamentos/telegram_vincular.html', context)


def telegram_desvincular(request):
    """Unlink Telegram account."""
    if request.method == 'POST':
        config = get_user_config()
        config.telegram_chat_id = None
        config.telegram_activo = False
        config.telegram_vinculado = None
        config.save()
        
        messages.success(request, 'Telegram desvinculado correctamente.')
    
    return redirect('medicamentos:configuracion')


def telegram_test(request):
    """Send test message to linked Telegram."""
    from .utils.telegram_bot import send_telegram_message
    
    config = get_user_config()
    
    if config.telegram_chat_id and config.telegram_activo:
        result = send_telegram_message(
            config.telegram_chat_id,
            "<b>🔔 Mensaje de Prueba</b>\n\n"
            "Este es un mensaje de prueba de DoseClock.\n"
            "Si recibes esto, la integracion funciona correctamente! ✅"
        )
        
        if result['success']:
            messages.success(request, 'Mensaje de prueba enviado!')
        else:
            messages.error(request, f'Error al enviar: {result.get("error")}')
    else:
        messages.warning(request, 'Telegram no esta vinculado o activo.')
    
    return redirect('medicamentos:configuracion')


@csrf_exempt
def api_telegram_check_reminders(request):
    """
    API endpoint to check and send Telegram reminders.
    Called periodically by JavaScript (every 60 seconds).
    
    Logic:
    - 5 minutes before: Send advance reminder if user has option enabled
    - Exact time (±2 min window): Always send main reminder
    """
    from .utils.telegram_bot import send_dose_reminder, send_upcoming_reminder
    
    now = timezone.now()
    config = get_user_config()
    
    # Check if Telegram is configured
    if not config or not config.telegram_activo or not config.telegram_chat_id:
        return JsonResponse({
            'success': False,
            'message': 'Telegram no configurado o inactivo',
            'reminders_sent': 0
        })
    
    chat_id = config.telegram_chat_id
    enviar_anticipado = config.recordatorio_anticipado  # 5 min antes
    
    # Get pending doses for the next 10 minutes
    fecha_inicio = now - timedelta(minutes=2)  # Small buffer for exact time
    fecha_limite = now + timedelta(minutes=10)
    
    tomas_pendientes = Toma.objects.filter(
        estado='pendiente',
        hora_programada__gte=fecha_inicio,
        hora_programada__lte=fecha_limite
    ).select_related('tratamiento', 'tratamiento__medicamento')
    
    enviados_anticipados = 0
    enviados_exactos = 0
    resultados = []
    
    for toma in tomas_pendientes:
        if not toma.tratamiento or not toma.tratamiento.medicamento:
            continue
        
        nombre_medicamento = toma.nombre_medicamento
        hora_toma = toma.hora_programada
        minutos_hasta_toma = (hora_toma - now).total_seconds() / 60
        
        # Check if we should send 5-minute advance reminder
        # Send if between 4-6 minutes before (to account for timing)
        if enviar_anticipado and 4 <= minutos_hasta_toma <= 6:
            # Check if advance reminder already sent
            notif_anticipada = Notificacion.objects.filter(
                toma=toma,
                tipo='recordatorio',
                enviada=True
            ).exists()
            
            if not notif_anticipada:
                result = send_upcoming_reminder(chat_id, nombre_medicamento, 5)
                
                if result.get('success'):
                    # Mark as sent
                    Notificacion.objects.create(
                        toma=toma,
                        tipo='recordatorio',
                        hora_programada=hora_toma - timedelta(minutes=5),
                        enviada=True,
                        fecha_envio=now
                    )
                    enviados_anticipados += 1
                    resultados.append({
                        'medicamento': nombre_medicamento,
                        'tipo': 'anticipado',
                        'enviado': True
                    })
        
        # Check if we should send exact time reminder
        # Send if within 2 minutes of scheduled time (before or after)
        if -2 <= minutos_hasta_toma <= 2:
            # Check if main reminder already sent
            notif_principal = Notificacion.objects.filter(
                toma=toma,
                tipo='principal',
                enviada=True
            ).exists()
            
            if not notif_principal:
                result = send_dose_reminder(
                    chat_id, 
                    nombre_medicamento, 
                    hora_toma,
                    str(toma.id)
                )
                
                if result.get('success'):
                    # Mark as sent
                    Notificacion.objects.create(
                        toma=toma,
                        tipo='principal',
                        hora_programada=hora_toma,
                        enviada=True,
                        fecha_envio=now
                    )
                    enviados_exactos += 1
                    resultados.append({
                        'medicamento': nombre_medicamento,
                        'tipo': 'exacto',
                        'enviado': True
                    })
    
    return JsonResponse({
        'success': True,
        'message': f'Verificación completada',
        'timestamp': now.isoformat(),
        'reminders_sent': {
            'anticipados': enviados_anticipados,
            'exactos': enviados_exactos,
            'total': enviados_anticipados + enviados_exactos
        },
        'detalles': resultados
    })


# ==================== BACKUPS ====================

def backup_list(request):
    """List available backups."""
    context = get_context_base()
    context['backups'] = list_backups()
    return render(request, 'medicamentos/backup_list.html', context)


def backup_create(request):
    """Create new backup."""
    if request.method == 'POST':
        result = create_backup()
        if result['success']:
            messages.success(request, f'Backup creado: {result["filename"]}')
        else:
            messages.error(request, 'Error al crear backup.')
    
    return redirect('medicamentos:backup_list')


def backup_restore(request, filename):
    """Restore from backup."""
    backup_dir = get_backup_directory()
    filepath = backup_dir / filename
    
    if request.method == 'POST':
        result = restore_backup(filepath)
        if result['success']:
            messages.success(request, 'Backup restaurado correctamente.')
        else:
            messages.error(request, f'Error: {result.get("error", "Unknown error")}')
        return redirect('medicamentos:backup_list')
    
    context = get_context_base()
    context['filename'] = filename
    return render(request, 'medicamentos/backup_confirm_restore.html', context)


def backup_delete(request, filename):
    """Delete a backup."""
    if request.method == 'POST':
        backup_dir = get_backup_directory()
        filepath = backup_dir / filename
        result = delete_backup_file(filepath)
        
        if result['success']:
            messages.success(request, 'Backup eliminado.')
        else:
            messages.error(request, f'Error: {result.get("error", "Unknown error")}')
    
    return redirect('medicamentos:backup_list')


def backup_download(request, filename):
    """Download a backup file."""
    backup_dir = get_backup_directory()
    filepath = backup_dir / filename
    
    if filepath.exists():
        return FileResponse(
            open(filepath, 'rb'),
            as_attachment=True,
            filename=filename
        )
    
    messages.error(request, 'Archivo no encontrado.')
    return redirect('medicamentos:backup_list')


# ==================== API ENDPOINTS ====================

def api_proximas_tomas(request):
    """API: Get upcoming doses for 7 days (for pillbox visualization)."""
    validate_and_update_doses()
    
    treatments = Tratamiento.objects.filter(estado='activo')
    doses_data = []
    
    # Get doses for next 7 days
    now = timezone.now()
    end_date = now + timedelta(days=7)
    
    for treatment in treatments:
        # Get more doses for the pillbox (7 days worth)
        future_doses = calculate_all_future_doses(treatment, count=50)
        
        for dose_time in future_doses:
            # Only include doses within next 7 days
            if dose_time > end_date:
                break
                
            time_info = get_time_until_dose(dose_time)
            
            # Check if dose exists in DB
            dose = Toma.objects.filter(
                tratamiento=treatment,
                hora_programada=dose_time
            ).first()
            
            doses_data.append({
                'treatment_id': str(treatment.id),
                'medication_name': treatment.medicamento.nombre,
                'medication_color': treatment.medicamento.color,
                'scheduled_time': dose_time.isoformat(),
                'countdown_seconds': time_info['total_seconds'],
                'countdown_formatted': format_countdown(time_info['total_seconds']),
                'can_confirm': can_confirm_dose(dose_time) if dose else False,
                'dose_id': str(dose.id) if dose else None,
                'status': dose.estado if dose else 'pendiente'
            })
    
    # Sort by time
    doses_data.sort(key=lambda x: x['scheduled_time'])
    
    return JsonResponse({'doses': doses_data})


@csrf_exempt
def api_confirmar_toma(request, pk):
    """API: Confirm a dose."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    toma = get_object_or_404(Toma, pk=pk)
    result = confirm_dose_util(toma)
    
    return JsonResponse(result)


def api_notificaciones_pendientes(request):
    """API: Get pending notifications."""
    schedule = get_notification_schedule()
    
    notifications = []
    for item in schedule:
        notifications.append({
            'id': str(item['notification'].id),
            'medication': item['medication'].nombre,
            'scheduled_time': item['scheduled_time'].isoformat(),
            'minutes_until': item['minutes_until'],
            'type': item['type']
        })
    
    return JsonResponse({'notifications': notifications})


def api_actualizar_estados(request):
    """API: Update dose statuses (called periodically)."""
    result = validate_and_update_doses()
    return JsonResponse(result)


# ==================== SERVICE WORKER ====================

def service_worker(request):
    """Serve the service worker JavaScript file."""
    sw_content = """
// DoseClock Service Worker
const CACHE_NAME = 'doseclock-v1';

self.addEventListener('install', (event) => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(clients.claim());
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    
    if (event.action === 'confirm') {
        const doseId = event.notification.data.doseId;
        // Send confirmation to server
        fetch(`/api/confirmar-toma/${doseId}/`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
    }
    
    // Focus or open the app
    event.waitUntil(
        clients.matchAll({type: 'window'}).then((clientList) => {
            if (clientList.length > 0) {
                return clientList[0].focus();
            }
            return clients.openWindow('/');
        })
    );
});
"""
    return HttpResponse(sw_content, content_type='application/javascript')

