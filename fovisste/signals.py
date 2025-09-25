from django.apps import apps
from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate
from django.dispatch import receiver

UPLOADER_GROUP = 'uploader'
VIEWER_GROUP = 'viewer'

@receiver(post_migrate)
def create_roles_and_permissions(sender, **kwargs):
    # Solo ejecutar después de migrar nuestra app
    if sender.label != 'fovisste':
        return

    # Crear grupos
    uploader_group, _ = Group.objects.get_or_create(name=UPLOADER_GROUP)
    viewer_group, _ = Group.objects.get_or_create(name=VIEWER_GROUP)

    # Obtener permisos de Record
    try:
        record_model = apps.get_model('fovisste', 'Record')
        opts = record_model._meta
        perms = Permission.objects.filter(content_type__app_label=opts.app_label, content_type__model=opts.model_name)
        perms_map = {p.codename: p for p in perms}
    except Exception:
        return

    # Asignar permisos:
    # - viewer: solo ver
    # - uploader: ver y agregar
    viewer_perms = [perms_map.get('view_record')]
    uploader_perms = [perms_map.get('view_record'), perms_map.get('add_record')]

    for p in viewer_perms:
        if p:
            viewer_group.permissions.add(p)
    for p in uploader_perms:
        if p:
            uploader_group.permissions.add(p)
