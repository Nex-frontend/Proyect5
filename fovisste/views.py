from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group, Permission, User
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import SignUpForm
from .models import Record, Activity

# Helpers de roles
UPLOADER_GROUP = 'uploader'
VIEWER_GROUP = 'viewer'

def ensure_roles():
    Group.objects.get_or_create(name=UPLOADER_GROUP)
    Group.objects.get_or_create(name=VIEWER_GROUP)

def add_activity(user, segmento, actividad):
    Activity.objects.create(user=user, segmento=segmento, actividad=actividad)

def signup_view(request: HttpRequest) -> HttpResponse:
    ensure_roles()
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data.get('first_name') or '',
                last_name=form.cleaned_data.get('last_name') or '',
            )
            viewer_group = Group.objects.get(name=VIEWER_GROUP)
            user.groups.add(viewer_group)
            login(request, user)
            add_activity(user, 'auth', 'registro')
            messages.success(request, 'Registro exitoso. Bienvenido.')
            return redirect('dashboard')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})

@login_required
def dashboard_view(request: HttpRequest) -> HttpResponse:
    return render(request, 'dashboard.html')

@login_required
@permission_required('fovisste.add_record', raise_exception=True)
def carga_view(request: HttpRequest) -> HttpResponse:
    # Renderiza página con drag & drop y tabla CRUD
    records = Record.objects.all()[:200]
    return render(request, 'carga.html', { 'records': records })

@login_required
@permission_required('fovisste.view_record', raise_exception=True)
def consulta_view(request: HttpRequest) -> HttpResponse:
    q = request.GET.get('q', '').strip()
    results = []
    if q:
        results = Record.objects.filter(
            Q(folio__icontains=q) | Q(nombre__icontains=q) | Q(curp__icontains=q) | Q(rfc__icontains=q)
        )
        add_activity(request.user, 'consulta', f'busqueda q="{q}"')
    return render(request, 'consulta.html', {'q': q, 'results': results})

@login_required
@permission_required('fovisste.add_record', raise_exception=True)
def api_upload_view(request: HttpRequest) -> JsonResponse:
    # Punto de subida vía drag & drop (archivos)
    # Aquí parsearías CSV/Excel y crearías Records en lote
    if request.method == 'POST':
        add_activity(request.user, 'carga', 'archivo subido')
        return JsonResponse({'ok': True})
    return JsonResponse({'ok': False, 'error': 'Metodo no permitido'}, status=405)
