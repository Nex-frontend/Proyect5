from django.db import models
from django.contrib.auth.models import User


class Record(models.Model):
    # Campos fixed-width (todos VARCHAR en MySQL según requerimiento)
    # Para facilitar migraciones y cargas iniciales, permitimos null/blank en todos.
    rfc = models.CharField(max_length=13, db_index=True, blank=True, null=True, default='')
    nombre = models.CharField(max_length=30, db_index=True, blank=True, null=True, default='')
    cadena1 = models.CharField(max_length=37, blank=True, null=True, default='')
    tipo = models.CharField(max_length=1, blank=True, null=True, default='')
    impor = models.CharField(max_length=8, blank=True, null=True, default='')
    cpto = models.CharField(max_length=2, blank=True, null=True, default='')
    lote_actual = models.CharField(max_length=1, blank=True, null=True, default='')
    qna = models.CharField(max_length=6, db_index=True, blank=True, null=True, default='')
    ptje = models.CharField(max_length=2, blank=True, null=True, default='')
    observacio = models.CharField(max_length=47, blank=True, null=True, default='')
    lote_anterior = models.CharField(max_length=6, blank=True, null=True, default='')
    qna_ini = models.CharField(max_length=6, blank=True, null=True, default='')

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado_en']

    def __str__(self):
        return f"{self.rfc} - {self.nombre}"


class Activity(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    segmento = models.CharField(max_length=100)
    actividad = models.CharField(max_length=200)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado_en']

    def __str__(self):
        return f"{self.user} - {self.segmento} - {self.actividad}"
