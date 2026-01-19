"""
Forms for DoseClock application.
"""

from django import forms
from .models import Medicamento, Tratamiento, ConfiguracionUsuario


class MedicamentoForm(forms.ModelForm):
    """Form for creating and editing medications."""
    
    class Meta:
        model = Medicamento
        fields = ['nombre', 'color', 'notas']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del medicamento',
                'aria-label': 'Nombre del medicamento'
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control form-control-color',
                'type': 'color',
                'aria-label': 'Color identificador'
            }),
            'notas': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notas adicionales (opcional)',
                'aria-label': 'Notas adicionales'
            }),
        }


class TratamientoForm(forms.ModelForm):
    """Form for creating and editing treatments."""
    
    FRECUENCIA_CHOICES = [
        ('', 'Seleccionar frecuencia'),
        ('5', 'Cada 5 horas'),
        ('8', 'Cada 8 horas'),
        ('12', 'Cada 12 horas'),
        ('24', 'Cada 24 horas'),
        ('custom', 'Personalizado'),
    ]
    
    frecuencia_preset = forms.ChoiceField(
        choices=FRECUENCIA_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'aria-label': 'Frecuencia predefinida'
        })
    )
    
    primera_toma_ahora = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'aria-label': '¿Primera toma ahora?'
        })
    )
    
    hora_ultima_toma = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local',
            'aria-label': 'Hora de ultima toma'
        })
    )
    
    class Meta:
        model = Tratamiento
        fields = [
            'medicamento', 
            'duracion_dias', 
            'es_indefinido',
            'frecuencia_horas', 
            'modo_calculo',
            'notas'
        ]
        widgets = {
            'medicamento': forms.Select(attrs={
                'class': 'form-select',
                'aria-label': 'Medicamento'
            }),
            'duracion_dias': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dias de tratamiento',
                'min': 1,
                'aria-label': 'Duracion en dias'
            }),
            'es_indefinido': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'aria-label': 'Tratamiento indefinido'
            }),
            'frecuencia_horas': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Horas entre tomas',
                'step': '0.5',
                'min': '0.5',
                'aria-label': 'Frecuencia en horas'
            }),
            'modo_calculo': forms.Select(attrs={
                'class': 'form-select',
                'aria-label': 'Modo de calculo'
            }),
            'notas': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notas sobre el tratamiento',
                'aria-label': 'Notas del tratamiento'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Filter medications by user
        if self.user:
            self.fields['medicamento'].queryset = Medicamento.objects.filter(
                usuario=self.user,
                activo=True
            )


class ConfiguracionForm(forms.ModelForm):
    """Form for user configuration."""
    
    class Meta:
        model = ConfiguracionUsuario
        fields = [
            'modo_visual',
            'paleta_colores',
            'tamano_texto',
            'alto_contraste',
            'recordatorio_anticipado',
            'notificaciones_activas',
            'sonido_notificacion',
            'backup_automatico',
            'frecuencia_backup_dias'
        ]
        widgets = {
            'modo_visual': forms.Select(attrs={
                'class': 'form-select',
                'aria-label': 'Modo visual'
            }),
            'paleta_colores': forms.Select(attrs={
                'class': 'form-select',
                'aria-label': 'Paleta de colores'
            }),
            'tamano_texto': forms.Select(attrs={
                'class': 'form-select',
                'aria-label': 'Tamano de texto'
            }),
            'alto_contraste': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'aria-label': 'Alto contraste'
            }),
            'recordatorio_anticipado': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'aria-label': 'Recordatorio anticipado'
            }),
            'notificaciones_activas': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'aria-label': 'Notificaciones activas'
            }),
            'sonido_notificacion': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'aria-label': 'Sonido de notificacion'
            }),
            'backup_automatico': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'aria-label': 'Backup automatico'
            }),
            'frecuencia_backup_dias': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 30,
                'aria-label': 'Frecuencia de backup'
            }),
        }


class ConfirmarTomaForm(forms.Form):
    """Simple form for confirming a dose."""
    
    notas = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Notas (opcional)',
            'aria-label': 'Notas de la toma'
        })
    )
