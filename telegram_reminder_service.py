"""
Servicio de recordatorios de Telegram para DoseClock.
Ejecuta verificaciones cada minuto para enviar recordatorios.

Uso: python telegram_reminder_service.py

Para ejecutar en producción, usa un servicio como:
- Windows Task Scheduler
- Linux cron
- systemd timer
- O déjalo corriendo en segundo plano
"""

import os
import sys
import time
import signal
from datetime import datetime

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'doseclock.settings')

import django
django.setup()

from django.core.management import call_command

# Flag for graceful shutdown
running = True


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global running
    print("\n\n⏹️  Deteniendo servicio de recordatorios...")
    running = False


def main():
    """Main service loop."""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 60)
    print("🔔 SERVICIO DE RECORDATORIOS TELEGRAM - DoseClock")
    print("=" * 60)
    print(f"Iniciado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("Verificando recordatorios cada 60 segundos...")
    print("Presiona Ctrl+C para detener")
    print("=" * 60)
    print()
    
    iteration = 0
    
    while running:
        iteration += 1
        
        try:
            print(f"\n🔄 Verificación #{iteration} - {datetime.now().strftime('%H:%M:%S')}")
            print("-" * 40)
            
            # Call the management command
            call_command('enviar_recordatorios_telegram')
            
        except Exception as e:
            print(f"❌ Error en verificación: {e}")
        
        # Wait 60 seconds before next check
        # Using smaller intervals to allow faster shutdown
        for _ in range(60):
            if not running:
                break
            time.sleep(1)
    
    print("\n✅ Servicio detenido correctamente")


if __name__ == "__main__":
    main()
