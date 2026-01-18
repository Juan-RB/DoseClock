# DoseClock 💊⏰

Aplicación local para gestión y recordatorio de medicamentos.

## Características

- ✅ Gestión de medicamentos y tratamientos
- ✅ Cálculo automático de próximas tomas
- ✅ Sistema de confirmación con estados (verde/naranja/rojo)
- ✅ Notificaciones push
- ✅ Calendario visual
- ✅ Historial completo de tomas
- ✅ Modo minimalista y modo visual avanzado
- ✅ Accesibilidad completa
- ✅ Copias de seguridad locales
- ✅ 100% offline

## Requisitos

- Python 3.10+
- pip

## Instalación

### 1. Crear entorno virtual

```powershell
cd D:\Proyecto-DoseClock
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Instalar dependencias

```powershell
pip install -r requirements.txt
```

### 3. Crear la base de datos

```powershell
python manage.py makemigrations
python manage.py migrate
```

### 4. Crear superusuario (opcional)

```powershell
python manage.py createsuperuser
```

### 5. Ejecutar servidor

```powershell
python manage.py runserver
```

Accede a la aplicación en: **http://127.0.0.1:8000/**

## Estructura del Proyecto

```
Proyecto-DoseClock/
├── manage.py
├── requirements.txt
├── db.sqlite3                  # Base de datos local
├── backups/                    # Copias de seguridad
├── doseclock/                  # Configuración Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── medicamentos/               # App principal
│   ├── models.py              # Entidades del sistema
│   ├── views.py               # Vistas (funciones)
│   ├── forms.py
│   ├── urls.py
│   ├── utils/                 # Funciones modulares
│   │   ├── calculos_tomas.py
│   │   ├── notificaciones.py
│   │   ├── backup.py
│   │   └── validaciones.py
│   └── templates/
│       └── medicamentos/
└── static/
    ├── css/
    ├── js/
    └── manifest.json
```

## Modelo de Datos

### Entidades

1. **Medicamento**: Información del medicamento
2. **Tratamiento**: Programación de un medicamento
3. **Toma**: Registro individual de cada dosis
4. **Notificacion**: Programación de recordatorios
5. **ConfiguracionUsuario**: Preferencias del usuario

### Estados de Toma

| Estado | Color | Descripción |
|--------|-------|-------------|
| Pendiente | Gris | Toma aún no programada |
| Confirmada | Verde | Confirmada a tiempo |
| Tarde | Naranja | Confirmada después del tiempo de gracia |
| No tomada | Rojo | No confirmada (auto-marcada tras 20 min) |

## Reglas de Negocio

### Confirmación de Tomas

- El botón de confirmar se habilita **5 minutos antes** de la hora programada
- Después de **20 minutos**, se marca automáticamente como "no tomada"
- Siempre se puede confirmar manualmente (se marcará como "tarde")

### Cálculo de Próximas Tomas

Dos modos disponibles:
1. **Desde hora programada**: La siguiente toma se calcula desde la hora original
2. **Desde hora de confirmación**: La siguiente toma se calcula desde cuando se confirmó

## Modos Visuales

### Modo Minimalista
- Diseño limpio y moderno
- Paletas de colores: Nude, Azul, Verde, Púrpura
- Ideal para uso diario

### Modo Visual Avanzado
- Pastillero 3D animado
- Visualización por compartimentos
- Animaciones fluidas

## Accesibilidad

- Tamaños de texto configurables (Normal, Grande, Muy Grande)
- Modo alto contraste
- Navegación por teclado
- Soporte para lectores de pantalla
- Iconos + colores (nunca solo color)

## Copias de Seguridad

### Manual
1. Ir a Configuración → Backups
2. Click en "Crear Backup"
3. El archivo JSON se guarda en `/backups/`

### Automática
- Configurable en Configuración
- Frecuencia: 1-30 días

### Restaurar
1. Ir a Backups
2. Click en el botón de restaurar
3. Confirmar

## API Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/proximas-tomas/` | GET | Próximas tomas programadas |
| `/api/confirmar-toma/<id>/` | POST | Confirmar una toma |
| `/api/notificaciones-pendientes/` | GET | Notificaciones pendientes |
| `/api/actualizar-estados/` | GET | Actualizar estados de tomas |

## Preparación para Migración a Nube

El sistema está preparado para futura migración:

- UUIDs como identificadores primarios
- Timestamps de sincronización
- Estructura JSON para configuraciones
- API REST lista para expandir
- Separación clara backend/frontend

## Desarrollo

### Ejecutar tests

```powershell
python manage.py test
```

### Crear migraciones

```powershell
python manage.py makemigrations
python manage.py migrate
```

## Licencia

Proyecto personal - Todos los derechos reservados.

---

Desarrollado con ❤️ usando Django y Bootstrap
