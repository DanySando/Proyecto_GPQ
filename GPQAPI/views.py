from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
import hashlib
import datetime
from decimal import Decimal  # <-- IMPORTANTE

from .models import (
    UsuarioPersonalizado,
    PerfilUsuario,
    RegistroFirma,
    Producto,
    TipoProducto,
    MateriaPrima,
    MaterialEnvasePrimario,
    MaterialEnvaseSecundarioEmpaque,
    ControlCalidad,
    PlanillaFabricacion,
    PlanillaEnvase,
    PlanillaEnvasePrimario,
    PlanillaEnvaseSecundarioEmpaque,
    Jarabe,
    Bodega,
    StockMateriaPrima,
    StockMaterialEnvasePrimario,
    StockMaterialEnvaseSecundarioEmpaque,
)

from .serializers import (
    UsuarioPersonalizadoSerializer,
    PerfilUsuarioSerializer,
    RegistroFirmaSerializer,
    ProductoSerializer,
    TipoProductoSerializer,
    MateriaPrimaSerializer,
    MaterialEnvasePrimarioSerializer,
    MaterialEnvaseSecundarioEmpaqueSerializer,
    ControlCalidadSerializer,
    PlanillaFabricacionSerializer,
    PlanillaEnvaseSerializer,
    PlanillaEnvasePrimarioSerializer,
    PlanillaEnvaseSecundarioEmpaqueSerializer,
    JarabeSerializer,
    FirmaSerializer,
    BodegaSerializer,
    StockMateriaPrimaSerializer,
    StockMaterialEnvasePrimarioSerializer,
    StockMaterialEnvaseSecundarioEmpaqueSerializer,
)

User = get_user_model()


# ===========================================================
# HELPERS
# ===========================================================
def obtener_bodega_principal(tipo, nombre_por_defecto):
    """
    Devuelve la bodega principal de un tipo (MP, EP, ES).
    Si no existe, la crea con el nombre_por_defecto.
    """
    bodega = Bodega.objects.filter(tipo=tipo, es_principal=True).first()
    if bodega:
        return bodega

    bodega, _ = Bodega.objects.get_or_create(
        nombre=nombre_por_defecto,
        defaults={
            "tipo": tipo,
            "ubicacion": "Principal",
            "es_principal": True,
        },
    )
    return bodega


# ===========================================================
# USUARIOS
# ===========================================================
class UsuarioPersonalizadoViewSet(viewsets.ModelViewSet):
    queryset = UsuarioPersonalizado.objects.all()
    serializer_class = UsuarioPersonalizadoSerializer


class PerfilUsuarioViewSet(viewsets.ModelViewSet):
    queryset = PerfilUsuario.objects.all()
    serializer_class = PerfilUsuarioSerializer


class RegistroFirmaViewSet(viewsets.ModelViewSet):
    queryset = RegistroFirma.objects.all()
    serializer_class = RegistroFirmaSerializer


# ===========================================================
# BODEGAS Y STOCK
# ===========================================================
class BodegaViewSet(viewsets.ModelViewSet):
    queryset = Bodega.objects.all()
    serializer_class = BodegaSerializer


class StockMateriaPrimaViewSet(viewsets.ModelViewSet):
    queryset = StockMateriaPrima.objects.all()
    serializer_class = StockMateriaPrimaSerializer

    def create(self, request, *args, **kwargs):
        """
        Upsert de stock de materia prima en la bodega principal.
        Si ya existe (Bodega MP principal, materia_prima) se ACTUALIZA
        cantidad_disponible en lugar de crear un nuevo registro.
        """
        materia_id = request.data.get("materia_prima")
        cantidad = request.data.get("cantidad_disponible")

        if materia_id is None or cantidad is None:
            return super().create(request, *args, **kwargs)

        try:
            cantidad = Decimal(str(cantidad))
        except Exception:
            return Response(
                {"detalle": "cantidad_disponible debe ser numérico"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bodega_mp = obtener_bodega_principal("MP", "Bodega Materias Primas")

        stock, created = StockMateriaPrima.objects.get_or_create(
            bodega=bodega_mp,
            materia_prima_id=materia_id,
            defaults={"cantidad_disponible": cantidad},
        )

        if not created:
            stock.cantidad_disponible = cantidad
            stock.save()

        serializer = self.get_serializer(stock)
        code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=code)


class StockMaterialEnvasePrimarioViewSet(viewsets.ModelViewSet):
    queryset = StockMaterialEnvasePrimario.objects.all()
    serializer_class = StockMaterialEnvasePrimarioSerializer

    def create(self, request, *args, **kwargs):
        """
        Upsert de stock de envase primario en la bodega principal.
        Si ya existe (Bodega EP principal, material_envase_primario)
        se ACTUALIZA cantidad_disponible.
        """
        material_id = request.data.get("material_envase_primario")
        cantidad = request.data.get("cantidad_disponible")

        if material_id is None or cantidad is None:
            return super().create(request, *args, **kwargs)

        try:
            cantidad = Decimal(str(cantidad))
        except Exception:
            return Response(
                {"detalle": "cantidad_disponible debe ser numérico"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bodega_ep = obtener_bodega_principal("EP", "Bodega Envase Primario")

        stock, created = StockMaterialEnvasePrimario.objects.get_or_create(
            bodega=bodega_ep,
            material_envase_primario_id=material_id,
            defaults={"cantidad_disponible": cantidad},
        )

        if not created:
            stock.cantidad_disponible = cantidad
            stock.save()

        serializer = self.get_serializer(stock)
        code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=code)


class StockMaterialEnvaseSecundarioEmpaqueViewSet(viewsets.ModelViewSet):
    queryset = StockMaterialEnvaseSecundarioEmpaque.objects.all()
    serializer_class = StockMaterialEnvaseSecundarioEmpaqueSerializer

    def create(self, request, *args, **kwargs):
        """
        Upsert de stock de envase secundario/empaque en la bodega principal.
        Si ya existe (Bodega ES principal, material_envase_secundario_empaque)
        se ACTUALIZA cantidad_disponible.
        """
        material_id = request.data.get("material_envase_secundario_empaque")
        cantidad = request.data.get("cantidad_disponible")

        if material_id is None or cantidad is None:
            return super().create(request, *args, **kwargs)

        try:
            cantidad = Decimal(str(cantidad))
        except Exception:
            return Response(
                {"detalle": "cantidad_disponible debe ser numérico"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bodega_es = obtener_bodega_principal("ES", "Bodega Envase Secundario")

        stock, created = StockMaterialEnvaseSecundarioEmpaque.objects.get_or_create(
            bodega=bodega_es,
            material_envase_secundario_empaque_id=material_id,
            defaults={"cantidad_disponible": cantidad},
        )

        if not created:
            stock.cantidad_disponible = cantidad
            stock.save()

        serializer = self.get_serializer(stock)
        code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=code)


# ===========================================================
# PRODUCTOS
# ===========================================================
class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer


class TipoProductoViewSet(viewsets.ModelViewSet):
    queryset = TipoProducto.objects.all()
    serializer_class = TipoProductoSerializer


class MateriaPrimaViewSet(viewsets.ModelViewSet):
    queryset = MateriaPrima.objects.all()
    serializer_class = MateriaPrimaSerializer

    def perform_create(self, serializer):
        materia = serializer.save()

        bodega_mp = obtener_bodega_principal("MP", "Bodega Materias Primas")

        # Upsert inicial: si ya existiera, se suma la cantidad
        stock, created = StockMateriaPrima.objects.get_or_create(
            bodega=bodega_mp,
            materia_prima=materia,
            defaults={"cantidad_disponible": materia.cantidad},
        )
        if not created:
            stock.cantidad_disponible = stock.cantidad_disponible + materia.cantidad
            stock.save()


class MaterialEnvasePrimarioViewSet(viewsets.ModelViewSet):
    queryset = MaterialEnvasePrimario.objects.all()
    serializer_class = MaterialEnvasePrimarioSerializer

    def perform_create(self, serializer):
        material = serializer.save()

        bodega_ep = obtener_bodega_principal("EP", "Bodega Envase Primario")

        # Upsert inicial (queda en 0 hasta que lo ajustes por API de stock)
        StockMaterialEnvasePrimario.objects.get_or_create(
            bodega=bodega_ep,
            material_envase_primario=material,
            defaults={"cantidad_disponible": 0},
        )


class MaterialEnvaseSecundarioEmpaqueViewSet(viewsets.ModelViewSet):
    queryset = MaterialEnvaseSecundarioEmpaque.objects.all()
    serializer_class = MaterialEnvaseSecundarioEmpaqueSerializer

    def perform_create(self, serializer):
        material = serializer.save()

        bodega_es = obtener_bodega_principal("ES", "Bodega Envase Secundario")

        StockMaterialEnvaseSecundarioEmpaque.objects.get_or_create(
            bodega=bodega_es,
            material_envase_secundario_empaque=material,
            defaults={"cantidad_disponible": 0},
        )


# ===========================================================
# CONTROL DE CALIDAD
# ===========================================================
class ControlCalidadViewSet(viewsets.ModelViewSet):
    queryset = ControlCalidad.objects.all()
    serializer_class = ControlCalidadSerializer

    def get_serializer_class(self):
        if getattr(self, "action", None) == "firmar":
            return FirmaSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        return ControlCalidad.objects.all()

    @action(detail=True, methods=["post"])
    def firmar(self, request, pk=None):
        control_calidad = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            return self._procesar_firma_control_calidad(
                control_calidad, serializer.validated_data, request
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _procesar_firma_control_calidad(self, control_calidad, data, request):
        try:
            user = User.objects.get(rut=data["rut"])
        except User.DoesNotExist:
            return Response(
                {"error": "RUT o contraseña inválidos"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.check_password(data["password"]):
            return Response(
                {"error": "RUT o contraseña inválidos"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not self._tiene_permiso_firma(user, control_calidad):
            return Response(
                {"error": "No tiene permisos para firmar este control de calidad"},
                status=status.HTTP_403_FORBIDDEN,
            )

        firma_hash = self._generar_hash_firma(user, control_calidad)

        registro_firma = RegistroFirma.objects.create(
            usuario=user,
            firma_hash=firma_hash,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        control_calidad.firma_control_calidad = registro_firma
        control_calidad.aprobado = True
        control_calidad.save(
            update_fields=["firma_control_calidad", "aprobado"]
        )

        mp = control_calidad.materia_prima
        if mp:
            mp.firma_inspector_calidad = registro_firma
            mp.actualizar_estado_aprobacion()

        mep = control_calidad.material_envase_primario
        if mep:
            mep.actualizar_estado_aprobacion(control_calidad)

        mes = control_calidad.material_envase_secundario_empaque
        if mes:
            mes.actualizar_estado_aprobacion(control_calidad)

        return Response(
            {
                "mensaje": "Control de calidad firmado correctamente",
                "firma_id": registro_firma.id,
                "timestamp": registro_firma.timestamp_firma,
                "aprobado": control_calidad.aprobado,
            }
        )

    def _tiene_permiso_firma(self, user, control_calidad):
        try:
            rol = user.perfilusuario.rol
        except PerfilUsuario.DoesNotExist:
            return False
        return rol == "INSPECTOR_CALIDAD"

    def _generar_hash_firma(self, user, control_calidad):
        data = (
            f"{user.rut}{control_calidad.id}"
            f"{datetime.datetime.now().isoformat()}"
        )
        return hashlib.sha256(data.encode()).hexdigest()

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        return (
            x_forwarded_for.split(",")[0]
            if x_forwarded_for
            else request.META.get("REMOTE_ADDR")
        )


# ===========================================================
# PLANILLA FABRICACIÓN
# ===========================================================
class PlanillaFabricacionViewSet(viewsets.ModelViewSet):
    queryset = PlanillaFabricacion.objects.all()
    serializer_class = PlanillaFabricacionSerializer

    def perform_create(self, serializer):
        usuario = (
            self.request.user.username
            if self.request.user.is_authenticated
            else "Sistema"
        )
        planilla = serializer.save(
            usuario_creacion=usuario,
            usuario_ultima_modificacion=usuario,
        )
        self._aplicar_movimiento_bodega(planilla)

    def perform_update(self, serializer):
        usuario = (
            self.request.user.username
            if self.request.user.is_authenticated
            else "Sistema"
        )
        serializer.save(usuario_ultima_modificacion=usuario)

    @action(detail=True, methods=["post"])
    def firmar(self, request, pk=None):
        planilla = self.get_object()
        serializer = FirmaSerializer(data=request.data)

        if serializer.is_valid():
            return self._procesar_firma(
                planilla, serializer.validated_data, request
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _procesar_firma(self, planilla, data, request):
        try:
            user = User.objects.get(rut=data["rut"])
        except User.DoesNotExist:
            return Response(
                {"error": "RUT o contraseña inválidos"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.check_password(data["password"]):
            return Response(
                {"error": "RUT o contraseña inválidos"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not self._tiene_permiso_firma(user):
            return Response(
                {"error": "No tiene permisos para esta firma"},
                status=status.HTTP_403_FORBIDDEN,
            )

        firma_hash = self._generar_hash_firma(user, planilla)

        registro_firma = RegistroFirma.objects.create(
            usuario=user,
            planilla_fabricacion=planilla,
            firma_hash=firma_hash,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        planilla.refresh_from_db()

        return Response(
            {
                "mensaje": "Firma registrada",
                "firma_id": registro_firma.id,
                "estado_aprobacion": planilla.estado_aprobacion,
            }
        )

    def _tiene_permiso_firma(self, user):
        try:
            rol = user.perfilusuario.rol
        except PerfilUsuario.DoesNotExist:
            return False
        return rol in {
            "JEFE_SECCION",
            "JEFE_PRODUCCION",
            "QUIMICO_FARMACEUTICO",
        }

    def _aplicar_movimiento_bodega(self, planilla: PlanillaFabricacion):
        if planilla.tipo_movimiento != "PEDIDO_BODEGA":
            return

        if planilla.cantidad_entregada is None or planilla.cantidad_entregada <= 0:
            return

        bodega_mp = obtener_bodega_principal("MP", "Bodega Materias Primas")

        stock, _ = StockMateriaPrima.objects.get_or_create(
            bodega=bodega_mp,
            materia_prima=planilla.materia_prima,
            defaults={"cantidad_disponible": 0},
        )

        nueva_cantidad = stock.cantidad_disponible - planilla.cantidad_entregada
        if nueva_cantidad < 0:
            nueva_cantidad = 0

        stock.cantidad_disponible = nueva_cantidad
        stock.save()

    def _generar_hash_firma(self, user, planilla):
        data = (
            f"{user.rut}{planilla.id}{datetime.datetime.now().isoformat()}"
        )
        return hashlib.sha256(data.encode()).hexdigest()

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        return (
            x_forwarded_for.split(",")[0]
            if x_forwarded_for
            else request.META.get("REMOTE_ADDR")
        )


# ===========================================================
# PLANILLA ENVASE
# ===========================================================
class PlanillaEnvaseViewSet(viewsets.ModelViewSet):
    queryset = PlanillaEnvase.objects.all()
    serializer_class = PlanillaEnvaseSerializer

    def perform_create(self, serializer):
        usuario = (
            self.request.user.username
            if self.request.user.is_authenticated
            else "Sistema"
        )
        serializer.save(
            usuario_creacion=usuario,
            usuario_ultima_modificacion=usuario,
        )

    def perform_update(self, serializer):
        usuario = (
            self.request.user.username
            if self.request.user.is_authenticated
            else "Sistema"
        )
        serializer.save(usuario_ultima_modificacion=usuario)


# ===========================================================
# PLANILLA ENVASE PRIMARIO
# ===========================================================
class PlanillaEnvasePrimarioViewSet(viewsets.ModelViewSet):
    queryset = PlanillaEnvasePrimario.objects.all()
    serializer_class = PlanillaEnvasePrimarioSerializer

    def perform_create(self, serializer):
        usuario = (
            self.request.user.username
            if self.request.user.is_authenticated
            else "Sistema"
        )
        planilla = serializer.save(
            usuario_creacion=usuario,
            usuario_ultima_modificacion=usuario,
        )
        self._aplicar_movimiento_bodega(planilla)

    def perform_update(self, serializer):
        usuario = (
            self.request.user.username
            if self.request.user.is_authenticated
            else "Sistema"
        )
        serializer.save(usuario_ultima_modificacion=usuario)

    @action(detail=True, methods=["post"])
    def firmar(self, request, pk=None):
        planilla = self.get_object()
        serializer = FirmaSerializer(data=request.data)

        if serializer.is_valid():
            return self._procesar_firma(
                planilla, serializer.validated_data, request
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _procesar_firma(self, planilla, data, request):
        try:
            user = User.objects.get(rut=data["rut"])
        except User.DoesNotExist:
            return Response(
                {"error": "RUT o contraseña inválidos"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.check_password(data["password"]):
            return Response(
                {"error": "RUT o contraseña inválidos"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not self._tiene_permiso_firma(user):
            return Response(
                {"error": "No tiene permisos para esta firma"},
                status=status.HTTP_403_FORBIDDEN,
            )

        firma_hash = self._generar_hash_firma(user, planilla)

        registro_firma = RegistroFirma.objects.create(
            usuario=user,
            planilla_envase_primario=planilla,
            firma_hash=firma_hash,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        planilla.refresh_from_db()

        return Response(
            {
                "mensaje": "Firma registrada",
                "firma_id": registro_firma.id,
                "estado_aprobacion": planilla.estado_aprobacion,
            }
        )

    def _tiene_permiso_firma(self, user):
        try:
            rol = user.perfilusuario.rol
        except PerfilUsuario.DoesNotExist:
            return False
        return rol in {
            "JEFE_SECCION",
            "JEFE_PRODUCCION",
            "QUIMICO_FARMACEUTICO",
        }

    def _aplicar_movimiento_bodega(self, planilla: PlanillaEnvasePrimario):
        if planilla.tipo_movimiento != "PEDIDO_BODEGA":
            return

        if planilla.cantidad_entregada is None or planilla.cantidad_entregada <= 0:
            return

        bodega_ep = obtener_bodega_principal("EP", "Bodega Envase Primario")

        stock, _ = StockMaterialEnvasePrimario.objects.get_or_create(
            bodega=bodega_ep,
            material_envase_primario=planilla.material_envase_primario,
            defaults={"cantidad_disponible": 0},
        )

        nueva_cantidad = stock.cantidad_disponible - planilla.cantidad_entregada
        if nueva_cantidad < 0:
            nueva_cantidad = 0

        stock.cantidad_disponible = nueva_cantidad
        stock.save()

    def _generar_hash_firma(self, user, planilla):
        data = (
            f"{user.rut}{planilla.id}{datetime.datetime.now().isoformat()}"
        )
        return hashlib.sha256(data.encode()).hexdigest()

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        return (
            x_forwarded_for.split(",")[0]
            if x_forwarded_for
            else request.META.get("REMOTE_ADDR")
        )


# ===========================================================
# PLANILLA ENVASE SECUNDARIO Y EMPAQUE
# ===========================================================
class PlanillaEnvaseSecundarioEmpaqueViewSet(viewsets.ModelViewSet):
    queryset = PlanillaEnvaseSecundarioEmpaque.objects.all()
    serializer_class = PlanillaEnvaseSecundarioEmpaqueSerializer

    def perform_create(self, serializer):
        usuario = (
            self.request.user.username
            if self.request.user.is_authenticated
            else "Sistema"
        )
        serializer.save(
            usuario_creacion=usuario,
            usuario_ultima_modificacion=usuario,
        )

    def perform_update(self, serializer):
        usuario = (
            self.request.user.username
            if self.request.user.is_authenticated
            else "Sistema"
        )
        serializer.save(usuario_ultima_modificacion=usuario)

    @action(detail=True, methods=["post"])
    def firmar(self, request, pk=None):
        planilla = self.get_object()
        serializer = FirmaSerializer(data=request.data)

        if serializer.is_valid():
            return self._procesar_firma(
                planilla, serializer.validated_data, request
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _procesar_firma(self, planilla, data, request):
        try:
            user = User.objects.get(rut=data["rut"])
        except User.DoesNotExist:
            return Response(
                {"error": "RUT o contraseña inválidos"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.check_password(data["password"]):
            return Response(
                {"error": "RUT o contraseña inválidos"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not self._tiene_permiso_firma(user):
            return Response(
                {"error": "No tiene permisos para esta firma"},
                status=status.HTTP_403_FORBIDDEN,
            )

        estado_inicial = planilla.estado_aprobacion

        firma_hash = self._generar_hash_firma(user, planilla)

        registro_firma = RegistroFirma.objects.create(
            usuario=user,
            planilla_envase_secundario_empaque=planilla,
            firma_hash=firma_hash,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        planilla.refresh_from_db()

        if (
            estado_inicial != "APROBADO"
            and planilla.estado_aprobacion == "APROBADO"
        ):
            self._aplicar_movimiento_bodega(planilla)

        return Response(
            {
                "mensaje": "Firma registrada",
                "firma_id": registro_firma.id,
                "estado_aprobacion": planilla.estado_aprobacion,
            }
        )

    def _tiene_permiso_firma(self, user):
        try:
            rol = user.perfilusuario.rol
        except PerfilUsuario.DoesNotExist:
            return False

        return rol in {
            "JEFE_SECCION",
            "JEFE_PRODUCCION",
            "QUIMICO_FARMACEUTICO",
        }

    def _aplicar_movimiento_bodega(self, planilla: PlanillaEnvaseSecundarioEmpaque):
        if planilla.tipo_movimiento != "PEDIDO_BODEGA":
            return

        if planilla.cantidad_entregada is None or planilla.cantidad_entregada <= 0:
            return

        bodega_es = obtener_bodega_principal("ES", "Bodega Envase Secundario")

        stock, _ = StockMaterialEnvaseSecundarioEmpaque.objects.get_or_create(
            bodega=bodega_es,
            material_envase_secundario_empaque=planilla.material_envase_secundario_empaque,
            defaults={"cantidad_disponible": 0},
        )

        if stock.cantidad_disponible < planilla.cantidad_entregada:
            print(
                f"DEBUG: No se descuenta stock ES; disponible={stock.cantidad_disponible}, "
                f"solicitado={planilla.cantidad_entregada}"
            )
            return

        stock.cantidad_disponible = (
            stock.cantidad_disponible - planilla.cantidad_entregada
        )
        stock.save()

    def _generar_hash_firma(self, user, planilla):
        data = (
            f"{user.rut}{planilla.id}{datetime.datetime.now().isoformat()}"
        )
        return hashlib.sha256(data.encode()).hexdigest()

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        return (
            x_forwarded_for.split(",")[0]
            if x_forwarded_for
            else request.META.get("REMOTE_ADDR")
        )


# ===========================================================
# JARABE (CONTENEDOR DE PLANILLAS)
# ===========================================================
class JarabeViewSet(viewsets.ModelViewSet):
    queryset = Jarabe.objects.all()
    serializer_class = JarabeSerializer

    @action(detail=True, methods=["get"])
    def fabricacion(self, request, pk=None):
        jarabe = self.get_object()

        if not jarabe.planilla_fabricacion:
            return Response(
                {"detalle": "No existe planilla de fabricación asociada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PlanillaFabricacionSerializer(jarabe.planilla_fabricacion)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def envase(self, request, pk=None):
        jarabe = self.get_object()

        if not jarabe.planilla_envase:
            return Response(
                {"detalle": "No existe planilla de envase asociada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PlanillaEnvaseSerializer(jarabe.planilla_envase)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="envase-primario")
    def envase_primario(self, request, pk=None):
        jarabe = self.get_object()

        if not jarabe.planilla_envase_primario:
            return Response(
                {"detalle": "No existe planilla de envase primario asociada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = PlanillaEnvasePrimarioSerializer(
            jarabe.planilla_envase_primario
        )
        return Response(serializer.data)
