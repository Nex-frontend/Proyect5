from django.contrib import admin
from .models import Record, Activity

@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    list_display = ("rfc", "nombre", "cadena1", "tipo", "impor", "cpto", "lote_actual", "qna", "ptje", "creado_en")
    search_fields = ("rfc", "nombre", "cadena1", "qna", "observacio", "lote_anterior", "qna_ini")

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("user", "segmento", "actividad", "creado_en")
    search_fields = ("user__username", "segmento", "actividad")
