from django.db import models


# =====================================================
# المتجر الإلكتروني
# =====================================================

class Store(models.Model):
    """
    متجر إلكتروني تابع لشركة
    """

    company = models.OneToOneField(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="online_store",
        verbose_name="الشركة",
    )

    name = models.CharField(
        max_length=200,
        verbose_name="اسم المتجر",
    )

    slug = models.SlugField(
        max_length=200,
        unique=True,
        verbose_name="الرابط",
    )

    logo = models.ImageField(
        upload_to="stores/logos/",
        blank=True,
        null=True,
        verbose_name="الشعار",
    )

    favicon = models.ImageField(
        upload_to="stores/favicon/",
        blank=True,
        null=True,
        verbose_name="أيقونة المتجر",
    )

    description = models.TextField(
        blank=True,
        verbose_name="وصف المتجر",
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="الهاتف",
    )

    email = models.EmailField(
        blank=True,
        verbose_name="البريد الإلكتروني",
    )


    # =====================================================
    # عنوان المتجر
    # =====================================================

    address = models.TextField(
        blank=True,
        default="",
        verbose_name="العنوان",
    )


    country = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="الدولة",
    )


    city = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="المدينة",
    )


    district = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="الحي",
    )


    street = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="الشارع",
    )


    building_no = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="رقم المبنى",
    )


    unit_no = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="رقم الوحدة",
    )


    postal_code = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name="الرمز البريدي",
    )


    google_map_url = models.URLField(
        blank=True,
        default="",
        verbose_name="رابط خرائط Google",
    )


    # =====================================================
    # إعدادات الشريط العلوي
    # =====================================================

    top_bar_text = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="رسالة الشريط العلوي",
    )


    top_bar_enabled = models.BooleanField(
        default=True,
        verbose_name="إظهار الشريط العلوي",
    )


    is_active = models.BooleanField(
        default=True,
        verbose_name="نشط",
    )


    created_at = models.DateTimeField(
        auto_now_add=True,
    )


    updated_at = models.DateTimeField(
        auto_now=True,
    )


    class Meta:
        verbose_name = "متجر إلكتروني"
        verbose_name_plural = "المتاجر الإلكترونية"


    def __str__(self):
        return self.name

# =====================================================
# تصميم المتجر
# =====================================================

class StoreTheme(models.Model):
    """
    إعدادات شكل المتجر
    """

    store = models.OneToOneField(
        Store,
        on_delete=models.CASCADE,
        related_name="theme",
    )

    primary_color = models.CharField(
        max_length=20,
        default="#000000",
    )

    secondary_color = models.CharField(
        max_length=20,
        default="#ffffff",
    )

    font_family = models.CharField(
        max_length=100,
        default="Tahoma",
    )

    dark_mode = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f"Theme - {self.store.name}"



# =====================================================
# إعدادات المتجر
# =====================================================

class StoreSetting(models.Model):

    store = models.OneToOneField(
        Store,
        on_delete=models.CASCADE,
        related_name="settings",
    )

    allow_guest_checkout = models.BooleanField(
        default=True,
        verbose_name="السماح بالشراء كزائر",
    )

    show_stock = models.BooleanField(
        default=True,
        verbose_name="إظهار المخزون",
    )

    enable_reviews = models.BooleanField(
        default=True,
        verbose_name="تفعيل التقييمات",
    )

    enable_wishlist = models.BooleanField(
        default=True,
        verbose_name="تفعيل المفضلة",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )



# =====================================================
# نطاق المتجر
# =====================================================

class StoreDomain(models.Model):

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="domains",
    )

    domain = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="الدومين",
    )

    is_primary = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return self.domain



# =====================================================
# أقسام الصفحة الرئيسية
# =====================================================

class HomepageSection(models.Model):

    SECTION_TYPES = (
        ("banner", "بانر"),
        ("category", "تصنيفات"),
        ("products", "منتجات"),
        ("text", "نص"),
    )

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="homepage_sections",
    )

    title = models.CharField(
        max_length=200,
    )

    section_type = models.CharField(
        max_length=30,
        choices=SECTION_TYPES,
    )

    image = models.ImageField(
        upload_to="stores/home/",
        blank=True,
        null=True,
    )

    sort_order = models.PositiveIntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["sort_order"]

    def __str__(self):
        return self.title