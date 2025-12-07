from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    UsuarioPersonalizadoViewSet,
    PerfilUsuarioViewSet,
    RegistroFirmaViewSet,
    ProductoViewSet,
    TipoProductoViewSet,
    MateriaPrimaViewSet,
    MaterialEnvasePrimarioViewSet,
    MaterialEnvaseSecundarioEmpaqueViewSet,
    ControlCalidadViewSet,
    PlanillaFabricacionViewSet,
    PlanillaEnvaseViewSet,
    PlanillaEnvasePrimarioViewSet,
    JarabeViewSet,
    BodegaViewSet,
    StockMateriaPrimaViewSet,
    StockMaterialEnvasePrimarioViewSet,
    StockMaterialEnvaseSecundarioEmpaqueViewSet,
    PlanillaEnvaseSecundarioEmpaqueViewSet
)

router = DefaultRouter()

router.register(r'usuarios', UsuarioPersonalizadoViewSet)
router.register(r'perfiles', PerfilUsuarioViewSet)
router.register(r'registro-firmas', RegistroFirmaViewSet)
router.register(r'productos', ProductoViewSet)
router.register(r'tipos-producto', TipoProductoViewSet)
router.register(r'materias-primas', MateriaPrimaViewSet)
router.register(r'materiales-envase-primario', MaterialEnvasePrimarioViewSet)
router.register(
    r'materiales-envase-secundario-empaque',
    MaterialEnvaseSecundarioEmpaqueViewSet
)
router.register(r'controles-calidad', ControlCalidadViewSet)
router.register(r'planillas-fabricacion-Pedido', PlanillaFabricacionViewSet)
router.register(r'planillas-envase', PlanillaEnvaseViewSet)
router.register(
    r'planillas-envase-primario-Pedido',
    PlanillaEnvasePrimarioViewSet
)
router.register(r'jarabes', JarabeViewSet)
router.register(r'bodegas', BodegaViewSet)
router.register(r'stock-materias-primas', StockMateriaPrimaViewSet)
router.register(
    r'stock-materiales-envase-primario',
    StockMaterialEnvasePrimarioViewSet
)
router.register(
    r'stock-materiales-envase-secundario',
    StockMaterialEnvaseSecundarioEmpaqueViewSet
)
router.register(r'planilla-envase-Secundario-empaque',
                PlanillaEnvaseSecundarioEmpaqueViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]
