from rest_framework import serializers
from .models import (
    UsuarioPersonalizado, Rol, PerfilUsuario,
    RegistroFirma, TipoProducto, Producto,
    MateriaPrima, MaterialEnvasePrimario, ControlCalidad,
    PlanillaFabricacion, PlanillaEnvase,
    PlanillaEnvasePrimario, Jarabe
)


# =====================================================
# USUARIO
# =====================================================
class UsuarioPersonalizadoSerializer(serializers.ModelSerializer):

    class Meta:
        model = UsuarioPersonalizado
        exclude = (
            "groups",
            "user_permissions",
            "last_login",
            "date_joined",
            "ultimo_acceso",
            "fecha_creacion",
        )
        extra_kwargs = {
            "password": {"write_only": True},
            "is_superuser": {"write_only": True},
            "is_staff": {"write_only": True},
            "is_active": {"write_only": True},
        }

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = UsuarioPersonalizado(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance


class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = "__all__"


class PerfilUsuarioSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(
        source="usuario.get_full_name", read_only=True
    )
    usuario_rut = serializers.CharField(
        source="usuario.rut", read_only=True
    )

    class Meta:
        model = PerfilUsuario
        fields = "__all__"


# =====================================================
# FIRMA
# =====================================================
class RegistroFirmaSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(
        source="usuario.get_full_name", read_only=True
    )
    usuario_rut = serializers.CharField(
        source="usuario.rut", read_only=True
    )

    class Meta:
        model = RegistroFirma
        exclude = ("tipo_firma",)
        read_only_fields = (
            "timestamp_firma",
            "firma_hash",
            "codigo_verificacion",
            "ip_address",
            "user_agent",
        )


class FirmaSerializer(serializers.Serializer):
    rut = serializers.CharField()
    password = serializers.CharField(style={"input_type": "password"})


# =====================================================
# PRODUCTOS
# =====================================================
class TipoProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoProducto
        fields = "__all__"


class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = "__all__"

    def validate(self, attrs):
        fecha_emision = attrs.get(
            "fecha_emision",
            getattr(self.instance, "fecha_emision",
                    None) if self.instance else None,
        )
        fecha_vencimiento = attrs.get(
            "fecha_vencimiento",
            getattr(self.instance, "fecha_vencimiento",
                    None) if self.instance else None,
        )
        if (
            fecha_emision
            and fecha_vencimiento
            and fecha_vencimiento < fecha_emision
        ):
            raise serializers.ValidationError({
                "fecha_vencimiento": "La fecha de vencimiento no puede ser anterior a la fecha de emisión."
            })
        return attrs


class MateriaPrimaSerializer(serializers.ModelSerializer):
    firma_inspector_calidad_info = RegistroFirmaSerializer(
        source="firma_inspector_calidad", read_only=True
    )

    class Meta:
        model = MateriaPrima
        fields = "__all__"
        read_only_fields = ("estado_aprobacion",)


class MaterialEnvasePrimarioSerializer(serializers.ModelSerializer):
    firma_inspector_calidad_info = RegistroFirmaSerializer(
        source="firma_inspector_calidad", read_only=True
    )

    class Meta:
        model = MaterialEnvasePrimario
        fields = "__all__"
        read_only_fields = ("estado_aprobacion", "codigo_calidad")


# =====================================================
# CONTROL CALIDAD
# =====================================================
class ControlCalidadSerializer(serializers.ModelSerializer):
    firma_control_calidad_info = RegistroFirmaSerializer(
        source="firma_control_calidad", read_only=True
    )
    inspector_nombre = serializers.CharField(
        source="inspector.get_full_name", read_only=True
    )
    inspector_rut = serializers.CharField(
        source="inspector.rut", read_only=True
    )

    class Meta:
        model = ControlCalidad
        fields = "__all__"


# =====================================================
# PLANILLA FABRICACION
# =====================================================
class PlanillaFabricacionSerializer(serializers.ModelSerializer):

    firma_jefe_seccion_info = RegistroFirmaSerializer(
        source="firma_jefe_seccion", read_only=True
    )
    firma_jefe_produccion_info = RegistroFirmaSerializer(
        source="firma_jefe_produccion", read_only=True
    )
    firma_inspector_calidad_info = RegistroFirmaSerializer(
        source="firma_inspector_calidad", read_only=True
    )
    firma_quimico_farmaceutico_info = RegistroFirmaSerializer(
        source="firma_quimico_farmaceutico", read_only=True
    )

    class Meta:
        model = PlanillaFabricacion
        fields = "__all__"
        read_only_fields = (
            "fecha_creacion",
            "fecha_primera_modificacion",
            "fecha_ultima_modificacion",
            "usuario_creacion",
            "usuario_ultima_modificacion",
            "estado_aprobacion",
        )

    def validate(self, attrs):
        fecha_emision = attrs.get(
            "fecha_emision",
            getattr(self.instance, "fecha_emision",
                    None) if self.instance else None,
        )
        fecha_vencimiento = attrs.get(
            "fecha_vencimiento",
            getattr(self.instance, "fecha_vencimiento",
                    None) if self.instance else None,
        )
        if (
            fecha_emision
            and fecha_vencimiento
            and fecha_vencimiento < fecha_emision
        ):
            raise serializers.ValidationError({
                "fecha_vencimiento": "La fecha de vencimiento no puede ser anterior a la fecha de emisión."
            })
        return attrs


# =====================================================
# PLANILLA ENVASE
# =====================================================
class PlanillaEnvaseSerializer(serializers.ModelSerializer):

    firma_jefe_seccion_info = RegistroFirmaSerializer(
        source="firma_jefe_seccion", read_only=True
    )
    firma_jefe_produccion_info = RegistroFirmaSerializer(
        source="firma_jefe_produccion", read_only=True
    )

    class Meta:
        model = PlanillaEnvase
        fields = "__all__"
        read_only_fields = (
            "fecha_creacion",
            "fecha_primera_modificacion",
            "fecha_ultima_modificacion",
            "usuario_creacion",
            "usuario_ultima_modificacion",
            "estado_aprobacion",
        )

    def validate(self, attrs):
        fecha_emision = attrs.get(
            "fecha_emision",
            getattr(self.instance, "fecha_emision",
                    None) if self.instance else None,
        )
        fecha_vencimiento = attrs.get(
            "fecha_vencimiento",
            getattr(self.instance, "fecha_vencimiento",
                    None) if self.instance else None,
        )
        if (
            fecha_emision
            and fecha_vencimiento
            and fecha_vencimiento < fecha_emision
        ):
            raise serializers.ValidationError({
                "fecha_vencimiento": "La fecha de vencimiento no puede ser anterior a la fecha de emisión."
            })
        return attrs


# =====================================================
# PLANILLA ENVASE PRIMARIO
# =====================================================
class PlanillaEnvasePrimarioSerializer(serializers.ModelSerializer):

    firma_jefe_seccion_info = RegistroFirmaSerializer(
        source="firma_jefe_seccion", read_only=True
    )
    firma_jefe_produccion_info = RegistroFirmaSerializer(
        source="firma_jefe_produccion", read_only=True
    )
    firma_inspector_calidad_info = RegistroFirmaSerializer(
        source="firma_inspector_calidad", read_only=True
    )
    firma_quimico_farmaceutico_info = RegistroFirmaSerializer(
        source="firma_quimico_farmaceutico", read_only=True
    )

    class Meta:
        model = PlanillaEnvasePrimario
        fields = "__all__"
        read_only_fields = (
            "fecha_creacion",
            "fecha_primera_modificacion",
            "fecha_ultima_modificacion",
            "usuario_creacion",
            "usuario_ultima_modificacion",
            "estado_aprobacion",
        )

    def validate(self, attrs):
        fecha_emision = attrs.get(
            "fecha_emision",
            getattr(self.instance, "fecha_emision",
                    None) if self.instance else None,
        )
        fecha_vencimiento = attrs.get(
            "fecha_vencimiento",
            getattr(self.instance, "fecha_vencimiento",
                    None) if self.instance else None,
        )
        if (
            fecha_emision
            and fecha_vencimiento
            and fecha_vencimiento < fecha_emision
        ):
            raise serializers.ValidationError({
                "fecha_vencimiento": "La fecha de vencimiento no puede ser anterior a la fecha de emisión."
            })
        return attrs


# =====================================================
# JARABE
# =====================================================
class JarabeSerializer(serializers.ModelSerializer):

    rutas = serializers.SerializerMethodField()

    class Meta:
        model = Jarabe
        fields = [
            "id",
            "producto",
            "lote",
            "fecha_inicio",
            "fecha_fin",
            "rutas",
        ]

    def _build_url(self, obj, suffix):
        request = self.context.get("request")
        path = f"/api/jarabes/{obj.id}/{suffix}/"
        return request.build_absolute_uri(path) if request else path

    def get_rutas(self, obj):
        return {
            "fabricacion": self._build_url(obj, "fabricacion"),
            "envase": self._build_url(obj, "envase"),
            "envase_primario": self._build_url(obj, "envase-primario"),
        }
