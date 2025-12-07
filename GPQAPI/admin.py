from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *


@admin.register(UsuarioPersonalizado)
class UsuarioPersonalizadoAdmin(UserAdmin):
    list_display = ('username', 'rut', 'first_name',
                    'last_name', 'email', 'is_active')
    list_filter = ('is_active', 'is_staff', 'is_superuser')
    search_fields = ('username', 'rut', 'first_name', 'last_name', 'email')


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'rol', 'departamento')
    list_filter = ('rol', 'departamento')
    search_fields = ('usuario__username', 'usuario__rut', 'departamento')


@admin.register(RegistroFirma)
class RegistroFirmaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'tipo_firma', 'timestamp_firma')
    list_filter = ('tipo_firma', 'timestamp_firma')
    search_fields = ('usuario__username', 'usuario__rut')


@admin.register(MateriaPrima)
class MateriaPrimaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'batch', 'cantidad',
                    'estado_aprobacion', 'control_calidad')
    list_filter = ('estado_aprobacion',)
    search_fields = ('nombre', 'batch')


@admin.register(ControlCalidad)
class ControlCalidadAdmin(admin.ModelAdmin):
    list_display = ('codigo_control_calidad', 'producto',
                    'fecha_verificacion', 'aprobado')
    list_filter = ('aprobado', 'fecha_verificacion')
    search_fields = ('codigo_control_calidad', 'producto__nombre')


admin.site.register(TipoProducto)
admin.site.register(Producto)
admin.site.register(PlanillaFabricacion)
admin.site.register(PlanillaEnvase)
admin.site.register(PlanillaEnvasePrimario)
