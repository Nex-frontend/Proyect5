from django.db import models
from django.contrib.auth.models import User

class Record(models.Model):
    # Campos de ejemplo (ajusta según tus registros Foviste reales)
    folio = models.CharField(max_length=50, db_index=True)
    nombre = models.CharField(max_length=150)
    curp = models.CharField(max_length=18, blank=True, null=True, db_index=True)
    rfc = models.CharField(max_length=13, blank=True, null=True, db_index=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado_en']

    def __str__(self):
        return f"{self.folio} - {self.nombre}"

class Activity(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    segmento = models.CharField(max_length=100)
    actividad = models.CharField(max_length=200)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado_en']

    def __str__(self):
        return f"{self.user} - {self.segmento} - {self.actividad}"
