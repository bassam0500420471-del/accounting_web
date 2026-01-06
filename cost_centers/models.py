from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


# ============================
# 🏢 الفروع
# ============================
class Branch(models.Model):
    name = models.CharField(
        max_length=150,
        verbose_name="اسم الفرع"
    )

    code = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="كود الفرع"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


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

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.CASCADE,
        verbose_name="مستوى مركز التكلفة (يتبع لمركز)"
    )

    branch = models.ForeignKey(
        Branch,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="الفرع"
    )

    # ============================
    # 🔗 ربط ديناميكي (مورد / عميل / موظف ...)
    # ============================
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

    content_object = GenericForeignKey(
        "content_type",
        "object_id"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "مركز تكلفة"
        verbose_name_plural = "مراكز التكلفة"

    # ============================
    # 🌳 دوال مساعدة للشجرة
    # ============================
    def is_root(self):
        return self.parent is None

    def has_children(self):
        return self.children.exists()

    def __str__(self):
        if self.parent:
            return f"{self.parent} › {self.name}"
        return self.name
