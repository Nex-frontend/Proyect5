from django.apps import AppConfig


class FovissteConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fovisste'
    verbose_name = 'FOVISSTE'

    def ready(self):
        # Importa señales para crear roles/permisos tras migraciones
        from . import signals  # noqa: F401
