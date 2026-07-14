from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from accounts.models import Company, Branch


# ============================
# 🎯 مراكز التكلفة
# ============================
class CostCenter(models.Model):

    TYPE_CHOICES = [
        ("BRANCH", "فرع"),
        ("PROJECT", "مشروع"),
        ("EMPLOYEE", "موظف"),
        ("SUPPLIER", "مورد"),
        ("CUSTOMER", "عميل"),
        ("CONTRACTOR", "مقاول"),
        ("DEPARTMENT", "إدارة"),
        ("OTHER", "أخرى"),
    ]

    STATUS_CHOICES = [
        ("ACTIVE", "نشط"),
        ("CLOSED", "مغلق"),
    ]

    # ✅ مؤقتاً تقبل null/blank حتى نملأ السجلات القديمة
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="cost_centers",
        verbose_name="الشركة",
        null=True,
        blank=True
    )

    name = models.CharField(
        max_length=200,
        verbose_name="اسم مركز التكلفة"
    )

    code = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        verbose_name="كود مركز التكلفة"
    )

    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        verbose_name="نوع مركز التكلفة"
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="ACTIVE",
        verbose_name="الحالة"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="نشط؟"
    )

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.CASCADE,
        verbose_name="مركز أعلى"
    )

    branch = models.ForeignKey(
        Branch,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="الفرع"
    )

    # 🔗 ربط ديناميكي (مورد / عميل / موظف ...)
    content_type = models.ForeignKey(
        ContentType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    object_id = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    content_object = GenericForeignKey("content_type", "object_id")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "مركز تكلفة"
        verbose_name_plural = "مراكز التكلفة"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"],
                name="cc_uniq_name_per_company"
            ),
            models.UniqueConstraint(
                fields=["company", "code"],
                name="cc_uniq_code_per_company"
            ),
        ]

    def clean(self):
        # لازم الشركة تكون موجودة في السجلات الجديدة
        if not self.company:
            return

        # الأب لازم يكون من نفس الشركة
        if self.parent and self.parent.company_id != self.company_id:
            raise ValidationError({
                "parent": "لا يمكن اختيار مركز أب من شركة أخرى."
            })

        # الفرع لازم يكون من نفس الشركة
        if self.branch and self.branch.company_id != self.company_id:
            raise ValidationError({
                "branch": "لا يمكن اختيار فرع من شركة أخرى."
            })

        # التحقق من الربط الديناميكي
        if self.content_type_id and self.object_id:
            obj = self.content_object
            if obj is None:
                raise ValidationError("العنصر المرتبط غير موجود.")

            obj_company_id = getattr(obj, "company_id", None)
            if obj_company_id and obj_company_id != self.company_id:
                raise ValidationError("لا يمكن ربط مركز التكلفة بعنصر يتبع لشركة أخرى.")

        # لو النوع مورد لازم يكون فيه مورد مربوط
        if self.type == "SUPPLIER" and not (self.content_type_id and self.object_id):
            raise ValidationError({
                "type": "عند اختيار نوع مورد يجب ربط مورد."
            })

        # لو النوع عميل لازم يكون فيه عميل مربوط
        if self.type == "CUSTOMER" and not (self.content_type_id and self.object_id):
            raise ValidationError({
                "type": "عند اختيار نوع عميل يجب ربط عميل."
            })

    def save(self, *args, **kwargs):
        self.is_active = (self.status == "ACTIVE")
        self.full_clean()
        super().save(*args, **kwargs)

    def is_root(self):
        return self.parent is None

    def has_children(self):
        return self.children.exists()

    def __str__(self):
        if self.parent:
            return f"{self.parent} › {self.name}"
        return self.name