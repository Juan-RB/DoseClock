"""
Management command to send Telegram reminders for upcoming doses.
Run with: python manage.py enviar_recordatorios_telegram

This should be run periodically (e.g., every minute via cron or Task Scheduler).
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from medicamentos.models import Toma, ConfiguracionUsuario, Notificacion
from medicamentos.utils.telegram_bot import (
    send_dose_reminder, 
    send_upcoming_reminder
)


class Command(BaseCommand):
    help = 'Envía recordatorios de medicamentos por Telegram'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué se enviaría sin enviar realmente',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now = timezone.now()
        
        self.stdout.write(f"\n{'='*50}")
        self.stdout.write(f"Verificando recordatorios - {now.strftime('%d/%m/%Y %H:%M:%S')}")
        self.stdout.write(f"{'='*50}\n")
        
        # Get user configuration
        config = ConfiguracionUsuario.objects.first()
        
        if not config:
            self.stdout.write(self.style.WARNING('No hay configuración de usuario'))
            return
        
        if not config.telegram_activo or not config.telegram_chat_id:
            self.stdout.write(self.style.WARNING(
                'Telegram no está activo o no hay chat_id configurado'
            ))
            return
        
        chat_id = config.telegram_chat_id
        enviar_anticipado = config.recordatorio_anticipado  # 5 min antes
        
        self.stdout.write(f"Chat ID: {chat_id}")
        self.stdout.write(f"Recordatorio anticipado (5 min): {'Sí' if enviar_anticipado else 'No'}")
        self.stdout.write("")
        
        enviados_anticipados = 0
        enviados_exactos = 0
        
        # Get pending doses for today and tomorrow
        fecha_limite = now + timedelta(hours=24)
        tomas_pendientes = Toma.objects.filter(
            estado='pendiente',
            hora_programada__gte=now - timedelta(minutes=2),  # Small buffer for exact time
            hora_programada__lte=fecha_limite
        ).select_related('tratamiento', 'tratamiento__medicamento')
        
        self.stdout.write(f"Tomas pendientes encontradas: {tomas_pendientes.count()}")
        self.stdout.write("")
        
        for toma in tomas_pendientes:
            if not toma.tratamiento or not toma.tratamiento.medicamento:
                continue
            
            nombre_medicamento = toma.nombre_medicamento
            hora_toma = toma.hora_programada
            minutos_hasta_toma = (hora_toma - now).total_seconds() / 60
            
            self.stdout.write(f"  📋 {nombre_medicamento}")
            self.stdout.write(f"     Hora programada: {hora_toma.strftime('%H:%M')}")
            self.stdout.write(f"     Minutos hasta toma: {minutos_hasta_toma:.1f}")
            
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
                    self.stdout.write(f"     → Enviando recordatorio anticipado (5 min antes)...")
                    
                    if not dry_run:
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
                            self.stdout.write(self.style.SUCCESS(
                                f"     ✅ Recordatorio anticipado enviado"
                            ))
                        else:
                            self.stdout.write(self.style.ERROR(
                                f"     ❌ Error: {result.get('error')}"
                            ))
                    else:
                        self.stdout.write(self.style.WARNING(
                            f"     [DRY-RUN] Se enviaría recordatorio anticipado"
                        ))
                        enviados_anticipados += 1
                else:
                    self.stdout.write(f"     ⏭️  Recordatorio anticipado ya enviado")
            
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
                    self.stdout.write(f"     → Enviando recordatorio HORA EXACTA...")
                    
                    if not dry_run:
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
                            self.stdout.write(self.style.SUCCESS(
                                f"     ✅ Recordatorio exacto enviado"
                            ))
                        else:
                            self.stdout.write(self.style.ERROR(
                                f"     ❌ Error: {result.get('error')}"
                            ))
                    else:
                        self.stdout.write(self.style.WARNING(
                            f"     [DRY-RUN] Se enviaría recordatorio exacto"
                        ))
                        enviados_exactos += 1
                else:
                    self.stdout.write(f"     ⏭️  Recordatorio exacto ya enviado")
            
            self.stdout.write("")
        
        # Summary
        self.stdout.write(f"\n{'='*50}")
        self.stdout.write("RESUMEN:")
        self.stdout.write(f"  Recordatorios anticipados enviados: {enviados_anticipados}")
        self.stdout.write(f"  Recordatorios hora exacta enviados: {enviados_exactos}")
        self.stdout.write(f"{'='*50}\n")
        
        if dry_run:
            self.stdout.write(self.style.WARNING(
                "Nota: Modo DRY-RUN - no se enviaron mensajes realmente"
            ))
