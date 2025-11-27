from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *


@admin.register(UsuarioPersonalizado)
class UsuarioPersonalizadoAdmin(UserAdmin):
    list_display = ('username', 'rut', 'first_name',
                    'last_name', 'email', 'is_active')
    list_filter = ('is_active', 'is_staff', 'is_superuser')
    search_fields = ('username', 'rut', 'first_name', 'last_name', 'email')


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'rol', 'departamento', 'cargo')
    list_filter = ('rol', 'departamento')
    search_fields = ('usuario__username', 'usuario__rut', 'departamento')


@admin.register(RegistroFirma)
class RegistroFirmaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'tipo_firma',  'timestamp_firma')
    list_filter = ('tipo_firma', 'timestamp_firma')
    search_fields = ('usuario__username', 'usuario__rut')


# Registra los demás modelos
admin.site.register(TipoProducto)
admin.site.register(Producto)
admin.site.register(MateriaPrima)
admin.site.register(ControlCalidad)
admin.site.register(PlanillaFabricacion)
admin.site.register(PlanillaEnvase)
admin.site.register(PlanillaEnvasePrimario)
