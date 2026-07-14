from django.db import models
from accounts.models import Company

class CompanyInfo(models.Model):
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name="info",
        verbose_name="الشركة"
    )

    # 🏢 بيانات الشركة الأساسية والرسمية
    name = models.CharField(max_length=255, blank=True, null=True, verbose_name="اسم الشركة (بالعربي)")
    name_en = models.CharField(max_length=255, blank=True, null=True, verbose_name="اسم الشركة بالإنجليزية")
    tax_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="الرقم الضريبي")
    commercial_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="السجل التجاري")

    # 📍 بيانات الموقع والعنوان الوطني
    country = models.CharField(max_length=100, default="المملكة العربية السعودية", verbose_name="الدولة")
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name="المدينة")
    district = models.CharField(max_length=100, blank=True, null=True, verbose_name="الحي")
    street = models.CharField(max_length=200, blank=True, null=True, verbose_name="الشارع")
    building_no = models.CharField(max_length=20, blank=True, null=True, verbose_name="رقم المبنى")
    postal_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="الرمز البريدي")
    additional_no = models.CharField(max_length=20, blank=True, null=True, verbose_name="الرقم الإضافي")
    national_address = models.TextField(blank=True, null=True, verbose_name="العنوان الوطني الكامل")

    # 📞 وسائل التواصل
    phone = models.CharField(max_length=50, blank=True, null=True, verbose_name="الهاتف الثابت")
    mobile = models.CharField(max_length=50, blank=True, null=True, verbose_name="جوال الشركة")
    email = models.EmailField(blank=True, null=True, verbose_name="البريد الإلكتروني للشركة")
    website = models.URLField(blank=True, null=True, verbose_name="الموقع الإلكتروني")
    logo = models.ImageField(upload_to='company/', blank=True, null=True, verbose_name="الشعار")

    # 🏦 الحساب البنكي
    bank_name = models.CharField(max_length=150, blank=True, null=True, verbose_name="اسم البنك")
    iban = models.CharField(max_length=50, blank=True, null=True, verbose_name="رقم الآيبان (IBAN)")
    account_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="رقم الحساب")
    swift_code = models.CharField(max_length=30, blank=True, null=True, verbose_name="Swift Code")

    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات إضافية")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")

    class Meta:
        verbose_name = "معلومات الشركة"
        verbose_name_plural = "معلومات الشركات"

    def __str__(self):
        return self.name if self.name else f"معلومات الـ {self.company}"