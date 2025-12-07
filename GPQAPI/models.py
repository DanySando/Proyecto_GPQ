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
# PERFIL USUARIO (ROL COMO CHARFIELD)
# =======================================================
class PerfilUsuario(models.Model):
    ROL_CHOICES = [
        ("JEFE_SECCION", "Jefe de Sección"),
        ("JEFE_PRODUCCION", "Jefe de Producción"),
        ("INSPECTOR_CALIDAD", "Inspector de Calidad"),
        ("QUIMICO_FARMACEUTICO", "Químico Farmacéutico"),
    ]

    usuario = models.OneToOneField(
        UsuarioPersonalizado, on_delete=models.CASCADE
    )
    rol = models.CharField(max_length=30, choices=ROL_CHOICES)

    departamento = models.CharField(max_length=100, blank=True)
    numero_licencia = models.CharField(max_length=50, blank=True)

    contacto_emergencia_nombre = models.CharField(max_length=100, blank=True)
    contacto_emergencia_telefono = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return f"{self.usuario.get_full_name()} - {self.get_rol_display()}"


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
    planilla_envase_secundario_empaque = models.ForeignKey(
        "PlanillaEnvaseSecundarioEmpaque",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
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

        # 1) Detectar tipo_firma según rol del usuario (rol como CharField)
        try:
            rol = self.usuario.perfilusuario.rol.strip().upper()
        except Exception:
            rol = (self.tipo_firma or "").strip().upper()

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
        if es_nueva:
            print(
                f"DEBUG: Nueva firma creada, tipo: {self.tipo_firma}, id: {self.id}"
            )

            # PLANILLA FABRICACIÓN
            if self.planilla_fabricacion:
                pf = self.planilla_fabricacion
                print(f"DEBUG: Asociando firma a planilla fabricación {pf.id}")
                asignacion = {
                    "JEFE_SECCION": "firma_jefe_seccion",
                    "JEFE_PRODUCCION": "firma_jefe_produccion",
                    "QUIMICO_FARMACEUTICO": "firma_quimico_farmaceutico",
                }
                campo = asignacion.get(self.tipo_firma)
                if campo:
                    setattr(pf, campo, self)
                    pf.save(update_fields=[campo])
                    pf.actualizar_estado_aprobacion()
                    print(
                        f"DEBUG: Firma asignada a {campo} en planilla fabricación"
                    )

            # PLANILLA ENVASE PRIMARIO
            if self.planilla_envase_primario:
                pep = self.planilla_envase_primario
                print(
                    f"DEBUG: Asociando firma a planilla envase primario {pep.id}"
                )
                asignacion2 = {
                    "JEFE_SECCION": "firma_jefe_seccion",
                    "JEFE_PRODUCCION": "firma_jefe_produccion",
                    "QUIMICO_FARMACEUTICO": "firma_quimico_farmaceutico",
                }
                campo = asignacion2.get(self.tipo_firma)
                if campo:
                    setattr(pep, campo, self)
                    pep.save(update_fields=[campo])
                    pep.actualizar_estado_aprobacion()
                    print(
                        f"DEBUG: Firma asignada a {campo} en planilla envase primario"
                    )

            # PLANILLA ENVASE SECUNDARIO Y EMPAQUE
            if self.planilla_envase_secundario_empaque:
                pes = self.planilla_envase_secundario_empaque
                print(
                    f"DEBUG: Asociando firma a planilla envase secundario/empaque {pes.id}"
                )
                asignacion3 = {
                    "JEFE_SECCION": "firma_jefe_seccion",
                    "JEFE_PRODUCCION": "firma_jefe_produccion",
                    "QUIMICO_FARMACEUTICO": "firma_quimico_farmaceutico",
                }
                campo = asignacion3.get(self.tipo_firma)
                if campo:
                    setattr(pes, campo, self)
                    pes.save(update_fields=[campo])
                    pes.actualizar_estado_aprobacion()
                    print(
                        f"DEBUG: Firma asignada a {campo} en planilla envase secundario/empaque"
                    )

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
        print(f"DEBUG: Actualizando estado de materia prima {self.id}")
        print(f"DEBUG: Firma inspector: {self.firma_inspector_calidad}")

        if self.firma_inspector_calidad:
            self.estado_aprobacion = "APROBADO"
            self.control_calidad = True
            print(f"DEBUG: Materia prima {self.id} APROBADA")
        else:
            self.estado_aprobacion = "PENDIENTE"
            self.control_calidad = False
            print(f"DEBUG: Materia prima {self.id} PENDIENTE")

        self.save()
        print(
            f"DEBUG: Materia prima {self.id} guardada, estado: {self.estado_aprobacion}"
        )

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

    codigo_calidad = models.CharField(
        max_length=50, unique=True, blank=True
    )

    control_calidad = models.BooleanField(default=False)

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

    def actualizar_estado_aprobacion(self, control_calidad):
        print(
            f"DEBUG: Actualizando estado de material envase primario {self.id}"
        )
        print(
            f"DEBUG: Control calidad asociado: {control_calidad.id if control_calidad else 'None'}"
        )
        print(
            f"DEBUG: Control calidad aprobado: {control_calidad.aprobado if control_calidad else 'False'}"
        )
        print(
            f"DEBUG: Control calidad tiene firma: {control_calidad.firma_control_calidad if control_calidad else 'False'}"
        )

        tiene_firma = (
            control_calidad and
            control_calidad.aprobado and
            control_calidad.firma_control_calidad is not None
        )

        if tiene_firma:
            self.estado_aprobacion = "APROBADO"
            self.control_calidad = True
            print(
                f"DEBUG: Material envase primario {self.id} APROBADO (tiene firma en control calidad)"
            )
        else:
            self.estado_aprobacion = "PENDIENTE"
            self.control_calidad = False
            print(
                f"DEBUG: Material envase primario {self.id} PENDIENTE (sin firma)"
            )

        self.save()
        print(
            f"DEBUG: Material envase primario {self.id} guardado, estado: {self.estado_aprobacion}, control_calidad: {self.control_calidad}"
        )

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


# =======================================================
# MATERIAL ENVASE SECUNDARIO Y EMPAQUE
# =======================================================
class MaterialEnvaseSecundarioEmpaque(models.Model):
    ESTADOS_APROBACION = [
        ("PENDIENTE", "Pendiente"),
        ("APROBADO", "Aprobado"),
    ]

    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=255)
    tipo_envase = models.CharField(max_length=100)

    codigo_calidad = models.CharField(
        max_length=50, unique=True, blank=True
    )

    control_calidad = models.BooleanField(default=False)

    estado_aprobacion = models.CharField(
        max_length=20, choices=ESTADOS_APROBACION, default="PENDIENTE"
    )

    def save(self, *args, **kwargs):
        if not self.codigo_calidad:
            last = MaterialEnvaseSecundarioEmpaque.objects.order_by(
                "-id").first()
            next_num = 1
            if last and last.codigo_calidad:
                try:
                    next_num = int(last.codigo_calidad.split("-")[-1]) + 1
                except Exception:
                    next_num = 1
            self.codigo_calidad = f"MES-{next_num:04d}"

        super().save(*args, **kwargs)

    def actualizar_estado_aprobacion(self, control_calidad):
        print(
            f"DEBUG: Actualizando estado de material envase secundario {self.id}"
        )
        print(
            f"DEBUG: Control calidad asociado: {control_calidad.id if control_calidad else 'None'}"
        )
        print(
            f"DEBUG: Control calidad aprobado: {control_calidad.aprobado if control_calidad else 'False'}"
        )
        print(
            f"DEBUG: Control calidad tiene firma: {control_calidad.firma_control_calidad if control_calidad else 'False'}"
        )

        tiene_firma = (
            control_calidad and
            control_calidad.aprobado and
            control_calidad.firma_control_calidad is not None
        )

        if tiene_firma:
            self.estado_aprobacion = "APROBADO"
            self.control_calidad = True
            print(
                f"DEBUG: Material envase secundario {self.id} APROBADO (tiene firma en control calidad)"
            )
        else:
            self.estado_aprobacion = "PENDIENTE"
            self.control_calidad = False
            print(
                f"DEBUG: Material envase secundario {self.id} PENDIENTE (sin firma)"
            )

        self.save()
        print(
            f"DEBUG: Material envase secundario {self.id} guardado, estado: {self.estado_aprobacion}, control_calidad: {self.control_calidad}"
        )

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


# =======================================================
# BODEGAS Y STOCK
# =======================================================
class Bodega(models.Model):
    TIPO_CHOICES = [
        ("MP", "Materia Prima"),
        ("EP", "Envase Primario"),
        ("ES", "Envase Secundario/Empaque"),
        ("PT", "Producto Terminado"),
    ]

    nombre = models.CharField(max_length=255, unique=True)
    tipo = models.CharField(max_length=2, choices=TIPO_CHOICES)
    ubicacion = models.CharField(max_length=255, blank=True)
    es_principal = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"


class StockMateriaPrima(models.Model):
    bodega = models.ForeignKey(
        Bodega, on_delete=models.CASCADE, related_name="stocks_materia_prima"
    )
    materia_prima = models.ForeignKey(
        MateriaPrima, on_delete=models.CASCADE, related_name="stocks"
    )
    cantidad_disponible = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("bodega", "materia_prima")

    def __str__(self):
        return f"Stock MP {self.materia_prima} en {self.bodega}: {self.cantidad_disponible}"


class StockMaterialEnvasePrimario(models.Model):
    bodega = models.ForeignKey(
        Bodega, on_delete=models.CASCADE, related_name="stocks_envase_primario"
    )
    material_envase_primario = models.ForeignKey(
        MaterialEnvasePrimario, on_delete=models.CASCADE, related_name="stocks"
    )
    cantidad_disponible = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("bodega", "material_envase_primario")

    def __str__(self):
        return f"Stock EP {self.material_envase_primario} en {self.bodega}: {self.cantidad_disponible}"


class StockMaterialEnvaseSecundarioEmpaque(models.Model):
    bodega = models.ForeignKey(
        Bodega, on_delete=models.CASCADE, related_name="stocks_envase_secundario"
    )
    material_envase_secundario_empaque = models.ForeignKey(
        MaterialEnvaseSecundarioEmpaque,
        on_delete=models.CASCADE,
        related_name="stocks",
    )
    cantidad_disponible = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("bodega", "material_envase_secundario_empaque")

    def __str__(self):
        return f"Stock ES {self.material_envase_secundario_empaque} en {self.bodega}: {self.cantidad_disponible}"


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

    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    materia_prima = models.ForeignKey(
        MateriaPrima, null=True, blank=True,
        on_delete=models.CASCADE, related_name="controles_calidad"
    )

    material_envase_primario = models.ForeignKey(
        MaterialEnvasePrimario, null=True, blank=True,
        on_delete=models.CASCADE,
        related_name="controles_calidad_envase_primario"
    )

    material_envase_secundario_empaque = models.ForeignKey(
        MaterialEnvaseSecundarioEmpaque, null=True, blank=True,
        on_delete=models.CASCADE,
        related_name="controles_calidad_envase_secundario"
    )

    inspector = models.ForeignKey(
        UsuarioPersonalizado,
        on_delete=models.PROTECT,
        related_name="controles_a_firmar"
    )

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

    TIPO_MOVIMIENTO_CHOICES = [
        ("PRODUCCION", "Producción"),
        ("PEDIDO_BODEGA", "Pedido a bodega"),
    ]

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    tipo_producto = models.ForeignKey(TipoProducto, on_delete=models.CASCADE)

    serie = models.CharField(max_length=50)
    numero_planilla = models.CharField(max_length=50)

    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField()

    # NUEVOS CAMPOS
    batch_standart = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Batch Standart",
    )
    cont_por_100ml = models.DecimalField(
        "Cont. por 100 mL",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # PRODUCCIÓN vs PEDIDO A BODEGA
    tipo_movimiento = models.CharField(
        max_length=20,
        choices=TIPO_MOVIMIENTO_CHOICES,
        default="PRODUCCION",
    )

    control_calidad = models.ForeignKey(
        ControlCalidad, on_delete=models.CASCADE,
        related_name="planillas_fabricacion"
    )

    rendimiento_teorico = models.DecimalField(max_digits=10, decimal_places=2)
    periodo_eficacia = models.IntegerField()
    # cantidad de estuches producidos (columna de la planilla)
    cantidad_estuches = models.DecimalField(max_digits=10, decimal_places=2)
    # cantidad entregada (para pedidos a bodega / control stock)
    cantidad_entregada = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )

    materia_prima = models.ForeignKey(MateriaPrima, on_delete=models.CASCADE)

    firma_jefe_seccion = models.ForeignKey(
        "RegistroFirma", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="firma_js_fabricacion"
    )
    firma_jefe_produccion = models.ForeignKey(
        "RegistroFirma", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="firma_jp_fabricacion"
    )
    # OJO: se elimina firma_inspector_calidad de la planilla
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
            self.firma_quimico_farmaceutico,
        ]
        self.estado_aprobacion = "APROBADO" if all(firmas) else "EN_PROCESO"
        self.save(update_fields=["estado_aprobacion"])

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
        self.save(update_fields=["estado_aprobacion"])

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

    TIPO_MOVIMIENTO_CHOICES = [
        ("PRODUCCION", "Producción"),
        ("PEDIDO_BODEGA", "Pedido a bodega"),
    ]

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    tipo_producto = models.ForeignKey(TipoProducto, on_delete=models.CASCADE)

    serie = models.CharField(maxlength=50) if False else models.CharField(
        max_length=50)  # para evitar errores de copia
    numero_planilla = models.CharField(max_length=50)

    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField()

    # NUEVO CAMPO
    batch_standart = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Batch Standart",
    )

    # PRODUCCIÓN vs PEDIDO A BODEGA
    tipo_movimiento = models.CharField(
        max_length=20,
        choices=TIPO_MOVIMIENTO_CHOICES,
        default="PRODUCCION",
    )

    control_calidad = models.ForeignKey(
        ControlCalidad, on_delete=models.CASCADE
    )

    rendimiento_teorico = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_estuches = models.DecimalField(max_digits=10, decimal_places=2)
    periodo_eficacia = models.IntegerField()
    # cantidad entregada (para pedidos a bodega / control stock)
    cantidad_entregada = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )

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
    # OJO: se elimina firma_inspector_calidad en envase primario
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
            self.firma_quimico_farmaceutico,
        ]
        self.estado_aprobacion = "APROBADO" if all(firmas) else "EN_PROCESO"
        self.save(update_fields=["estado_aprobacion"])

    def __str__(self):
        return f"EnvPrim {self.serie}-{self.numero_planilla}"


# =======================================================
# PLANILLA ENVASE SECUNDARIO Y EMPAQUE
# =======================================================
class PlanillaEnvaseSecundarioEmpaque(ModeloAuditoria):
    ESTADOS_APROBACION = [
        ("EN_PROCESO", "En proceso"),
        ("APROBADO", "Aprobado"),
    ]

    TIPO_MOVIMIENTO_CHOICES = [
        ("PRODUCCION", "Producción"),
        ("PEDIDO_BODEGA", "Pedido a bodega"),
    ]

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    tipo_producto = models.ForeignKey(TipoProducto, on_delete=models.CASCADE)

    serie = models.CharField(max_length=50)
    numero_planilla = models.CharField(max_length=50)

    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField()

    batch_standart = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Batch Standart",
    )

    tipo_movimiento = models.CharField(
        max_length=20,
        choices=TIPO_MOVIMIENTO_CHOICES,
        default="PRODUCCION",
    )

    control_calidad = models.ForeignKey(
        ControlCalidad, on_delete=models.CASCADE
    )

    rendimiento_teorico = models.DecimalField(max_digits=10, decimal_places=2)
    periodo_eficacia = models.IntegerField()
    cantidad_estuches = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_entregada = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )

    material_envase_secundario_empaque = models.ForeignKey(
        MaterialEnvaseSecundarioEmpaque, on_delete=models.CASCADE
    )

    firma_jefe_seccion = models.ForeignKey(
        "RegistroFirma", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="firma_js_envase_secundario"
    )
    firma_jefe_produccion = models.ForeignKey(
        "RegistroFirma", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="firma_jp_envase_secundario"
    )
    firma_quimico_farmaceutico = models.ForeignKey(
        "RegistroFirma", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="firma_qf_envase_secundario"
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
            self.firma_quimico_farmaceutico,
        ]
        self.estado_aprobacion = "APROBADO" if all(firmas) else "EN_PROCESO"
        self.save(update_fields=["estado_aprobacion"])

    def __str__(self):
        return f"EnvSec {self.serie}-{self.numero_planilla}"


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
