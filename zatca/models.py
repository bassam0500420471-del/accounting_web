from django.db import models
from company.models import Company


class ZatcaSettings(models.Model):

    SANDBOX = "sandbox"
    SIMULATION = "simulation"
    PRODUCTION = "production"

    ENVIRONMENT_CHOICES = [
        (SANDBOX, "Sandbox"),
        (SIMULATION, "Simulation"),
        (PRODUCTION, "Production"),
    ]

    STATUS_CHOICES = [
        ("draft", "غير جاهز"),
        ("csr_created", "تم إنشاء CSR"),
        ("compliance", "اختبار الامتثال"),
        ("active", "مفعل"),
        ("failed", "فشل الربط"),
    ]

    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name="zatca",
        verbose_name="الشركة",
    )

    environment = models.CharField(
        max_length=20,
        choices=ENVIRONMENT_CHOICES,
        default=SANDBOX,
        verbose_name="بيئة العمل",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
        verbose_name="حالة الربط",
    )

    is_enabled = models.BooleanField(
        default=False,
        verbose_name="تفعيل الربط",
    )

    device_uuid = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Device UUID",
    )

    compliance_request_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Compliance Request ID",
    )

    binary_security_token = models.TextField(
        blank=True,
        null=True,
        verbose_name="Binary Security Token",
    )

    secret = models.TextField(
        blank=True,
        null=True,
        verbose_name="Secret",
    )

    certificate = models.TextField(
        blank=True,
        null=True,
        verbose_name="Certificate",
    )

    private_key = models.TextField(
        blank=True,
        null=True,
        verbose_name="Private Key",
    )

    public_key = models.TextField(
        blank=True,
        null=True,
        verbose_name="Public Key",
    )

    csr = models.TextField(
        blank=True,
        null=True,
        verbose_name="CSR",
    )

    private_key_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Private Key Path",
    )

    public_key_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Public Key Path",
    )

    csr_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="CSR Path",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="آخر تحديث",
    )

    def __str__(self):
        return f"{self.company.name} - {self.environment}"