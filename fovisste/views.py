import io

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group, Permission, User
from django.db import transaction
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
            Q(rfc__icontains=q) |
            Q(nombre__icontains=q) |
            Q(cadena1__icontains=q) |
            Q(tipo__icontains=q) |
            Q(impor__icontains=q) |
            Q(cpto__icontains=q) |
            Q(lote_actual__icontains=q) |
            Q(qna__icontains=q) |
            Q(ptje__icontains=q) |
            Q(observacio__icontains=q) |
            Q(lote_anterior__icontains=q) |
            Q(qna_ini__icontains=q)
        )
        add_activity(request.user, 'consulta', f'busqueda q="{q}"')
    return render(request, 'consulta.html', {'q': q, 'results': results})

@login_required
@permission_required('fovisste.add_record', raise_exception=True)
def api_upload_view(request: HttpRequest) -> JsonResponse:
    """Carga de archivos de ancho fijo y grabado directo en MySQL vía ORM.

    Formato confirmado (posiciones 0..159, longitudes entre paréntesis):
      rfc(13), nombre(30), cadena1(37), tipo(1), impor(8), cpto(2), lote_actual(1),
      qna(6), ptje(2), observacio(47), lote_anterior(6), qna_ini(6)

    Valida que cada línea tenga al menos 159 caracteres (las faltantes se reportan como error).
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Metodo no permitido'}, status=405)

    files = request.FILES.getlist('files')
    if not files:
        return JsonResponse({'ok': False, 'error': 'No se recibieron archivos'}, status=400)

    total_created = 0
    errors = []

    # Definición de cortes fixed-width (inicio, fin)
    FIELDS = [
        ("rfc", 0, 13),
        ("nombre", 13, 43),
        ("cadena1", 43, 80),
        ("tipo", 80, 81),
        ("impor", 81, 89),
        ("cpto", 89, 91),
        ("lote_actual", 91, 92),
        ("qna", 92, 98),
        ("ptje", 98, 100),
        ("observacio", 100, 147),
        ("lote_anterior", 147, 153),
        ("qna_ini", 153, 159),
    ]
    REQUIRED_LINE_LEN = 159
    REQUIRED_MIN_LEN = 100  # según aclaración: si la línea tiene 100, el resto son blancos

    for f in files:
        try:
            content = f.read()
            # Intentar decodificar como UTF-8, con fallback latin-1
            try:
                text = content.decode('utf-8')
            except UnicodeDecodeError:
                text = content.decode('latin-1')

            lines = [ln.rstrip('\r\n') for ln in text.splitlines() if ln.strip()]
            if not lines:
                continue

            batch = []
            with transaction.atomic():
                for idx, line in enumerate(lines, start=1):
                    if len(line) < REQUIRED_MIN_LEN:
                        errors.append({
                            'file': f.name,
                            'line': idx,
                            'error': f'Longitud {len(line)} < {REQUIRED_MIN_LEN}',
                        })
                        continue
                    # Asegurar ancho para cortes (pad con espacios hasta 159)
                    if len(line) < REQUIRED_LINE_LEN:
                        line = line.ljust(REQUIRED_LINE_LEN)
                    data = {}
                    for field, start, end in FIELDS:
                        data[field] = line[start:end].rstrip()

                    # Crear instancia usando ORM (se insertará en MySQL)
                    rec = Record(
                        rfc=data['rfc'][:13],
                        nombre=data['nombre'][:30],
                        cadena1=(data['cadena1'][:37] or None),
                        tipo=data['tipo'][:1],
                        impor=data['impor'][:8],
                        cpto=data['cpto'][:2],
                        lote_actual=data['lote_actual'][:1],
                        qna=data['qna'][:6],
                        ptje=data['ptje'][:2],
                        observacio=(data['observacio'][:47] or None),
                        lote_anterior=(data['lote_anterior'][:6] or None),
                        qna_ini=(data['qna_ini'][:6] or None),
                    )
                    batch.append(rec)

                if batch:
                    Record.objects.bulk_create(batch, batch_size=1000)
                    total_created += len(batch)

            add_activity(request.user, 'carga', f'{f.name}: creados {len(batch)} registros')
        except Exception as e:
            errors.append({'file': f.name, 'error': str(e)})

    return JsonResponse({'ok': True, 'created': total_created, 'errors': errors})
