from django.db import models


class Account(models.Model):
    """
    Chart of Accounts - شجرة الحسابات
    """

    ACCOUNT_TYPES = [
        ('ASSET', 'أصول'),
        ('LIABILITY', 'خصوم'),
        ('EQUITY', 'حقوق ملكية'),
        ('REVENUE', 'إيرادات'),
        ('EXPENSE', 'مصروفات'),
    ]

    NATURE_CHOICES = [
        ('DEBIT', 'مدين'),
        ('CREDIT', 'دائن'),
    ]

    company = models.ForeignKey(
        'accounts.Company',
        on_delete=models.CASCADE,
        related_name='accounts',
        null=True,
        blank=True,
        verbose_name='الشركة'
    )

    code = models.CharField(
        max_length=20,
        verbose_name='رقم الحساب'
    )

    name = models.CharField(
        max_length=255,
        verbose_name='اسم الحساب'
    )

    name_en = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='اسم الحساب بالإنجليزية'
    )

    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPES,
        verbose_name='نوع الحساب الأساسي'
    )

    nature = models.CharField(
        max_length=10,
        choices=NATURE_CHOICES,
        verbose_name='الطبيعة المحاسبية'
    )

    parent = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='الحساب الأب'
    )

    is_group = models.BooleanField(
        default=False,
        verbose_name='حساب تجميعي',
        help_text='لا يقبل قيود مباشرة'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='نشط'
    )

    is_locked = models.BooleanField(
        default=False,
        verbose_name='مقفول'
    )

    is_payment_method = models.BooleanField(
        default=False,
        verbose_name='طريقة دفع'
    )


    tags = models.JSONField(
        default=list,
        blank=True,
        verbose_name='وسوم'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['code']
        verbose_name = 'حساب'
        verbose_name_plural = 'شجرة الحسابات'
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'code'],
                name='unique_account_code_per_company'
            )
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def is_postable(self):
        return not self.is_group