from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
import random
import string


# =======================================================
# USUARIO PERSONALIZADO
# =======================================================
class UsuarioPersonalizado(AbstractUser):
    rut = models.CharField(max_length=12, unique=True)
    telefono = models.CharField(max_length=15, blank=True)
    firma_digital = models.TextField(blank=True)

    activo = models.BooleanField(default=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    ultimo_acceso = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.get_full_name()} - {self.rut}"


# =======================================================
# ROLES
# =======================================================
class Rol(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True)
    permisos = models.JSONField(default=list)

    def __str__(self):
        return self.nombre


# =======================================================
# PERFIL USUARIO
# =======================================================
class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(
        UsuarioPersonalizado, on_delete=models.CASCADE
    )
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE)
    departamento = models.CharField(max_length=100, blank=True)
    cargo = models.CharField(max_length=100, blank=True)
    numero_licencia = models.CharField(max_length=50, blank=True)

    contacto_emergencia_nombre = models.CharField(max_length=100, blank=True)
    contacto_emergencia_telefono = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return f"{self.usuario.get_full_name()} - {self.rol.nombre}"


# =======================================================
# FIRMA DIGITAL
# =======================================================
class RegistroFirma(models.Model):

    usuario = models.ForeignKey(UsuarioPersonalizado, on_delete=models.CASCADE)

    # Firmas asociadas a procesos
    planilla_fabricacion = models.ForeignKey(
        "PlanillaFabricacion", null=True, blank=True, on_delete=models.CASCADE
    )
    planilla_envase_primario = models.ForeignKey(
        "PlanillaEnvasePrimario", null=True, blank=True, on_delete=models.CASCADE
    )

    tipo_firma = models.CharField(max_length=40)
    firma_hash = models.CharField(max_length=255)
    timestamp_firma = models.DateTimeField(auto_now_add=True)

    codigo_verificacion = models.CharField(max_length=6, blank=True)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)

    MAPA_FIRMA = {
        "JEFE_SECCION": "JEFE_SECCION",
        "JEFE_DE_SECCION": "JEFE_SECCION",
        "JEFE SECCION": "JEFE_SECCION",
        "JEFE SECCIÓN": "JEFE_SECCION",

        "JEFE_PRODUCCION": "JEFE_PRODUCCION",
        "JEFE_DE_PRODUCCION": "JEFE_PRODUCCION",
        "JEFE PRODUCCION": "JEFE_PRODUCCION",
        "JEFE PRODUCCIÓN": "JEFE_PRODUCCION",

        "INSPECTOR_CALIDAD": "INSPECTOR_CALIDAD",
        "INSPECTOR_DE_CALIDAD": "INSPECTOR_CALIDAD",
        "INSPECTOR CALIDAD": "INSPECTOR_CALIDAD",
        "INPESCTOR_CALIDAD": "INSPECTOR_CALIDAD",
        "INPESCTOR CALIDAD": "INSPECTOR_CALIDAD",

        "QUIMICO_FARMACEUTICO": "QUIMICO_FARMACEUTICO",
        "QUIMICO_FARMACÉUTICO": "QUIMICO_FARMACEUTICO",
        "QUIMICO FARMACEUTICO": "QUIMICO_FARMACEUTICO",
        "QUIMICO FARMACÉUTICO": "QUIMICO_FARMACEUTICO",
        "QUIMICO": "QUIMICO_FARMACEUTICO",

        "CONTROL_CALIDAD": "INSPECTOR_CALIDAD",
        "CONTROL DE CALIDAD": "INSPECTOR_CALIDAD",
        "CONTROL CALIDAD": "INSPECTOR_CALIDAD",
    }

    def save(self, *args, **kwargs):
        es_nueva = self.pk is None

        # 1) Detectar tipo_firma según rol del usuario
        try:
            rol = self.usuario.perfilusuario.rol.nombre.strip().upper()
        except Exception:
            # si no tiene perfil, usamos lo que ya venga en tipo_firma
            rol = self.tipo_firma or ""

        normalizado = (
            rol.replace(" ", "_")
               .replace("Á", "A")
               .replace("É", "E")
               .replace("Í", "I")
               .replace("Ó", "O")
               .replace("Ú", "U")
               .replace("Ñ", "N")
        )

        tipo_detectado = self.MAPA_FIRMA.get(normalizado) or \
            self.MAPA_FIRMA.get(rol.replace("_", " "))

        self.tipo_firma = tipo_detectado or rol

        # 2) Código verificación
        if not self.codigo_verificacion:
            self.codigo_verificacion = ''.join(
                random.choices(string.digits, k=6)
            )

        super().save(*args, **kwargs)

        # 3) Acciones automáticas solo en nueva firma
        if not es_nueva:
            return

        # PLANILLA FABRICACIÓN
        if self.planilla_fabricacion:
            pf = self.planilla_fabricacion
            asignacion = {
                "JEFE_SECCION": "firma_jefe_seccion",
                "JEFE_PRODUCCION": "firma_jefe_produccion",
                "INSPECTOR_CALIDAD": "firma_inspector_calidad",
                "QUIMICO_FARMACEUTICO": "firma_quimico_farmaceutico",
            }
            campo = asignacion.get(self.tipo_firma)
            if campo:
                setattr(pf, campo, self)
                pf.save(update_fields=[campo])
                pf.actualizar_estado_aprobacion()

        # PLANILLA ENVASE PRIMARIO
        if self.planilla_envase_primario:
            pep = self.planilla_envase_primario
            asignacion2 = {
                "JEFE_SECCION": "firma_jefe_seccion",
                "JEFE_PRODUCCION": "firma_jefe_produccion",
                "INSPECTOR_CALIDAD": "firma_inspector_calidad",
                "QUIMICO_FARMACEUTICO": "firma_quimico_farmaceutico",
            }
            campo = asignacion2.get(self.tipo_firma)
            if campo:
                setattr(pep, campo, self)
                pep.save(update_fields=[campo])
                pep.actualizar_estado_aprobacion()

    def __str__(self):
        return f"{self.usuario.rut} - {self.tipo_firma}"


# =======================================================
# AUDITORÍA
# =======================================================
class ModeloAuditoria(models.Model):
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    usuario_creacion = models.CharField(max_length=100, blank=True)

    fecha_primera_modificacion = models.DateTimeField(null=True, blank=True)
    fecha_ultima_modificacion = models.DateTimeField(auto_now=True)
    usuario_ultima_modificacion = models.CharField(max_length=100, blank=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.fecha_primera_modificacion:
            self.fecha_primera_modificacion = timezone.now()
        super().save(*args, **kwargs)


# =======================================================
# PRODUCTO – MATERIA PRIMA – ETC.
# =======================================================
class TipoProducto(models.Model):
    nombre = models.CharField(max_length=255, unique=True)
    descripcion = models.TextField()

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    nombre = models.CharField(max_length=255)
    cantidad_teorica = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_real = models.DecimalField(max_digits=10, decimal_places=2)
    rendimiento = models.DecimalField(max_digits=5, decimal_places=2)
    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField()

    def clean(self):
        if (
            self.fecha_emision
            and self.fecha_vencimiento
            and self.fecha_vencimiento < self.fecha_emision
        ):
            raise ValidationError({
                "fecha_vencimiento": "La fecha de vencimiento no puede ser anterior a la fecha de emisión."
            })

    def __str__(self):
        return self.nombre


class MateriaPrima(models.Model):
    ESTADOS_APROBACION = [
        ("PENDIENTE", "Pendiente"),
        ("APROBADO", "Aprobado"),
    ]

    nombre = models.CharField(max_length=255)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    batch = models.CharField(max_length=100)
    control_calidad = models.BooleanField(default=False)

    firma_inspector_calidad = models.ForeignKey(
        "RegistroFirma", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="firmas_materia_prima"
    )

    estado_aprobacion = models.CharField(
        max_length=20, choices=ESTADOS_APROBACION, default="PENDIENTE"
    )

    def actualizar_estado_aprobacion(self):
        if self.firma_inspector_calidad:
            self.estado_aprobacion = "APROBADO"
            self.control_calidad = True
        else:
            self.estado_aprobacion = "PENDIENTE"
            self.control_calidad = False

        super().save(update_fields=["estado_aprobacion", "control_calidad"])

    def __str__(self):
        return f"{self.nombre} - {self.batch}"


# =======================================================
# MATERIAL ENVASE PRIMARIO
# =======================================================
class MaterialEnvasePrimario(models.Model):
    ESTADOS_APROBACION = [
        ("PENDIENTE", "Pendiente"),
        ("APROBADO", "Aprobado"),
    ]

    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=255)
    tipo_envase = models.CharField(max_length=100)

    # código de calidad automático
    codigo_calidad = models.CharField(
        max_length=50, unique=True, blank=True
    )

    control_calidad = models.BooleanField(default=False)

    firma_inspector_calidad = models.ForeignKey(
        "RegistroFirma", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="firmas_material_envase_primario"
    )

    estado_aprobacion = models.CharField(
        max_length=20, choices=ESTADOS_APROBACION, default="PENDIENTE"
    )

    def save(self, *args, **kwargs):
        if not self.codigo_calidad:
            last = MaterialEnvasePrimario.objects.order_by("-id").first()
            next_num = 1
            if last and last.codigo_calidad:
                try:
                    next_num = int(last.codigo_calidad.split("-")[-1]) + 1
                except Exception:
                    next_num = 1
            self.codigo_calidad = f"MEP-{next_num:04d}"
        super().save(*args, **kwargs)

    def actualizar_estado_aprobacion(self):
        if self.firma_inspector_calidad:
            self.estado_aprobacion = "APROBADO"
            self.control_calidad = True
        else:
            self.estado_aprobacion = "PENDIENTE"
            self.control_calidad = False

        super().save(update_fields=["estado_aprobacion", "control_calidad"])

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


# =======================================================
# CONTROL CALIDAD
# =======================================================
class ControlCalidad(models.Model):
    codigo_control_calidad = models.CharField(
        max_length=50, unique=True, blank=True
    )

    resultado = models.CharField(max_length=255)
    fecha_verificacion = models.DateField()
    aprobado = models.BooleanField(default=False)

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)

    # Materia prima asociada al control
    materia_prima = models.ForeignKey(
        MateriaPrima, null=True, blank=True,
        on_delete=models.CASCADE, related_name="controles_calidad"
    )

    # Material de envase primario asociado al control
    material_envase_primario = models.ForeignKey(
        MaterialEnvasePrimario, null=True, blank=True,
        on_delete=models.CASCADE, related_name="controles_calidad_envase_primario"
    )

    # Inspector asignado obligatoriamente
    inspector = models.ForeignKey(
        UsuarioPersonalizado,
        on_delete=models.PROTECT,
        related_name="controles_a_firmar"
    )

    # Firma registrada cuando el inspector firma el control
    firma_control_calidad = models.ForeignKey(
        "RegistroFirma", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="firmas_cc"
    )

    def save(self, *args, **kwargs):
        if not self.codigo_control_calidad:
            last = ControlCalidad.objects.order_by("-id").first()
            next_num = 1
            if last and last.codigo_control_calidad:
                try:
                    next_num = int(
                        last.codigo_control_calidad.split("-")[-1]
                    ) + 1
                except Exception:
                    next_num = 1

            self.codigo_control_calidad = f"CC-{next_num:04d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return self.codigo_control_calidad


# =======================================================
# PLANILLA FABRICACIÓN
# =======================================================
class PlanillaFabricacion(ModeloAuditoria):
    ESTADOS_APROBACION = [
        ("EN_PROCESO", "En proceso"),
        ("APROBADO", "Aprobado"),
    ]

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    tipo_producto = models.ForeignKey(TipoProducto, on_delete=models.CASCADE)

    serie = models.CharField(max_length=50)
    numero_planilla = models.CharField(max_length=50)

    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField()

    control_calidad = models.ForeignKey(
        ControlCalidad, on_delete=models.CASCADE,
        related_name="planillas_fabricacion"
    )

    rendimiento_teorico = models.DecimalField(max_digits=10, decimal_places=2)
    periodo_eficacia = models.IntegerField()
    cantidad_estuches = models.DecimalField(max_digits=10, decimal_places=2)

    materia_prima = models.ForeignKey(MateriaPrima, on_delete=models.CASCADE)

    firma_jefe_seccion = models.ForeignKey(
        "RegistroFirma", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="firma_js_fabricacion"
    )
    firma_jefe_produccion = models.ForeignKey(
        "RegistroFirma", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="firma_jp_fabricacion"
    )
    firma_inspector_calidad = models.ForeignKey(
        "RegistroFirma", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="firma_ic_fabricacion"
    )
    firma_quimico_farmaceutico = models.ForeignKey(
        "RegistroFirma", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="firma_qf_fabricacion"
    )

    sala_pesaje = models.CharField(max_length=100, blank=True)
    balanza_numero = models.CharField(max_length=100, blank=True)
    liberacion_area = models.BooleanField(default=False)
    etiqueta_limpieza = models.BooleanField(default=False)

    estado_aprobacion = models.CharField(
        max_length=20, choices=ESTADOS_APROBACION, default="EN_PROCESO"
    )

    def clean(self):
        if (
            self.fecha_emision
            and self.fecha_vencimiento
            and self.fecha_vencimiento < self.fecha_emision
        ):
            raise ValidationError({
                "fecha_vencimiento": "La fecha de vencimiento no puede ser anterior a la fecha de emisión."
            })

    def actualizar_estado_aprobacion(self):
        firmas = [
            self.firma_jefe_seccion,
            self.firma_jefe_produccion,
            self.firma_inspector_calidad,
            self.firma_quimico_farmaceutico,
        ]
        self.estado_aprobacion = "APROBADO" if all(firmas) else "EN_PROCESO"
        super().save(update_fields=["estado_aprobacion"])

    def __str__(self):
        return f"{self.serie}-{self.numero_planilla}"


# =======================================================
# PLANILLA ENVASE
# =======================================================
class PlanillaEnvase(ModeloAuditoria):
    ESTADOS_APROBACION = [
        ("EN_PROCESO", "En proceso"),
        ("APROBADO", "Aprobado"),
    ]

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    tipo_producto = models.ForeignKey(TipoProducto, on_delete=models.CASCADE)

    cantidad_teorica = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_real = models.DecimalField(max_digits=10, decimal_places=2)
    rendimiento = models.DecimalField(max_digits=5, decimal_places=2)

    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField()

    firma_jefe_seccion = models.ForeignKey(
        "RegistroFirma", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="firma_js_envase"
    )
    firma_jefe_produccion = models.ForeignKey(
        "RegistroFirma", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="firma_jp_envase"
    )

    estado_aprobacion = models.CharField(
        max_length=20, choices=ESTADOS_APROBACION, default="EN_PROCESO"
    )

    def clean(self):
        if (
            self.fecha_emision
            and self.fecha_vencimiento
            and self.fecha_vencimiento < self.fecha_emision
        ):
            raise ValidationError({
                "fecha_vencimiento": "La fecha de vencimiento no puede ser anterior a la fecha de emisión."
            })

    def actualizar_estado_aprobacion(self):
        firmas = [
            self.firma_jefe_seccion,
            self.firma_jefe_produccion,
        ]
        self.estado_aprobacion = "APROBADO" if all(firmas) else "EN_PROCESO"
        super().save(update_fields=["estado_aprobacion"])

    def __str__(self):
        return f"Envase {self.producto.nombre}"


# =======================================================
# PLANILLA ENVASE PRIMARIO
# =======================================================
class PlanillaEnvasePrimario(ModeloAuditoria):
    ESTADOS_APROBACION = [
        ("EN_PROCESO", "En proceso"),
        ("APROBADO", "Aprobado"),
    ]

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    tipo_producto = models.ForeignKey(TipoProducto, on_delete=models.CASCADE)

    serie = models.CharField(max_length=50)
    numero_planilla = models.CharField(max_length=50)

    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField()

    control_calidad = models.ForeignKey(
        ControlCalidad, on_delete=models.CASCADE
    )

    rendimiento_teorico = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_estuches = models.DecimalField(max_digits=10, decimal_places=2)
    periodo_eficacia = models.IntegerField()

    sala_pesaje = models.CharField(max_length=100, blank=True)
    balanza_numero = models.CharField(max_length=100, blank=True)

    material_envase_primario = models.ForeignKey(
        MaterialEnvasePrimario, on_delete=models.CASCADE
    )

    firma_jefe_seccion = models.ForeignKey(
        "RegistroFirma", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="firma_js_envase_primario"
    )
    firma_jefe_produccion = models.ForeignKey(
        "RegistroFirma", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="firma_jp_envase_primario"
    )
    firma_inspector_calidad = models.ForeignKey(
        "RegistroFirma", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="firma_ic_envase_primario"
    )
    firma_quimico_farmaceutico = models.ForeignKey(
        "RegistroFirma", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="firma_qf_envase_primario"
    )

    estado_aprobacion = models.CharField(
        max_length=20, choices=ESTADOS_APROBACION, default="EN_PROCESO"
    )

    def clean(self):
        if (
            self.fecha_emision
            and self.fecha_vencimiento
            and self.fecha_vencimiento < self.fecha_emision
        ):
            raise ValidationError({
                "fecha_vencimiento": "La fecha de vencimiento no puede ser anterior a la fecha de emisión."
            })

    def actualizar_estado_aprobacion(self):
        firmas = [
            self.firma_jefe_seccion,
            self.firma_jefe_produccion,
            self.firma_inspector_calidad,
            self.firma_quimico_farmaceutico,
        ]
        self.estado_aprobacion = "APROBADO" if all(firmas) else "EN_PROCESO"
        super().save(update_fields=["estado_aprobacion"])

    def __str__(self):
        return f"EnvPrim {self.serie}-{self.numero_planilla}"


# =======================================================
# JARABE
# =======================================================
class Jarabe(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    lote = models.CharField(max_length=50)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)

    planilla_fabricacion = models.OneToOneField(
        PlanillaFabricacion, null=True, blank=True, on_delete=models.SET_NULL
    )
    planilla_envase = models.OneToOneField(
        PlanillaEnvase, null=True, blank=True, on_delete=models.SET_NULL
    )
    planilla_envase_primario = models.OneToOneField(
        PlanillaEnvasePrimario, null=True, blank=True, on_delete=models.SET_NULL
    )

    def __str__(self):
        return f"Jarabe {self.producto.nombre} | Lote {self.lote}"
