from django.db import models


class CostCenter(models.Model):
    """
    Cost Center - مركز تكلفة
    يمكن استخدامه للأقسام / الفروع / المشاريع
    """

    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='كود مركز التكلفة'
    )

    name = models.CharField(
        max_length=255,
        verbose_name='اسم مركز التكلفة'
    )

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='مركز التكلفة الأب'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='نشط'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['code']
        verbose_name = 'مركز تكلفة'
        verbose_name_plural = 'مراكز التكلفة'

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def is_root(self):
        return self.parent is None
