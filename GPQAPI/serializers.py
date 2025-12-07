from rest_framework import serializers
from .models import (
    UsuarioPersonalizado, PerfilUsuario,
    RegistroFirma, TipoProducto, Producto,
    MateriaPrima, MaterialEnvasePrimario, MaterialEnvaseSecundarioEmpaque,
    ControlCalidad,
    PlanillaFabricacion, PlanillaEnvase,
    PlanillaEnvasePrimario, PlanillaEnvaseSecundarioEmpaque, Jarabe,
    Bodega, StockMateriaPrima,
    StockMaterialEnvasePrimario,
    StockMaterialEnvaseSecundarioEmpaque,
)

import hashlib
import datetime


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
# PRODUCTOS (TIPO, MP, ENVASES)
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
        read_only_fields = ("estado_aprobacion", "control_calidad")


class MaterialEnvasePrimarioSerializer(serializers.ModelSerializer):
    control_calidad_info = serializers.SerializerMethodField()

    class Meta:
        model = MaterialEnvasePrimario
        fields = "__all__"
        read_only_fields = ("estado_aprobacion",
                            "codigo_calidad", "control_calidad")

    def get_control_calidad_info(self, obj):
        control = obj.controles_calidad_envase_primario.first()
        if control:
            return {
                "id": control.id,
                "codigo": control.codigo_control_calidad,
                "aprobado": control.aprobado,
                "tiene_firma": control.firma_control_calidad is not None,
                "fecha_verificacion": control.fecha_verificacion,
                "inspector": control.inspector.get_full_name() if control.inspector else None,
            }
        return None


class MaterialEnvaseSecundarioEmpaqueSerializer(serializers.ModelSerializer):
    control_calidad_info = serializers.SerializerMethodField()

    class Meta:
        model = MaterialEnvaseSecundarioEmpaque
        fields = "__all__"
        read_only_fields = ("estado_aprobacion",
                            "codigo_calidad", "control_calidad")

    def get_control_calidad_info(self, obj):
        control = obj.controles_calidad_envase_secundario.first()
        if control:
            return {
                "id": control.id,
                "codigo": control.codigo_control_calidad,
                "aprobado": control.aprobado,
                "tiene_firma": control.firma_control_calidad is not None,
                "fecha_verificacion": control.fecha_verificacion,
                "inspector": control.inspector.get_full_name() if control.inspector else None,
            }
        return None


# =====================================================
# BODEGAS Y STOCK
# =====================================================
class BodegaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bodega
        fields = "__all__"


class StockMateriaPrimaSerializer(serializers.ModelSerializer):
    materia_prima_detalle = MateriaPrimaSerializer(
        source="materia_prima", read_only=True
    )
    bodega_detalle = BodegaSerializer(source="bodega", read_only=True)

    class Meta:
        model = StockMateriaPrima
        fields = "__all__"


class StockMaterialEnvasePrimarioSerializer(serializers.ModelSerializer):
    material_detalle = MaterialEnvasePrimarioSerializer(
        source="material_envase_primario", read_only=True
    )
    bodega_detalle = BodegaSerializer(source="bodega", read_only=True)

    class Meta:
        model = StockMaterialEnvasePrimario
        fields = "__all__"


class StockMaterialEnvaseSecundarioEmpaqueSerializer(serializers.ModelSerializer):
    material_detalle = MaterialEnvaseSecundarioEmpaqueSerializer(
        source="material_envase_secundario_empaque", read_only=True
    )
    bodega_detalle = BodegaSerializer(source="bodega", read_only=True)

    class Meta:
        model = StockMaterialEnvaseSecundarioEmpaque
        fields = "__all__"


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

    material_envase_primario_info = MaterialEnvasePrimarioSerializer(
        source="material_envase_primario", read_only=True
    )
    material_envase_secundario_info = MaterialEnvaseSecundarioEmpaqueSerializer(
        source="material_envase_secundario_empaque", read_only=True
    )

    class Meta:
        model = ControlCalidad
        fields = "__all__"
        read_only_fields = (
            "codigo_control_calidad",
            "firma_control_calidad",
        )

    def _generar_hash_firma(self, user, control_calidad):
        data = f"{user.rut}{control_calidad.id}{datetime.datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()

    def _get_client_ip(self, request):
        if not request:
            return None
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        return x_forwarded_for.split(",")[0] if x_forwarded_for else request.META.get("REMOTE_ADDR")

    def update(self, instance, validated_data):
        print(f"DEBUG serializer: Actualizando control calidad {instance.id}")
        print(f"DEBUG serializer: validated_data: {validated_data}")

        aprobado_antes = instance.aprobado
        print(f"DEBUG serializer: aprobado antes: {aprobado_antes}")

        instance = super().update(instance, validated_data)
        print(f"DEBUG serializer: aprobado después: {instance.aprobado}")

        request = self.context.get("request")
        user = getattr(request, "user", None)
        print(f"DEBUG serializer: usuario autenticado: {user}")

        if (
            instance.aprobado
            and not aprobado_antes
            and instance.firma_control_calidad is None
            and user is not None
            and user.is_authenticated
        ):
            print(
                f"DEBUG serializer: Generando firma automática para control {instance.id}"
            )
            firma_hash = self._generar_hash_firma(user, instance)

            registro_firma = RegistroFirma.objects.create(
                usuario=user,
                firma_hash=firma_hash,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get(
                    "HTTP_USER_AGENT", "") if request else "",
            )

            instance.firma_control_calidad = registro_firma
            instance.save(update_fields=["firma_control_calidad"])
            print(
                f"DEBUG serializer: Firma {registro_firma.id} asignada a control calidad"
            )

            if instance.materia_prima:
                mp = instance.materia_prima
                mp.firma_inspector_calidad = registro_firma
                mp.actualizar_estado_aprobacion()
                print(f"DEBUG serializer: Materia prima {mp.id} actualizada")

            if instance.material_envase_primario:
                mep = instance.material_envase_primario
                mep.actualizar_estado_aprobacion(instance)
                print(
                    f"DEBUG serializer: Material envase primario {mep.id} actualizado"
                )

            if instance.material_envase_secundario_empaque:
                mes = instance.material_envase_secundario_empaque
                mes.actualizar_estado_aprobacion(instance)
                print(
                    f"DEBUG serializer: Material envase secundario {mes.id} actualizado"
                )
        else:
            print(f"DEBUG serializer: No se generó firma automática")
            print(
                f"DEBUG serializer: Condiciones: aprobado={instance.aprobado}, aprobado_antes={aprobado_antes}, firma_existe={instance.firma_control_calidad is not None}"
            )

        return instance


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
    firma_quimico_farmaceutico_info = RegistroFirmaSerializer(
        source="firma_quimico_farmaceutico", read_only=True
    )

    # control de calidad automático
    control_calidad = serializers.PrimaryKeyRelatedField(read_only=True)
    codigo_control_calidad = serializers.CharField(
        source="control_calidad.codigo_control_calidad", read_only=True
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
        # Validación fechas
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

        # validación de cantidad_entregada y stock
        tipo_mov = attrs.get(
            "tipo_movimiento",
            getattr(self.instance, "tipo_movimiento", "PRODUCCION")
            if self.instance else "PRODUCCION",
        )
        cantidad_entregada = attrs.get(
            "cantidad_entregada",
            getattr(self.instance, "cantidad_entregada", 0)
            if self.instance else 0,
        )

        if cantidad_entregada is not None and cantidad_entregada < 0:
            raise serializers.ValidationError({
                "cantidad_entregada": "La cantidad entregada no puede ser negativa."
            })

        if tipo_mov == "PEDIDO_BODEGA":
            materia = attrs.get(
                "materia_prima",
                getattr(self.instance, "materia_prima", None)
                if self.instance else None,
            )
            if not materia:
                raise serializers.ValidationError({
                    "materia_prima": "Debe seleccionar una materia prima para el pedido a bodega."
                })

            if cantidad_entregada is None or cantidad_entregada <= 0:
                raise serializers.ValidationError({
                    "cantidad_entregada": "En un pedido a bodega la cantidad entregada debe ser mayor a cero."
                })

            # Buscar stock disponible en la bodega de materias primas
            bodega_mp = Bodega.objects.filter(
                nombre="Bodega Materias Primas"
            ).first()
            stock_disponible = 0
            if bodega_mp:
                stock_obj = StockMateriaPrima.objects.filter(
                    bodega=bodega_mp,
                    materia_prima=materia
                ).first()
                if stock_obj:
                    stock_disponible = stock_obj.cantidad_disponible

            if cantidad_entregada > stock_disponible:
                raise serializers.ValidationError({
                    "cantidad_entregada": f"No hay stock suficiente de la materia prima en bodega. Stock disponible: {stock_disponible}."
                })

        return attrs

    def create(self, validated_data):
        materia = validated_data.get("materia_prima")
        if not materia:
            raise serializers.ValidationError({
                "materia_prima": "Debe seleccionar una materia prima."
            })

        cc = ControlCalidad.objects.filter(
            materia_prima=materia,
            aprobado=True,
        ).order_by("-fecha_verificacion", "-id").first()

        if not cc:
            raise serializers.ValidationError({
                "control_calidad": "No existe un control de calidad aprobado para esta materia prima."
            })

        validated_data["control_calidad"] = cc
        return super().create(validated_data)

    def update(self, instance, validated_data):
        materia = validated_data.get("materia_prima", instance.materia_prima)

        if materia != instance.materia_prima:
            cc = ControlCalidad.objects.filter(
                materia_prima=materia,
                aprobado=True,
            ).order_by("-fecha_verificacion", "-id").first()

            if not cc:
                raise serializers.ValidationError({
                    "control_calidad": "No existe un control de calidad aprobado para esta materia prima."
                })

            validated_data["control_calidad"] = cc

        return super().update(instance, validated_data)


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
    firma_quimico_farmaceutico_info = RegistroFirmaSerializer(
        source="firma_quimico_farmaceutico", read_only=True
    )

    # control de calidad automático
    control_calidad = serializers.PrimaryKeyRelatedField(read_only=True)
    codigo_control_calidad = serializers.CharField(
        source="control_calidad.codigo_control_calidad", read_only=True
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
        # Validación fechas
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

        # validación de cantidad_entregada y stock
        tipo_mov = attrs.get(
            "tipo_movimiento",
            getattr(self.instance, "tipo_movimiento", "PRODUCCION")
            if self.instance else "PRODUCCION",
        )
        cantidad_entregada = attrs.get(
            "cantidad_entregada",
            getattr(self.instance, "cantidad_entregada", 0)
            if self.instance else 0,
        )

        if cantidad_entregada is not None and cantidad_entregada < 0:
            raise serializers.ValidationError({
                "cantidad_entregada": "La cantidad entregada no puede ser negativa."
            })

        if tipo_mov == "PEDIDO_BODEGA":
            material = attrs.get(
                "material_envase_primario",
                getattr(self.instance, "material_envase_primario", None)
                if self.instance else None,
            )
            if not material:
                raise serializers.ValidationError({
                    "material_envase_primario": "Debe seleccionar un material de envase primario para el pedido a bodega."
                })

            if cantidad_entregada is None or cantidad_entregada <= 0:
                raise serializers.ValidationError({
                    "cantidad_entregada": "En un pedido a bodega la cantidad entregada debe ser mayor a cero."
                })

            # Buscar stock disponible en la bodega de envase primario
            bodega_ep = Bodega.objects.filter(
                nombre="Bodega Envase Primario"
            ).first()
            stock_disponible = 0
            if bodega_ep:
                stock_obj = StockMaterialEnvasePrimario.objects.filter(
                    bodega=bodega_ep,
                    material_envase_primario=material
                ).first()
                if stock_obj:
                    stock_disponible = stock_obj.cantidad_disponible

            if cantidad_entregada > stock_disponible:
                raise serializers.ValidationError({
                    "cantidad_entregada": f"No hay stock suficiente del material de envase primario en bodega. Stock disponible: {stock_disponible}."
                })

        return attrs

    def create(self, validated_data):
        material = validated_data.get("material_envase_primario")
        if not material:
            raise serializers.ValidationError({
                "material_envase_primario": "Debe seleccionar un material de envase primario."
            })

        cc = ControlCalidad.objects.filter(
            material_envase_primario=material,
            aprobado=True,
        ).order_by("-fecha_verificacion", "-id").first()

        if not cc:
            raise serializers.ValidationError({
                "control_calidad": "No existe un control de calidad aprobado para este material de envase primario."
            })

        validated_data["control_calidad"] = cc
        return super().create(validated_data)

    def update(self, instance, validated_data):
        material = validated_data.get(
            "material_envase_primario", instance.material_envase_primario
        )

        if material != instance.material_envase_primario:
            cc = ControlCalidad.objects.filter(
                material_envase_primario=material,
                aprobado=True,
            ).order_by("-fecha_verificacion", "-id").first()

            if not cc:
                raise serializers.ValidationError({
                    "control_calidad": "No existe un control de calidad aprobado para este material de envase primario."
                })

            validated_data["control_calidad"] = cc

        return super().update(instance, validated_data)


# =====================================================
# PLANILLA ENVASE SECUNDARIO Y EMPAQUE
# =====================================================
class PlanillaEnvaseSecundarioEmpaqueSerializer(serializers.ModelSerializer):

    firma_jefe_seccion_info = RegistroFirmaSerializer(
        source="firma_jefe_seccion", read_only=True
    )
    firma_jefe_produccion_info = RegistroFirmaSerializer(
        source="firma_jefe_produccion", read_only=True
    )
    firma_quimico_farmaceutico_info = RegistroFirmaSerializer(
        source="firma_quimico_farmaceutico", read_only=True
    )

    control_calidad = serializers.PrimaryKeyRelatedField(read_only=True)
    codigo_control_calidad = serializers.CharField(
        source="control_calidad.codigo_control_calidad", read_only=True
    )

    class Meta:
        model = PlanillaEnvaseSecundarioEmpaque
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
        # Validación fechas
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

        # validación de cantidad_entregada y stock
        tipo_mov = attrs.get(
            "tipo_movimiento",
            getattr(self.instance, "tipo_movimiento", "PRODUCCION")
            if self.instance else "PRODUCCION",
        )
        cantidad_entregada = attrs.get(
            "cantidad_entregada",
            getattr(self.instance, "cantidad_entregada", 0)
            if self.instance else 0,
        )

        if cantidad_entregada is not None and cantidad_entregada < 0:
            raise serializers.ValidationError({
                "cantidad_entregada": "La cantidad entregada no puede ser negativa."
            })

        if tipo_mov == "PEDIDO_BODEGA":
            material = attrs.get(
                "material_envase_secundario_empaque",
                getattr(self.instance, "material_envase_secundario_empaque", None)
                if self.instance else None,
            )
            if not material:
                raise serializers.ValidationError({
                    "material_envase_secundario_empaque": "Debe seleccionar un material de envase secundario/empaque para el pedido a bodega."
                })

            if cantidad_entregada is None or cantidad_entregada <= 0:
                raise serializers.ValidationError({
                    "cantidad_entregada": "En un pedido a bodega la cantidad entregada debe ser mayor a cero."
                })

            # Buscar stock disponible en la bodega de envase secundario
            bodega_es = Bodega.objects.filter(
                nombre="Bodega Envase Secundario"
            ).first()
            stock_disponible = 0
            if bodega_es:
                stock_obj = StockMaterialEnvaseSecundarioEmpaque.objects.filter(
                    bodega=bodega_es,
                    material_envase_secundario_empaque=material
                ).first()
                if stock_obj:
                    stock_disponible = stock_obj.cantidad_disponible

            if cantidad_entregada > stock_disponible:
                raise serializers.ValidationError({
                    "cantidad_entregada": f"No hay stock suficiente del material de envase secundario/empaque en bodega. Stock disponible: {stock_disponible}."
                })

        return attrs

    def create(self, validated_data):
        material = validated_data.get("material_envase_secundario_empaque")
        if not material:
            raise serializers.ValidationError({
                "material_envase_secundario_empaque": "Debe seleccionar un material de envase secundario/empaque."
            })

        cc = ControlCalidad.objects.filter(
            material_envase_secundario_empaque=material,
            aprobado=True,
        ).order_by("-fecha_verificacion", "-id").first()

        if not cc:
            raise serializers.ValidationError({
                "control_calidad": "No existe un control de calidad aprobado para este material de envase secundario/empaque."
            })

        validated_data["control_calidad"] = cc
        return super().create(validated_data)

    def update(self, instance, validated_data):
        material = validated_data.get(
            "material_envase_secundario_empaque",
            instance.material_envase_secundario_empaque
        )

        if material != instance.material_envase_secundario_empaque:
            cc = ControlCalidad.objects.filter(
                material_envase_secundario_empaque=material,
                aprobado=True,
            ).order_by("-fecha_verificacion", "-id").first()

            if not cc:
                raise serializers.ValidationError({
                    "control_calidad": "No existe un control de calidad aprobado para este material de envase secundario/empaque."
                })

            validated_data["control_calidad"] = cc

        return super().update(instance, validated_data)


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
