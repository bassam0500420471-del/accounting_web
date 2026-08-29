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

    shipping_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=15.00,
        verbose_name="سعر التوصيل",
    )

    # =====================================================
    # روابط التواصل الاجتماعي
    # =====================================================

    facebook_url = models.URLField(
        blank=True,
        null=True,
        verbose_name="رابط فيسبوك",
    )

    instagram_url = models.URLField(
        blank=True,
        null=True,
        verbose_name="رابط إنستغرام",
    )

    twitter_url = models.URLField(
        blank=True,
        null=True,
        verbose_name="رابط X",
    )

    whatsapp_url = models.URLField(
        blank=True,
        null=True,
        verbose_name="رابط واتساب",
    )

    youtube_url = models.URLField(
        blank=True,
        null=True,
        verbose_name="رابط يوتيوب",
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

    # =====================================================
    # حالة المتجر
    # =====================================================

    is_active = models.BooleanField(
        default=True,
        verbose_name="نشط",
    )

    # =====================================================
    # التواريخ
    # =====================================================

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
# إعلانات الشريط العلوي
# =====================================================

class StoreAnnouncement(models.Model):

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="announcements",
        verbose_name="المتجر",
    )

    text = models.CharField(
        max_length=255,
        verbose_name="نص الإعلان",
    )

    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name="ترتيب الإعلان",
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
        ordering = [
            "sort_order",
            "id",
        ]

        verbose_name = "إعلان الشريط العلوي"
        verbose_name_plural = "إعلانات الشريط العلوي"

    def __str__(self):
        return f"{self.store.name} - {self.text}"


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
# سياسات المتجر
# =====================================================

class StorePolicy(models.Model):

    POLICY_TYPES = (
        ("shipping", "سياسة الشحن"),
        ("return", "سياسة الاسترجاع"),
        ("terms", "الشروط والأحكام"),
        ("privacy", "سياسة الخصوصية"),
    )

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="policies",
        verbose_name="المتجر",
    )

    policy_type = models.CharField(
        max_length=20,
        choices=POLICY_TYPES,
        verbose_name="نوع السياسة",
    )

    title = models.CharField(
        max_length=200,
        verbose_name="عنوان السياسة",
    )

    content = models.TextField(
        blank=True,
        verbose_name="محتوى السياسة",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="آخر تحديث",
    )

    class Meta:
        verbose_name = "سياسة متجر"
        verbose_name_plural = "سياسات المتجر"

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "store",
                    "policy_type",
                ],
                name="unique_store_policy",
            )
        ]

    def __str__(self):
        return f"{self.store.name} - {self.title}"


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
        ordering = [
            "sort_order",
        ]

    def __str__(self):
        return self.title
