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

def has_existing_load(user, qna_ini, lote_anterior):
    """Verifica si ya existe una carga para esta combinación de usuario, quincena y lote"""
    return Record.objects.filter(
        responsable=user,
        qna_ini=qna_ini,
        lote_anterior=lote_anterior
    ).exists()

def ensure_roles(): # Crear roles si no existen
    Group.objects.get_or_create(name=UPLOADER_GROUP)
    Group.objects.get_or_create(name=VIEWER_GROUP)

def add_activity(user, segmento, actividad): # Agregar actividad
    Activity.objects.create(user=user, segmento=segmento, actividad=actividad)

def signup_view(request: HttpRequest) -> HttpResponse: # Registro de usuario
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
@login_required # Panel principal
def dashboard_view(request: HttpRequest) -> HttpResponse:
    return render(request, 'dashboard.html')

@login_required # Carga de archivos
@permission_required('fovisste.add_record', raise_exception=True)
def carga_view(request: HttpRequest) -> HttpResponse:
    # Requiere que se haya capturado Quincena Proceso y Lote desde qnaproceso
    if not (request.session.get('qna_ini') and request.session.get('lote_anterior')):
        messages.error(request, 'Debes capturar "Quincena Proceso" y "Lote" en la página de configuración antes de realizar la carga.')
        return redirect('qnaproceso')

    qna_ini = request.session.get('qna_ini')
    lote_anterior = request.session.get('lote_anterior')

    # Verificar si ya existe una carga para esta combinación
    if has_existing_load(request.user, qna_ini, lote_anterior):
        messages.warning(request, 'Ya existe una carga para esta combinación. Reinicia el proceso en la página de Quincena Proceso.')
        return redirect('qnaproceso')

    # Obtener datos de sesión para preview si existen
    preview_records = request.session.get('preview_records', [])
    print(f"DEBUG: Preview records recuperados de sesión: {len(preview_records)} registros")  # Depuración

    # Calcular conteos para preview
    tipo_a_count = sum(1 for r in preview_records if r.get('tipo') == 'A')
    tipo_b_count = sum(1 for r in preview_records if r.get('tipo') == 'B')
    total_count = len(preview_records)
    print(f"DEBUG: Conteos calculados - Tipo A: {tipo_a_count}, Tipo B: {tipo_b_count}, Total: {total_count}")  # Depuración

    context = {
        'qna_ini': qna_ini,
        'lote_anterior': lote_anterior,
        'preview_records': preview_records,
        'tipo_a_count': tipo_a_count,
        'tipo_b_count': tipo_b_count,
        'total_count': total_count,
    }
    return render(request, 'carga.html', context)

@login_required # Consulta de archivos
@permission_required('fovisste.view_record', raise_exception=True)
def consulta_view(request: HttpRequest) -> HttpResponse:
    q = request.GET.get('q', '').strip()
    results = []  # Inicializar results como lista vacía

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

@login_required  # Página de quincena en proceso
def qnaproceso_view(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        if 'cancel' in request.POST:
            request.session.pop('qna_ini', None)
            request.session.pop('lote_anterior', None)
            messages.info(request, 'Operación cancelada.')
            return redirect('dashboard')
        qna = (request.POST.get('qna_proceso') or '').strip()
        lote = (request.POST.get('lote') or '').strip()
        # Validaciones: qna = YYYYMM (6 dígitos), lote = 4 caracteres (asumimos dígitos)
        import re
        ok = True
        if not re.fullmatch(r"\d{6}", qna):
            messages.error(request, 'Quincena Proceso debe tener 6 dígitos con formato AAAAMM (ejemplo: 202508).')
            ok = False
        if not re.fullmatch(r"\d{4}", lote):
            messages.error(request, 'Lote debe tener 5 dígitos.')
            ok = False
        if ok:
            # Nueva validación: verificar si el lote ya está duplicado en la BD
            if Record.objects.filter(lote_anterior=lote, qna_ini=qna).exists():
                messages.error(request, f'El lote "{lote}" para la quincena "{qna}" ya tiene registros cargados. Por favor, elige un lote diferente o reinicia el proceso.')
            else:
                request.session['qna_ini'] = qna
                request.session['lote_anterior'] = lote
                messages.success(request, 'Datos guardados. Ahora puedes realizar la carga de archivos.')
                return redirect('carga')
    # GET o POST inválido: renderizar formulario mostrando valores actuales si existen
    ctx = {
        'qna_ini': request.session.get('qna_ini', ''),
        'lote_anterior': request.session.get('lote_anterior', ''),
    }
    return render(request, 'qnaproceso.html', ctx)
@login_required
@permission_required('fovisste.view_record', raise_exception=True)
def resultados_view(request: HttpRequest) -> HttpResponse:
    """Vista para mostrar resultados de cargas recientes."""
    # Obtener parámetros de consulta opcionales
    qna_filter = request.GET.get('qna', '').strip()
    lote_filter = request.GET.get('lote', '').strip()

    # Construir consulta base
    records = Record.objects.filter(responsable=request.user).order_by('-fecha_carga')

    # Aplicar filtros si se proporcionan
    if qna_filter:
        records = records.filter(qna_ini__icontains=qna_filter)
    if lote_filter:
        records = records.filter(lote_anterior__icontains=lote_filter)

    # Limitar a los últimos 200 para evitar sobrecarga
    records = records[:200]

    context = {
        'records': records,
        'qna_filter': qna_filter,
        'lote_filter': lote_filter,
    }
@login_required
@permission_required('fovisste.add_record', raise_exception=True)
def update_lote_view(request: HttpRequest) -> JsonResponse:
    """Vista para actualizar el lote en sesión para carga múltiple."""
    if request.method == 'POST':
        nuevo_lote = request.POST.get('nuevo_lote', '').strip()
        if not re.fullmatch(r"\d{4}", nuevo_lote):
            return JsonResponse({'ok': False, 'error': 'Lote debe tener 4 dígitos.'}, status=400)
        request.session['lote_anterior'] = nuevo_lote
        return JsonResponse({'ok': True})
    return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)
@permission_required('fovisste.add_record', raise_exception=True)
def api_upload_view(request: HttpRequest) -> JsonResponse:
    """Carga de archivos de ancho fijo y grabado directo en MySQL vía ORM.

    Formato confirmado (posiciones 0..158, longitudes entre paréntesis):
      rfc(13), nombre(30), cadena1(37), tipo(1), impor(8), cpto(2), lote_actual(1),
      qna(6), ptje(2), observacio(47), lote_anterior(4), qna_ini(5)

    Valida que cada línea tenga al menos 158 caracteres (las faltantes se reportan como error).
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Metodo no permitido'}, status=405)

    # Requerir valores en sesión antes de permitir carga
    if not (request.session.get('qna_ini') and request.session.get('lote_anterior')):
        return JsonResponse({
            'ok': False,
            'error': 'Debes capturar "Quincena Proceso" y "Lote" antes de realizar la carga.'
        }, status=400)

    # Verificar si ya existe una carga para esta combinación
    qna_ini = request.session.get('qna_ini')
    lote_anterior = request.session.get('lote_anterior')
    if has_existing_load(request.user, qna_ini, lote_anterior):
        return JsonResponse({
            'ok': False,
            'error': 'Ya existe una carga para esta combinación de Quincena y Lote. Debes reiniciar el proceso en la página de Quincena Proceso.',
            'redirect': 'qnaproceso'
        }, status=400)

    # Si es confirmación, procesar datos editados
    if request.POST.get('confirm'):
        print("DEBUG: Entrando en flujo de confirmación en api_upload_view")  # Depuración
        preview_records = request.session.get('preview_records', [])
        print(f"DEBUG: Preview records en confirmación: {len(preview_records)}")  # Depuración
        batch = []
        for data in preview_records:
            rec = Record(
                rfc=data.get('rfc', '')[:13],
                nombre=data.get('nombre', '')[:30],
                cadena1=data.get('cadena1') or None,
                tipo=data.get('tipo', '')[:1],
                impor=data.get('impor', '')[:8],
                cpto=data.get('cpto', '')[:2],
                lote_actual=data.get('lote_actual', '')[:1],
                qna=data.get('qna', '')[:6],
                ptje=data.get('ptje', '')[:2],
                observacio=data.get('observacio') or None,
                lote_anterior=data.get('lote_anterior', '')[:5],
                qna_ini=data.get('qna_ini', '')[:6],
                responsable=request.user,
            )
            batch.append(rec)

        if batch:
            print(f"DEBUG: Procesando {len(batch)} registros para bulk_create")  # Depuración
            Record.objects.bulk_create(batch, batch_size=1000)
            total_created = len(batch)
            print(f"DEBUG: Registros creados exitosamente: {total_created}")  # Depuración
        else:
            print("DEBUG: No hay registros para procesar en confirmación")  # Depuración

        # Limpiar sesiones
        request.session.pop('preview_records', None)
        request.session.pop('preview_errors', None)
        print("DEBUG: Sesiones limpiadas después de confirmación")  # Depuración
        return JsonResponse({'ok': True, 'created': total_created, 'errors': []})

    # Código original para carga directa

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
        ("qna_ini", 153, 157),
    ]
    REQUIRED_LINE_LEN = 157
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
                        # Sobrescribir con sesión si está disponible
                        lote_anterior=(request.session.get('lote_anterior') or data['lote_anterior'][:6] or None),
                        qna_ini=(request.session.get('qna_ini') or data['qna_ini'][:4] or None),
                        responsable=request.user, # Usuario que realiza la carga
                    )
                    batch.append(rec)

                if batch:
                    Record.objects.bulk_create(batch, batch_size=1000)
                    total_created += len(batch)

            add_activity(request.user, 'carga', f'{f.name}: creados {len(batch)} registros')
        except Exception as e:
            errors.append({'file': f.name, 'error': str(e)})

    # Limpiar sesión después de carga exitosa para forzar nuevo proceso
    if total_created > 0:
        request.session.pop('qna_ini', None)
        request.session.pop('lote_anterior', None)

@login_required # Preview de archivos antes de guardar
@permission_required('fovisste.add_record', raise_exception=True)
def preview_upload_view(request: HttpRequest) -> JsonResponse:
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido'}, status=405)

    # Verificar sesión
    if not (request.session.get('qna_ini') and request.session.get('lote_anterior')):
        return JsonResponse({'ok': False, 'error': 'Sesión inválida. Reinicia el proceso.'}, status=400)

    files = request.FILES.getlist('files')
    if not files:
        return JsonResponse({'ok': False, 'error': 'No se recibieron archivos'}, status=400)

    preview_records = []
    errors = []

    # Definición de cortes fixed-width (igual que en api_upload_view)
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
        ("qna_ini", 153, 157),
    ]
    REQUIRED_LINE_LEN = 157
    REQUIRED_MIN_LEN = 100

    for f in files:
        try:
            content = f.read()
            try:
                text = content.decode('utf-8')
            except UnicodeDecodeError:
                text = content.decode('latin-1')

            lines = [ln.rstrip('\r\n') for ln in text.splitlines() if ln.strip()]
            if not lines:
                continue

            for idx, line in enumerate(lines, start=1):
                if len(line) < REQUIRED_MIN_LEN:
                    errors.append({'file': f.name, 'line': idx, 'error': f'Longitud {len(line)} < {REQUIRED_MIN_LEN}'})
                    continue
                if len(line) < REQUIRED_LINE_LEN:
                    line = line.ljust(REQUIRED_LINE_LEN)
                data = {field: line[start:end].rstrip() for field, start, end in FIELDS}
                # Sobrescribir con sesión
                data['lote_anterior'] = request.session.get('lote_anterior') or data['lote_anterior']
                data['qna_ini'] = request.session.get('qna_ini') or data['qna_ini']
                preview_records.append(data)
        except Exception as e:
            errors.append({'file': f.name, 'error': str(e)})

    # Guardar en sesión para mostrar en carga.html
    request.session['preview_records'] = preview_records
    request.session['preview_errors'] = errors
    print(f"DEBUG: Preview records guardados en sesión: {len(preview_records)} registros")  # Depuración
    print(f"DEBUG: Errores en preview: {errors}")  # Depuración

    return JsonResponse({'ok': True, 'preview_count': len(preview_records), 'errors': errors})
