"""
Views for user authentication.
Handles login, logout, registration, and profile management.
"""

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse

from .forms import LoginForm, RegistroForm, PerfilForm


def login_view(request):
    """
    Handle user login with custom form.
    Redirects to dashboard on success.
    """
    # Redirect if already logged in
    if request.user.is_authenticated:
        return redirect('medicamentos:dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'¡Bienvenido de vuelta, {user.perfil.nombre_completo}!')
            
            # Redirect to next page or dashboard
            next_url = request.GET.get('next', 'medicamentos:dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Usuario o contrasena incorrectos.')
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


def registro_view(request):
    """
    Handle user registration with profile creation.
    """
    # Redirect if already logged in
    if request.user.is_authenticated:
        return redirect('medicamentos:dashboard')
    
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request, 
                f'¡Cuenta creada exitosamente! Bienvenido, {user.perfil.nombre_completo}.'
            )
            return redirect('medicamentos:dashboard')
    else:
        form = RegistroForm()
    
    return render(request, 'accounts/register.html', {'form': form})


def logout_view(request):
    """
    Handle user logout.
    """
    if request.user.is_authenticated:
        nombre = request.user.perfil.nombre_completo if hasattr(request.user, 'perfil') else request.user.username
        logout(request)
        messages.info(request, f'Hasta pronto, {nombre}. Tu sesion ha sido cerrada!')
    return redirect('accounts:login')


@login_required
def perfil_view(request):
    """
    Display and edit user profile.
    """
    perfil = request.user.perfil
    
    if request.method == 'POST':
        form = PerfilForm(request.POST, instance=perfil, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado correctamente.')
            return redirect('accounts:perfil')
    else:
        form = PerfilForm(instance=perfil, user=request.user)
    
    return render(request, 'accounts/perfil.html', {
        'form': form,
        'perfil': perfil
    })


def validar_username(request):
    """
    AJAX endpoint to check if username is available.
    """
    username = request.GET.get('username', '')
    from django.contrib.auth.models import User
    
    exists = User.objects.filter(username__iexact=username).exists()
    
    return JsonResponse({
        'available': not exists,
        'message': 'Usuario disponible' if not exists else 'Este usuario ya existe'
    })


def validar_email(request):
    """
    AJAX endpoint to check if email is available.
    """
    email = request.GET.get('email', '')
    from django.contrib.auth.models import User
    
    if not email:
        return JsonResponse({'available': True, 'message': ''})
    
    exists = User.objects.filter(email__iexact=email).exists()
    
    return JsonResponse({
        'available': not exists,
        'message': 'Correo disponible' if not exists else 'Este correo ya esta registrado'
    })
