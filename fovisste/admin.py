from django.contrib import admin
from .models import Record, Activity

@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    list_display = ("folio", "nombre", "curp", "rfc", "creado_en")
    search_fields = ("folio", "nombre", "curp", "rfc")

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("user", "segmento", "actividad", "creado_en")
    search_fields = ("user__username", "segmento", "actividad")
