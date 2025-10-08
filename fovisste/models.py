from django.db import models
from django.contrib.auth.models import User


class Record(models.Model):
    # Campos de auditoría - nuevos campos agregados para rastreo
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
    lote_anterior = models.CharField(max_length=5, blank=True, null=True, default='')
    responsable = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Responsable de Carga') # Usuario que cargó el archivo
    qna_ini = models.CharField(max_length=6, blank=True, null=True, default='')
    fecha_carga = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Carga')
    # creado_en = models.DateTimeField(auto_now_add=True) # Fecha de creación - REMOVIDO, se usa fecha_carga

    class Meta: # Meta datos
        ordering = ['-fecha_carga']

    def __str__(self): # Representación en str
        return f"{self.rfc} - {self.nombre}"


class Activity(models.Model): # Modelo de actividad
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    segmento = models.CharField(max_length=100)
    actividad = models.CharField(max_length=200)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta: # Meta datos
        ordering = ['-creado_en']

    def __str__(self): # Representación en str
        return f"{self.user} - {self.segmento} - {self.actividad}"
