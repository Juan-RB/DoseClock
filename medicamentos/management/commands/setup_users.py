"""
Management command to set up initial users and migrate existing data.
Creates an admin superuser and a regular user with existing data.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import PerfilUsuario
from medicamentos.models import Medicamento, Tratamiento, ConfiguracionUsuario


class Command(BaseCommand):
    help = 'Set up initial users and migrate existing data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--admin-password',
            type=str,
            default='Admin123!',
            help='Password for the admin user'
        )
        parser.add_argument(
            '--user-password',
            type=str,
            default='Usuario123!',
            help='Password for the regular user'
        )

    def handle(self, *args, **options):
        admin_password = options['admin_password']
        user_password = options['user_password']
        
        self.stdout.write(self.style.NOTICE('Setting up users...'))
        
        # 1. Create admin superuser
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@doseclock.local',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            admin_user.set_password(admin_password)
            admin_user.save()
            # Create or update admin profile
            PerfilUsuario.objects.update_or_create(
                user=admin_user,
                defaults={
                    'nombre_completo': 'Administrador',
                    'edad': 30
                }
            )
            self.stdout.write(self.style.SUCCESS(
                f'✅ Admin user created: admin / {admin_password}'
            ))
        else:
            self.stdout.write(self.style.WARNING('Admin user already exists'))
        
        # 2. Create regular user
        regular_user, created = User.objects.get_or_create(
            username='usuario',
            defaults={
                'email': 'usuario@doseclock.local',
                'is_staff': False,
                'is_superuser': False
            }
        )
        if created:
            regular_user.set_password(user_password)
            regular_user.save()
            # Create or update user profile
            PerfilUsuario.objects.update_or_create(
                user=regular_user,
                defaults={
                    'nombre_completo': 'Usuario Principal',
                    'edad': 25
                }
            )
            self.stdout.write(self.style.SUCCESS(
                f'✅ Regular user created: usuario / {user_password}'
            ))
        else:
            self.stdout.write(self.style.WARNING('Regular user already exists'))
        
        # 3. Create juan_1 user (main user)
        juan_user, created = User.objects.get_or_create(
            username='juan_1',
            defaults={
                'email': 'juan@doseclock.local',
                'is_staff': False,
                'is_superuser': False
            }
        )
        if created:
            juan_user.set_password(user_password)
            juan_user.save()
            PerfilUsuario.objects.update_or_create(
                user=juan_user,
                defaults={
                    'nombre_completo': 'Juan',
                    'edad': 25
                }
            )
            # Create configuration for juan_1
            ConfiguracionUsuario.objects.get_or_create(
                usuario=juan_user,
                defaults={
                    'modo_visual': 'minimalista',
                    'paleta_colores': 'nude',
                    'telegram_activo': False
                }
            )
            self.stdout.write(self.style.SUCCESS(
                f'✅ Juan user created: juan_1 / {user_password}'
            ))
        else:
            self.stdout.write(self.style.WARNING('juan_1 user already exists'))
        
        # 4. Migrate existing data to regular user
        self.stdout.write(self.style.NOTICE('Migrating existing data...'))
        
        # Migrate medications without owner
        meds_updated = Medicamento.objects.filter(usuario__isnull=True).update(
            usuario=regular_user
        )
        self.stdout.write(f'  - Medications assigned: {meds_updated}')
        
        # Migrate treatments without owner
        treatments_updated = Tratamiento.objects.filter(usuario__isnull=True).update(
            usuario=regular_user
        )
        self.stdout.write(f'  - Treatments assigned: {treatments_updated}')
        
        # Migrate or create configuration for regular user
        existing_config = ConfiguracionUsuario.objects.filter(usuario__isnull=True).first()
        if existing_config:
            existing_config.usuario = regular_user
            existing_config.save()
            self.stdout.write('  - Configuration migrated')
        else:
            ConfiguracionUsuario.objects.get_or_create(
                usuario=regular_user,
                defaults={
                    'modo_visual': 'minimalista',
                    'paleta_colores': 'nude'
                }
            )
            self.stdout.write('  - New configuration created')
        
        # Create configuration for admin
        ConfiguracionUsuario.objects.get_or_create(
            usuario=admin_user,
            defaults={
                'modo_visual': 'minimalista',
                'paleta_colores': 'azul'
            }
        )
        
        self.stdout.write(self.style.SUCCESS('\n✅ Setup complete!'))
        self.stdout.write(self.style.NOTICE('\nCredentials:'))
        self.stdout.write(f'  Admin:  admin / {admin_password}')
        self.stdout.write(f'  User:   usuario / {user_password}')
        self.stdout.write(f'  Juan:   juan_1 / {user_password}')
        self.stdout.write(self.style.WARNING(
            '\n⚠️  Remember to change these passwords in production!'
        ))
