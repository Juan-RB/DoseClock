"""
Forms for user authentication and registration.
Includes custom validation for password strength.
"""

import re
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from .models import PerfilUsuario


def validate_password_strength(password):
    """
    Validate password meets minimum security requirements.
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character
    """
    errors = []
    
    if len(password) < 8:
        errors.append("La contrasena debe tener al menos 8 caracteres.")
    
    if not re.search(r'[A-Z]', password):
        errors.append("Debe contener al menos una letra mayuscula.")
    
    if not re.search(r'[a-z]', password):
        errors.append("Debe contener al menos una letra minuscula.")
    
    if not re.search(r'\d', password):
        errors.append("Debe contener al menos un numero.")
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;\'`~]', password):
        errors.append("Debe contener al menos un caracter especial (!@#$%^&*...).")
    
    if errors:
        raise ValidationError(errors)


class LoginForm(AuthenticationForm):
    """
    Custom login form with styled fields.
    """
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Usuario',
            'autocomplete': 'username',
            'id': 'login-username'
        }),
        label='Usuario'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Contrasena',
            'autocomplete': 'current-password',
            'id': 'login-password'
        }),
        label='Contrasena'
    )

    error_messages = {
        'invalid_login': 'Usuario o contrasena incorrectos. Por favor, intenta de nuevo.',
        'inactive': 'Esta cuenta esta desactivada.',
    }


class RegistroForm(UserCreationForm):
    """
    Custom registration form with extended profile fields.
    Includes strong password validation.
    """
    nombre_completo = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Nombre completo',
            'id': 'registro-nombre'
        }),
        label='Nombre completo',
        help_text='Tu nombre real para identificarte'
    )
    
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'correo@ejemplo.com (opcional)',
            'id': 'registro-email'
        }),
        label='Correo electronico (opcional)',
        help_text='Para recuperar tu cuenta si olvidas la contrasena'
    )
    
    edad = forms.IntegerField(
        min_value=1,
        max_value=120,
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Edad',
            'id': 'registro-edad',
            'min': '1',
            'max': '120'
        }),
        label='Edad',
        help_text='Requerido para validaciones medicas'
    )
    
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Nombre de usuario',
            'autocomplete': 'username',
            'id': 'registro-username'
        }),
        label='Nombre de usuario',
        help_text='Unico, sin espacios. Ej: juan_perez'
    )
    
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Contrasena',
            'autocomplete': 'new-password',
            'id': 'registro-password1'
        }),
        label='Contrasena',
        help_text='Minimo 8 caracteres, con mayuscula, numero y simbolo'
    )
    
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Confirmar contrasena',
            'autocomplete': 'new-password',
            'id': 'registro-password2'
        }),
        label='Confirmar contrasena'
    )

    class Meta:
        model = User
        fields = ['nombre_completo', 'email', 'edad', 'username', 'password1', 'password2']

    def clean_username(self):
        """Validate username is unique and has no spaces."""
        username = self.cleaned_data.get('username')
        
        if ' ' in username:
            raise ValidationError('El nombre de usuario no puede contener espacios.')
        
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('Este nombre de usuario ya esta en uso.')
        
        return username.lower()

    def clean_email(self):
        """Validate email is unique if provided."""
        email = self.cleaned_data.get('email')
        
        if email and User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Este correo electronico ya esta registrado.')
        
        return email.lower() if email else ''

    def clean_password1(self):
        """Validate password strength."""
        password = self.cleaned_data.get('password1')
        username = self.cleaned_data.get('username', '')
        nombre = self.cleaned_data.get('nombre_completo', '')
        
        validate_password_strength(password)
        
        # Check password is not too similar to username or name
        if username and username.lower() in password.lower():
            raise ValidationError('La contrasena no puede contener tu nombre de usuario.')
        
        if nombre:
            nombre_parts = nombre.lower().split()
            for part in nombre_parts:
                if len(part) > 3 and part in password.lower():
                    raise ValidationError('La contrasena no puede contener partes de tu nombre.')
        
        return password

    def save(self, commit=True):
        """Save user and create associated profile."""
        user = super().save(commit=False)
        user.email = self.cleaned_data.get('email', '')
        
        if commit:
            user.save()
            # Update or create profile with additional data
            PerfilUsuario.objects.update_or_create(
                user=user,
                defaults={
                    'nombre_completo': self.cleaned_data['nombre_completo'],
                    'edad': self.cleaned_data['edad']
                }
            )
        
        return user


class PerfilForm(forms.ModelForm):
    """
    Form for editing user profile.
    """
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'correo@ejemplo.com'
        }),
        label='Correo electronico'
    )
    
    class Meta:
        model = PerfilUsuario
        fields = ['nombre_completo', 'edad']
        widgets = {
            'nombre_completo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre completo'
            }),
            'edad': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '120'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['email'].initial = self.user.email

    def save(self, commit=True):
        perfil = super().save(commit=False)
        
        if commit:
            perfil.save()
            if self.user:
                self.user.email = self.cleaned_data.get('email', '')
                self.user.save()
        
        return perfil
