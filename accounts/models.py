from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


# ==========================================================
# 🏢 الشركة
# ==========================================================
class Company(models.Model):

    # ==========================================
    # البيانات الأساسية
    # ==========================================
    name = models.CharField(
        "اسم الشركة",
        max_length=200
    )

    name_en = models.CharField(
        "اسم الشركة بالإنجليزية",
        max_length=200,
        blank=True,
        null=True
    )

    # ==========================================
    # الشعار
    # ==========================================
    logo = models.ImageField(
        "شعار الشركة",
        upload_to="company_logos/",
        blank=True,
        null=True
    )

    # ==========================================
    # البيانات الرسمية
    # ==========================================
    vat_no = models.CharField(
        "الرقم الضريبي",
        max_length=20,
        blank=True,
        null=True
    )

    commercial_record = models.CharField(
        "السجل التجاري",
        max_length=50,
        blank=True,
        null=True
    )

    national_address = models.TextField(
        "العنوان الوطني",
        blank=True,
        null=True
    )

    # ==========================================
    # بيانات الموقع
    # ==========================================
    country = models.CharField(
        "الدولة",
        max_length=100,
        default="المملكة العربية السعودية"
    )

    city = models.CharField(
        "المدينة",
        max_length=100,
        blank=True,
        null=True
    )

    district = models.CharField(
        "الحي",
        max_length=100,
        blank=True,
        null=True
    )

    street = models.CharField(
        "الشارع",
        max_length=200,
        blank=True,
        null=True
    )

    building_no = models.CharField(
        "رقم المبنى",
        max_length=20,
        blank=True,
        null=True
    )

    postal_code = models.CharField(
        "الرمز البريدي",
        max_length=20,
        blank=True,
        null=True
    )

    additional_no = models.CharField(
        "الرقم الإضافي",
        max_length=20,
        blank=True,
        null=True
    )

    # ==========================================
    # وسائل التواصل
    # ==========================================
    phone = models.CharField(
        "الهاتف",
        max_length=30,
        blank=True,
        null=True
    )

    mobile = models.CharField(
        "الجوال",
        max_length=30,
        blank=True,
        null=True
    )

    email = models.EmailField(
        "البريد الإلكتروني",
        blank=True,
        null=True
    )

    website = models.URLField(
        "الموقع الإلكتروني",
        blank=True,
        null=True
    )

    # ==========================================
    # الحساب البنكي
    # ==========================================
    bank_name = models.CharField(
        "اسم البنك",
        max_length=150,
        blank=True,
        null=True
    )

    iban = models.CharField(
        "رقم الآيبان",
        max_length=50,
        blank=True,
        null=True
    )

    account_number = models.CharField(
        "رقم الحساب",
        max_length=50,
        blank=True,
        null=True
    )

    swift_code = models.CharField(
        "Swift Code",
        max_length=30,
        blank=True,
        null=True
    )

    # ==========================================
    # بيانات إضافية
    # ==========================================
    notes = models.TextField(
        "ملاحظات",
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        "نشطة",
        default=True
    )

    created_at = models.DateTimeField(
        "تاريخ الإنشاء",
        auto_now_add=True
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "شركة"
        verbose_name_plural = "الشركات"

    def __str__(self):
        return self.name


# ==========================================================
# 🏢 الفروع
# ==========================================================
class Branch(models.Model):

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="branches"
    )

    name = models.CharField(
        "اسم الفرع",
        max_length=150
    )

    is_active = models.BooleanField(
        "نشط",
        default=True
    )

    created_at = models.DateTimeField(
        "تاريخ الإنشاء",
        auto_now_add=True
    )

    class Meta:
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"],
                name="uniq_branch_name_per_company",
            )
        ]

    def __str__(self):
        return f"{self.company.name} - {self.name}"
# ==========================================================
# 👤 ملف المستخدم
# ==========================================================
class UserProfile(models.Model):

    ROLE_CHOICES = (
        ("owner", "Owner"),
        ("admin", "Admin"),
        ("staff", "Staff"),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True,
    )

    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        related_name="users",
        null=True,
        blank=True,
        verbose_name="الفرع"
    )

    role = models.CharField(
        "الصلاحية",
        max_length=20,
        choices=ROLE_CHOICES,
        default="staff"
    )

    avatar = models.ImageField(
        "صورة المستخدم",
        upload_to="avatars/",
        blank=True,
        null=True
    )

    phone = models.CharField(
        "رقم الجوال",
        max_length=30,
        blank=True,
        null=True
    )

    job_title = models.CharField(
        "المسمى الوظيفي",
        max_length=100,
        blank=True,
        null=True
    )

    language = models.CharField(
        "اللغة",
        max_length=10,
        default="ar"
    )

    is_active = models.BooleanField(
        "نشط",
        default=True
    )

    created_at = models.DateTimeField(
        "تاريخ الإنشاء",
        auto_now_add=True
    )

    class Meta:
        verbose_name = "مستخدم"
        verbose_name_plural = "المستخدمون"

    def __str__(self):
        company = self.company.name if self.company else "No Company"
        return f"{self.user.username} - {company}"


# ==========================================================
# إنشاء Profile تلقائياً
# ==========================================================
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


# ==========================================================
# حفظ Profile
# ==========================================================
@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, "profile"):
        pass