from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    UsuarioPersonalizadoViewSet,
    RolViewSet,
    PerfilUsuarioViewSet,
    RegistroFirmaViewSet,
    ProductoViewSet,
    TipoProductoViewSet,
    MateriaPrimaViewSet,
    MaterialEnvasePrimarioViewSet,
    ControlCalidadViewSet,
    PlanillaFabricacionViewSet,
    PlanillaEnvaseViewSet,
    PlanillaEnvasePrimarioViewSet,
    JarabeViewSet,
)

router = DefaultRouter()

router.register(r'usuarios', UsuarioPersonalizadoViewSet)
router.register(r'roles', RolViewSet)
router.register(r'perfiles', PerfilUsuarioViewSet)
router.register(r'registro-firmas', RegistroFirmaViewSet)
router.register(r'productos', ProductoViewSet)
router.register(r'tipos-producto', TipoProductoViewSet)
router.register(r'materias-primas', MateriaPrimaViewSet)
router.register(r'materiales-envase-primario', MaterialEnvasePrimarioViewSet)
router.register(r'controles-calidad', ControlCalidadViewSet)
router.register(r'planillas-fabricacion-Pedido', PlanillaFabricacionViewSet)
router.register(r'planillas-envase', PlanillaEnvaseViewSet)
router.register(r'planillas-envase-primario-Pedido',
                PlanillaEnvasePrimarioViewSet)
router.register(r'jarabes', JarabeViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]
