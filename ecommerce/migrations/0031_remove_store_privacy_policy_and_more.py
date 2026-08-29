from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "ecommerce",
            "0030_alter_store_options_remove_store_address_and_more",
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="StoreAnnouncement",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        (
                            "text",
                            models.CharField(
                                max_length=255,
                                verbose_name="نص الإعلان",
                            ),
                        ),
                        (
                            "sort_order",
                            models.PositiveIntegerField(
                                default=0,
                                verbose_name="ترتيب الإعلان",
                            ),
                        ),
                        (
                            "shipping_policy",
                            models.TextField(
                                blank=True,
                                default="",
                                verbose_name="سياسة الشحن",
                            ),
                        ),
                        (
                            "return_policy",
                            models.TextField(
                                blank=True,
                                default="",
                                verbose_name="سياسة الاسترجاع",
                            ),
                        ),
                        (
                            "terms_policy",
                            models.TextField(
                                blank=True,
                                default="",
                                verbose_name="الشروط والأحكام",
                            ),
                        ),
                        (
                            "privacy_policy",
                            models.TextField(
                                blank=True,
                                default="",
                                verbose_name="سياسة الخصوصية",
                            ),
                        ),
                        (
                            "facebook_url",
                            models.URLField(
                                blank=True,
                                null=True,
                                verbose_name="رابط فيسبوك",
                            ),
                        ),
                        (
                            "instagram_url",
                            models.URLField(
                                blank=True,
                                null=True,
                                verbose_name="رابط إنستغرام",
                            ),
                        ),
                        (
                            "twitter_url",
                            models.URLField(
                                blank=True,
                                null=True,
                                verbose_name="رابط X",
                            ),
                        ),
                        (
                            "whatsapp_url",
                            models.URLField(
                                blank=True,
                                null=True,
                                verbose_name="رابط واتساب",
                            ),
                        ),
                        (
                            "youtube_url",
                            models.URLField(
                                blank=True,
                                null=True,
                                verbose_name="رابط يوتيوب",
                            ),
                        ),
                        (
                            "address",
                            models.TextField(
                                blank=True,
                                default="",
                                verbose_name="العنوان",
                            ),
                        ),
                        (
                            "country",
                            models.CharField(
                                max_length=100,
                                blank=True,
                                default="",
                                verbose_name="الدولة",
                            ),
                        ),
                        (
                            "city",
                            models.CharField(
                                max_length=100,
                                blank=True,
                                default="",
                                verbose_name="المدينة",
                            ),
                        ),
                        (
                            "district",
                            models.CharField(
                                max_length=100,
                                blank=True,
                                default="",
                                verbose_name="الحي",
                            ),
                        ),
                        (
                            "street",
                            models.CharField(
                                max_length=200,
                                blank=True,
                                default="",
                                verbose_name="الشارع",
                            ),
                        ),
                        (
                            "building_no",
                            models.CharField(
                                max_length=50,
                                blank=True,
                                default="",
                                verbose_name="رقم المبنى",
                            ),
                        ),
                        (
                            "unit_no",
                            models.CharField(
                                max_length=50,
                                blank=True,
                                default="",
                                verbose_name="رقم الوحدة",
                            ),
                        ),
                        (
                            "postal_code",
                            models.CharField(
                                max_length=20,
                                blank=True,
                                default="",
                                verbose_name="الرمز البريدي",
                            ),
                        ),
                        (
                            "google_map_url",
                            models.URLField(
                                blank=True,
                                default="",
                                verbose_name="رابط خرائط Google",
                            ),
                        ),
                        (
                            "top_bar_text",
                            models.CharField(
                                max_length=255,
                                blank=True,
                                default="",
                                verbose_name="رسالة الشريط العلوي",
                            ),
                        ),
                        (
                            "top_bar_enabled",
                            models.BooleanField(
                                default=True,
                                verbose_name="إظهار الشريط العلوي",
                            ),
                        ),
                        (
                            "is_active",
                            models.BooleanField(
                                default=True,
                                verbose_name="نشط",
                            ),
                        ),
                        (
                            "created_at",
                            models.DateTimeField(
                                auto_now_add=True,
                            ),
                        ),
                        (
                            "updated_at",
                            models.DateTimeField(
                                auto_now=True,
                            ),
                        ),
                        (
                            "store",
                            models.ForeignKey(
                                on_delete=models.deletion.CASCADE,
                                related_name="announcements",
                                to="ecommerce.store",
                                verbose_name="المتجر",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "إعلان الشريط العلوي",
                        "verbose_name_plural": "إعلانات الشريط العلوي",
                        "ordering": ["sort_order", "id"],
                    },
                ),
            ],
        ),
    ]
