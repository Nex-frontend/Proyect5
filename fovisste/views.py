import csv
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
            Q(folio__icontains=q) | Q(nombre__icontains=q) | Q(curp__icontains=q) | Q(rfc__icontains=q)
        )
        add_activity(request.user, 'consulta', f'busqueda q="{q}"')
    return render(request, 'consulta.html', {'q': q, 'results': results})

@login_required
@permission_required('fovisste.add_record', raise_exception=True)
def api_upload_view(request: HttpRequest) -> JsonResponse:
    # Punto de subida vía drag & drop (archivos)
    # Soporta CSV/TXT con encabezados folio,nombre,curp,rfc o posiciones [0..3] en ese orden.
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Metodo no permitido'}, status=405)

    files = request.FILES.getlist('files')
    if not files:
        return JsonResponse({'ok': False, 'error': 'No se recibieron archivos'}, status=400)

    total_created = 0
    errors = []

    for f in files:
        try:
            content = f.read()
            # Intentar decodificar como UTF-8, con fallback latin-1
            try:
                text = content.decode('utf-8')
            except UnicodeDecodeError:
                text = content.decode('latin-1')

            buf = io.StringIO(text)
            sample = text[:4096]
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=',;\t|')
            except Exception:
                # por defecto coma
                dialect = csv.excel
                dialect.delimiter = ','

            reader = csv.reader(buf, dialect)
            rows = list(reader)
            if not rows:
                continue

            # Detectar encabezados
            header = [h.strip().lower() for h in rows[0]]
            has_header = set({'folio', 'nombre', 'curp', 'rfc'}).issubset(set(header))
            start_idx = 1 if has_header else 0

            def get_val(row, key_or_idx):
                if isinstance(key_or_idx, int):
                    return (row[key_or_idx] if len(row) > key_or_idx else '').strip()
                try:
                    idx = header.index(key_or_idx)
                    return (row[idx] if len(row) > idx else '').strip()
                except Exception:
                    return ''

            with transaction.atomic():
                for r in rows[start_idx:]:
                    if not any(r):
                        continue
                    folio = get_val(r, 'folio') if has_header else get_val(r, 0)
                    nombre = get_val(r, 'nombre') if has_header else get_val(r, 1)
                    curp = get_val(r, 'curp') if has_header else get_val(r, 2)
                    rfc = get_val(r, 'rfc') if has_header else get_val(r, 3)
                    if not folio and not nombre:
                        # fila inválida mínima
                        continue
                    Record.objects.create(
                        folio=folio[:50],
                        nombre=nombre[:150] if nombre else '',
                        curp=curp[:18] if curp else None,
                        rfc=rfc[:13] if rfc else None,
                    )
                    total_created += 1

            add_activity(request.user, 'carga', f'{f.name} subido, {total_created} registros (acumulado)')
        except Exception as e:
            errors.append({
                'file': f.name,
                'error': str(e),
            })

    return JsonResponse({'ok': True, 'created': total_created, 'errors': errors})
