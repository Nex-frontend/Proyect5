## Instrucciones rápidas para agentes AI

Resumen corto (qué es este repo): proyecto Django llamado `Prestaciones` con una app principal `fovisste` que procesa archivos de ancho fijo (fixed-width), guarda registros en la tabla `Record` y mantiene un historial de `Activity`.

- Stack: Django 5.x, soporte MySQL/Postgres (controlado por `DB_ENGINE` en `Prestaciones/settings.py`). Ver `requirements.txt`.
- Flujo principal: el usuario configura `qna_ini` y `lote_anterior` (vista `qnaproceso_view`), sube archivos a `api_preview` para previsualizar (se guardan en sesión `preview_records`), confirma en `api_upload` y el servidor hace `bulk_create` sobre `Record`.

Puntos imprescindibles para ediciones y PRs

- Lee `fovisste/views.py` antes de tocar la lógica de carga. Ahí está toda la lógica de parsing fixed-width, validaciones, sesión y confirmación. Las constantes relevantes: `FIELDS`, `REQUIRED_MIN_LEN = 100` y `REQUIRED_LINE_LEN = 157`.
- Cambios en el modelo `Record` (`fovisste/models.py`) requieren migraciones; el proyecto asume que muchos campos permiten `null/blank` y tienen `default=''`. Mantén esa convención o actualiza migraciones y tests.
- El proyecto usa permisos y grupos: revisa `signup_view`, `ensure_roles()` y los decoradores `@permission_required('fovisste.add_record')` / `view_record`. Nuevos endpoints o cambios de autorización deben respetar este esquema.

Comandos frecuentes (local/develop)

  python -m pip install --upgrade pip; pip install -r requirements.txt

  python manage.py migrate
  python manage.py runserver

Ejecutar tests (el workflow usa pytest si está disponible, sino `manage.py test`):

  pytest -q
  # fallback:
  python manage.py test

Integración CI (referencia)

- `.github/workflows/django-tests.yml` ejecuta tests en matrix con `mysql` y `postgres`. Para reproducir localmente, ejecuta migraciones apuntando a la DB deseada y exporta `DB_ENGINE`.

Convenciones y patrones del código (ejemplos concretos)

- Parsing fixed-width: en `api_preview` y `api_upload` se usan los cortes:
  - rfc: [0:13], nombre: [13:43], cadena1: [43:80], tipo: [80:81], ... qna_ini: [153:157]
  - Si la línea tiene < 100 chars se trata como error; si está entre 100 y 157 se paddea con espacios.
- Sesión: claves usadas por el flujo — `qna_ini`, `lote_anterior`, `preview_records`, `preview_errors`. Los endpoints dependen de esos valores y muchos errores devolvemos JSON con `ok: False` y `error`.
- DB writes en batch: se utiliza `Record.objects.bulk_create(batch, batch_size=1000)` dentro de `transaction.atomic()`; ten cuidado con señales/post-save que asuman una instancia ya en la BD.

Pruebas y cómo ampliarlas

- Tests existentes están en `fovisste/tests/test_preview.py` y usan `django.test.Client` y `SimpleUploadedFile` para simular uploads y sesión. Antes de cambiar la forma en que se guardan `preview_records`, actualiza esos tests.
- Los tests asumen valores concretos: sesión con `qna_ini='202510'` y `lote_anterior='0001'`. Mantén compatibilidad o actualiza los fixtures.

Errores y trampas comunes (para revisar en PRs)

- Encoding: el código intenta `utf-8` y cae a `latin-1`. Prueba archivos con ambas codificaciones.
- Longitudes de línea: la lógica permite líneas >=100; si cambias los offsets actualiza también `fovisste/tests/test_preview.py` y las plantillas que muestran conteos.
- Duplicados: `has_existing_load` evita re-carga para misma combinación `responsable/qna_ini/lote_anterior`. Si modificas lógica de duplicados, actualiza mensajes y redirecciones en `carga_view` y `api_upload_view`.

Dónde mirar primero cuando algo falla

- `fovisste/views.py` — upload, preview y confirm
- `fovisste/models.py` — campos y defaults de `Record`
- `fovisste/tests/test_preview.py` — pruebas de flujo de preview/confirm
- `Prestaciones/settings.py` — comportamiento DB por `DB_ENGINE` y configuración por `.env`

Checklist rápido para PRs que toquen carga/parseo

1. Actualizar/ejecutar tests en `fovisste/tests` (pytest preferable)
2. Verificar migraciones si se cambian modelos
3. Probar uploads con archivos UTF-8 y Latin-1, y con líneas <100/ entre 100-157/ >157
4. Mantener mensajes de sesión/redirects consistentes (ej.: `qnaproceso` y `carga`)

Si algo no está claro, pide detalle sobre offsets exactos, ejemplos de payload JSON, o cómo replicar matrix DB localmente y lo amplio.
