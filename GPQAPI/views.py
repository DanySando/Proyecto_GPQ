from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import authenticate
import hashlib
import datetime

from .models import (
    UsuarioPersonalizado,
    Rol,
    PerfilUsuario,
    RegistroFirma,
    Producto,
    TipoProducto,
    MateriaPrima,
    MaterialEnvasePrimario,
    ControlCalidad,
    PlanillaFabricacion,
    PlanillaEnvase,
    PlanillaEnvasePrimario,
    Jarabe,
)

from .serializers import (
    UsuarioPersonalizadoSerializer,
    RolSerializer,
    PerfilUsuarioSerializer,
    RegistroFirmaSerializer,
    ProductoSerializer,
    TipoProductoSerializer,
    MateriaPrimaSerializer,
    MaterialEnvasePrimarioSerializer,
    ControlCalidadSerializer,
    PlanillaFabricacionSerializer,
    PlanillaEnvaseSerializer,
    PlanillaEnvasePrimarioSerializer,
    JarabeSerializer,
    FirmaSerializer,
)


# ===========================================================
# USUARIOS
# ===========================================================
class UsuarioPersonalizadoViewSet(viewsets.ModelViewSet):
    queryset = UsuarioPersonalizado.objects.all()
    serializer_class = UsuarioPersonalizadoSerializer


class RolViewSet(viewsets.ModelViewSet):
    queryset = Rol.objects.all()
    serializer_class = RolSerializer


class PerfilUsuarioViewSet(viewsets.ModelViewSet):
    queryset = PerfilUsuario.objects.all()
    serializer_class = PerfilUsuarioSerializer


class RegistroFirmaViewSet(viewsets.ModelViewSet):
    queryset = RegistroFirma.objects.all()
    serializer_class = RegistroFirmaSerializer


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
    # La firma de materia prima viene desde ControlCalidad.firmar


class MaterialEnvasePrimarioViewSet(viewsets.ModelViewSet):
    queryset = MaterialEnvasePrimario.objects.all()
    serializer_class = MaterialEnvasePrimarioSerializer
    # La firma de este material también viene desde ControlCalidad.firmar


# ===========================================================
# CONTROL DE CALIDAD
# ===========================================================
class ControlCalidadViewSet(viewsets.ModelViewSet):

    queryset = ControlCalidad.objects.all()
    serializer_class = ControlCalidadSerializer

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return ControlCalidad.objects.none()

        try:
            rol = user.perfilusuario.rol.nombre
        except PerfilUsuario.DoesNotExist:
            return ControlCalidad.objects.none()

        # Solo los inspectores ven sus propios controles asignados
        if rol == "INSPECTOR_CALIDAD":
            return ControlCalidad.objects.filter(inspector=user)

        # Otros roles actualmente no ven nada
        return ControlCalidad.objects.none()

    @action(detail=True, methods=["post"])
    def firmar(self, request, pk=None):
        control_calidad = self.get_object()
        serializer = FirmaSerializer(data=request.data)

        if serializer.is_valid():
            return self._procesar_firma_control_calidad(
                control_calidad, serializer.validated_data, request
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _procesar_firma_control_calidad(self, control_calidad, data, request):
        user = authenticate(username=data["rut"], password=data["password"])

        if not user:
            return Response(
                {"error": "Credenciales inválidas"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not self._tiene_permiso_firma(user, control_calidad):
            return Response(
                {"error": "No tiene permisos para firmar este control de calidad"},
                status=status.HTTP_403_FORBIDDEN
            )

        firma_hash = self._generar_hash_firma(user, control_calidad)

        # 1) Crear registro de firma
        registro_firma = RegistroFirma.objects.create(
            usuario=user,
            firma_hash=firma_hash,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")
        )

        # 2) Actualizar control de calidad
        control_calidad.firma_control_calidad = registro_firma
        control_calidad.aprobado = True
        control_calidad.save(
            update_fields=["firma_control_calidad", "aprobado"]
        )

        # 3) Actualizar materia prima asociada (si existe)
        mp = control_calidad.materia_prima
        if mp:
            mp.firma_inspector_calidad = registro_firma
            mp.control_calidad = True
            mp.estado_aprobacion = "APROBADO"
            mp.save(update_fields=[
                "firma_inspector_calidad",
                "control_calidad",
                "estado_aprobacion",
            ])

        # 4) Actualizar material de envase primario asociado (si existe)
        mep = control_calidad.material_envase_primario
        if mep:
            mep.firma_inspector_calidad = registro_firma
            mep.control_calidad = True
            mep.estado_aprobacion = "APROBADO"
            mep.save(update_fields=[
                "firma_inspector_calidad",
                "control_calidad",
                "estado_aprobacion",
            ])

        return Response({
            "mensaje": "Control de calidad firmado correctamente",
            "firma_id": registro_firma.id,
            "timestamp": registro_firma.timestamp_firma,
            "aprobado": control_calidad.aprobado,
        })

    def _tiene_permiso_firma(self, user, control_calidad):
        """
        Debe:
        - tener rol INSPECTOR_CALIDAD
        - ser exactamente el inspector asignado al ControlCalidad
        """
        try:
            rol = user.perfilusuario.rol.nombre
        except PerfilUsuario.DoesNotExist:
            return False

        if rol != "INSPECTOR_CALIDAD":
            return False

        # solo el inspector asignado puede firmar este control
        return control_calidad.inspector_id == user.id

    def _generar_hash_firma(self, user, control_calidad):
        data = f"{user.rut}{control_calidad.id}{datetime.datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        return x_forwarded_for.split(",")[0] if x_forwarded_for else request.META.get("REMOTE_ADDR")


# ===========================================================
# PLANILLA FABRICACIÓN
# ===========================================================
class PlanillaFabricacionViewSet(viewsets.ModelViewSet):
    queryset = PlanillaFabricacion.objects.all()
    serializer_class = PlanillaFabricacionSerializer

    def perform_create(self, serializer):
        usuario = self.request.user.username if self.request.user.is_authenticated else "Sistema"
        serializer.save(
            usuario_creacion=usuario,
            usuario_ultima_modificacion=usuario
        )

    def perform_update(self, serializer):
        usuario = self.request.user.username if self.request.user.is_authenticated else "Sistema"
        serializer.save(usuario_ultima_modificacion=usuario)

    @action(detail=True, methods=["post"])
    def firmar(self, request, pk=None):
        planilla = self.get_object()
        serializer = FirmaSerializer(data=request.data)

        if serializer.is_valid():
            return self._procesar_firma(planilla, serializer.validated_data, request)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _procesar_firma(self, planilla, data, request):
        user = authenticate(username=data["rut"], password=data["password"])

        if not user:
            return Response(
                {"error": "Credenciales inválidas"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not self._tiene_permiso_firma(user):
            return Response(
                {"error": "No tiene permisos para esta firma"},
                status=status.HTTP_403_FORBIDDEN
            )

        firma_hash = self._generar_hash_firma(user, planilla)

        registro_firma = RegistroFirma.objects.create(
            usuario=user,
            planilla_fabricacion=planilla,
            firma_hash=firma_hash,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")
        )

        planilla.refresh_from_db()

        return Response({
            "mensaje": "Firma registrada",
            "firma_id": registro_firma.id,
            "estado_aprobacion": planilla.estado_aprobacion,
        })

    def _tiene_permiso_firma(self, user):
        try:
            rol = user.perfilusuario.rol.nombre
        except PerfilUsuario.DoesNotExist:
            return False

        return rol in {
            "JEFE_SECCION",
            "JEFE_PRODUCCION",
            "INSPECTOR_CALIDAD",
            "QUIMICO_FARMACEUTICO",
        }

    def _generar_hash_firma(self, user, planilla):
        data = f"{user.rut}{planilla.id}{datetime.datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        return x_forwarded_for.split(",")[0] if x_forwarded_for else request.META.get("REMOTE_ADDR")


# ===========================================================
# PLANILLA ENVASE
# ===========================================================
class PlanillaEnvaseViewSet(viewsets.ModelViewSet):
    queryset = PlanillaEnvase.objects.all()
    serializer_class = PlanillaEnvaseSerializer

    def perform_create(self, serializer):
        usuario = self.request.user.username if self.request.user.is_authenticated else "Sistema"
        serializer.save(
            usuario_creacion=usuario,
            usuario_ultima_modificacion=usuario
        )

    def perform_update(self, serializer):
        usuario = self.request.user.username if self.request.user.is_authenticated else "Sistema"
        serializer.save(usuario_ultima_modificacion=usuario)


# ===========================================================
# PLANILLA ENVASE PRIMARIO
# ===========================================================
class PlanillaEnvasePrimarioViewSet(viewsets.ModelViewSet):
    queryset = PlanillaEnvasePrimario.objects.all()
    serializer_class = PlanillaEnvasePrimarioSerializer

    def perform_create(self, serializer):
        usuario = self.request.user.username if self.request.user.is_authenticated else "Sistema"
        serializer.save(
            usuario_creacion=usuario,
            usuario_ultima_modificacion=usuario
        )

    def perform_update(self, serializer):
        usuario = self.request.user.username if self.request.user.is_authenticated else "Sistema"
        serializer.save(usuario_ultima_modificacion=usuario)

    @action(detail=True, methods=["post"])
    def firmar(self, request, pk=None):
        planilla = self.get_object()
        serializer = FirmaSerializer(data=request.data)

        if serializer.is_valid():
            return self._procesar_firma(planilla, serializer.validated_data, request)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _procesar_firma(self, planilla, data, request):
        user = authenticate(username=data["rut"], password=data["password"])

        if not user:
            return Response(
                {"error": "Credenciales inválidas"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not self._tiene_permiso_firma(user):
            return Response(
                {"error": "No tiene permisos para esta firma"},
                status=status.HTTP_403_FORBIDDEN
            )

        firma_hash = self._generar_hash_firma(user, planilla)

        registro_firma = RegistroFirma.objects.create(
            usuario=user,
            planilla_envase_primario=planilla,
            firma_hash=firma_hash,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")
        )

        planilla.refresh_from_db()

        return Response({
            "mensaje": "Firma registrada",
            "firma_id": registro_firma.id,
            "estado_aprobacion": planilla.estado_aprobacion
        })

    def _tiene_permiso_firma(self, user):
        try:
            rol = user.perfilusuario.rol.nombre
        except PerfilUsuario.DoesNotExist:
            return False

        return rol in {
            "JEFE_SECCION",
            "JEFE_PRODUCCION",
            "INSPECTOR_CALIDAD",
            "QUIMICO_FARMACEUTICO",
        }

    def _generar_hash_firma(self, user, planilla):
        data = f"{user.rut}{planilla.id}{datetime.datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        return x_forwarded_for.split(",")[0] if x_forwarded_for else request.META.get("REMOTE_ADDR")


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
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = PlanillaFabricacionSerializer(jarabe.planilla_fabricacion)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def envase(self, request, pk=None):
        jarabe = self.get_object()

        if not jarabe.planilla_envase:
            return Response(
                {"detalle": "No existe planilla de envase asociada."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = PlanillaEnvaseSerializer(jarabe.planilla_envase)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="envase-primario")
    def envase_primario(self, request, pk=None):
        jarabe = self.get_object()

        if not jarabe.planilla_envase_primario:
            return Response(
                {"detalle": "No existe planilla de envase primario asociada."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = PlanillaEnvasePrimarioSerializer(
            jarabe.planilla_envase_primario
        )
        return Response(serializer.data)
