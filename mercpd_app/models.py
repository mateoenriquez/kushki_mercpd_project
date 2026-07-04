from django.db import models
from decimal import Decimal


class Usuario(models.Model):
    usuarioid = models.AutoField(primary_key=True, db_column='UsuarioID')
    nombre = models.CharField(max_length=100, db_column='Nombre')
    rol = models.CharField(max_length=50, db_column='Rol')
    email = models.CharField(max_length=100, unique=True, db_column='Email')
    passwordhash = models.CharField(max_length=255, db_column='PasswordHash', blank=True, null=True)
    fechacreacion = models.DateTimeField(auto_now_add=True, db_column='FechaCreacion')

    class Meta:
        managed = False
        db_table = '[mercpd].[Usuarios]'


class Activo(models.Model):
    activoid = models.AutoField(primary_key=True, db_column='ActivoID')
    nombre = models.CharField(max_length=150, db_column='Nombre')
    categoria = models.CharField(max_length=50, db_column='Categoria')
    custodio = models.ForeignKey(Usuario, models.DO_NOTHING, db_column='CustodioID', blank=True, null=True)

    # Variables Triada CIA
    confidencialidad = models.IntegerField(db_column='Confidencialidad')
    integridad = models.IntegerField(db_column='Integridad')
    disponibilidad = models.IntegerField(db_column='Disponibilidad')

    valoractivo = models.DecimalField(max_digits=5, decimal_places=3, db_column='ValorActivo')
    fecharegistro = models.DateTimeField(auto_now_add=True, db_column='FechaRegistro')

    class Meta:
        managed = False
        db_table = '[mercpd].[Activos]'


class Amenaza(models.Model):
    amenazaid = models.AutoField(primary_key=True, db_column='AmenazaID')
    tipo = models.CharField(max_length=50, db_column='Tipo')
    nombre = models.CharField(max_length=150, db_column='Nombre')
    descripcion = models.CharField(max_length=500, db_column='Descripcion', blank=True, null=True)

    class Meta:
        managed = False
        db_table = '[mercpd].[Amenazas]'


class Vulnerabilidad(models.Model):
    vulnerabilidadid = models.AutoField(primary_key=True, db_column='VulnerabilidadID')
    tipo = models.CharField(max_length=50, db_column='Tipo')
    nombre = models.CharField(max_length=150, db_column='Nombre')
    descripcion = models.CharField(max_length=500, db_column='Descripcion', blank=True, null=True)

    class Meta:
        managed = False
        db_table = '[mercpd].[Vulnerabilidades]'


class EscenarioRiesgo(models.Model):
    escenarioid = models.AutoField(primary_key=True, db_column='EscenarioID')
    activo = models.ForeignKey(Activo, models.DO_NOTHING, db_column='ActivoID')
    amenaza = models.ForeignKey(Amenaza, models.DO_NOTHING, db_column='AmenazaID')
    vulnerabilidad = models.ForeignKey(Vulnerabilidad, models.DO_NOTHING, db_column='VulnerabilidadID')

    # Variables analíticas
    probabilidad = models.IntegerField(db_column='Probabilidad')
    impactooperativo = models.IntegerField(db_column='ImpactoOperativo')
    impactospdp = models.IntegerField(db_column='ImpactoSPDP')
    impactofinanciero = models.IntegerField(db_column='ImpactoFinanciero')

    # Resultados calculados
    impactobase = models.IntegerField(db_column='ImpactoBase')
    impactofinal = models.DecimalField(max_digits=5, decimal_places=3, db_column='ImpactoFinal')
    riesgototal = models.DecimalField(max_digits=5, decimal_places=3, db_column='RiesgoTotal')
    fechaevaluacion = models.DateTimeField(auto_now_add=True, db_column='FechaEvaluacion')

    # Trazabilidad temporal (Sección 6.3 de la metodología MERC-PD): plazo
    # máximo para tratar el riesgo, calculado según su nivel (Bajo/Medio/
    # Alto/Crítico) en el momento del registro.
    fechalimitetratamiento = models.DateTimeField(db_column='FechaLimiteTratamiento', blank=True, null=True)

    class Meta:
        managed = False
        db_table = '[mercpd].[EscenariosRiesgo]'


class Tratamiento(models.Model):
    tratamientoid = models.AutoField(primary_key=True, db_column='TratamientoID')
    escenario = models.ForeignKey(EscenarioRiesgo, models.DO_NOTHING, db_column='EscenarioID')
    opciontratamiento = models.CharField(max_length=50, db_column='OpcionTratamiento')
    controlaplicado = models.CharField(max_length=500, db_column='ControlAplicado')
    eficaciacontrol = models.DecimalField(max_digits=3, decimal_places=2, db_column='EficaciaControl')
    riesgoresidual = models.DecimalField(max_digits=5, decimal_places=3, db_column='RiesgoResidual', default=Decimal('0.000'))
    fechatratamiento = models.DateTimeField(auto_now_add=True, db_column='FechaTratamiento')

    # Evidencia de cumplimiento SLA: plazo que estaba vigente al registrar
    # este tratamiento (permite calcular el KPI de cumplimiento de la matriz).
    fechalimitecierre = models.DateTimeField(db_column='FechaLimiteCierre', blank=True, null=True)

    class Meta:
        managed = False
        db_table = '[mercpd].[Tratamientos]'

class Comunicacion(models.Model):
    TIPO_CHOICES = [
        ('Observacion', 'Observación'),
        ('Recomendacion', 'Recomendación'),
    ]
    comunicacionid = models.AutoField(primary_key=True, db_column='ComunicacionID')
    escenario = models.ForeignKey(EscenarioRiesgo, models.DO_NOTHING, db_column='EscenarioID')
    usuario = models.ForeignKey(Usuario, models.DO_NOTHING, db_column='UsuarioID', blank=True, null=True)
    tipo = models.CharField(max_length=20, db_column='Tipo', choices=TIPO_CHOICES)
    contenido = models.CharField(max_length=1000, db_column='Contenido')
    fechacomunicacion = models.DateTimeField(auto_now_add=True, db_column='FechaComunicacion')

    class Meta:
        managed = False
        db_table = '[mercpd].[Comunicaciones]'