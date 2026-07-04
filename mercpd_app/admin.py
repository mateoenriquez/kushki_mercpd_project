from django.contrib import admin
from .models import Usuario, Activo, Amenaza, Vulnerabilidad, EscenarioRiesgo, Tratamiento, Comunicacion


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuarioid', 'nombre', 'rol', 'email', 'fechacreacion')
    search_fields = ('nombre', 'email')


@admin.register(Activo)
class ActivoAdmin(admin.ModelAdmin):
    list_display = ('activoid', 'nombre', 'categoria', 'custodio', 'valoractivo', 'fecharegistro')
    list_filter = ('categoria',)
    search_fields = ('nombre',)


@admin.register(Amenaza)
class AmenazaAdmin(admin.ModelAdmin):
    list_display = ('amenazaid', 'nombre', 'tipo')
    list_filter = ('tipo',)


@admin.register(Vulnerabilidad)
class VulnerabilidadAdmin(admin.ModelAdmin):
    list_display = ('vulnerabilidadid', 'nombre', 'tipo')
    list_filter = ('tipo',)


@admin.register(EscenarioRiesgo)
class EscenarioRiesgoAdmin(admin.ModelAdmin):
    list_display = ('escenarioid', 'activo', 'amenaza', 'vulnerabilidad', 'probabilidad', 'riesgototal', 'fechaevaluacion')
    list_filter = ('probabilidad',)


@admin.register(Tratamiento)
class TratamientoAdmin(admin.ModelAdmin):
    list_display = ('tratamientoid', 'escenario', 'opciontratamiento', 'eficaciacontrol', 'riesgoresidual', 'fechatratamiento')
    list_filter = ('opciontratamiento',)


@admin.register(Comunicacion)
class ComunicacionAdmin(admin.ModelAdmin):
    list_display = ('comunicacionid', 'escenario', 'tipo', 'usuario', 'fechacomunicacion')
    list_filter = ('tipo',)