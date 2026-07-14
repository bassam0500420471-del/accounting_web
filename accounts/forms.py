from django import forms
from django.contrib.auth.models import User
from django.db import transaction
from .models import Company, Branch


class RegisterCompanyForm(forms.Form):
    # ==========================================
    # 🏢 بيانات الشركة الأساسية والرسمية
    # ==========================================
    company_name = forms.CharField(
        max_length=200,
        label="اسم الشركة (بالعربي)",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "مثال: شركة مصمم الأزهار",
            "autocomplete": "off",
        })
    )

    company_name_en = forms.CharField(
        max_length=200,
        required=False,
        label="اسم الشركة بالإنجليزية",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Example: Flower Designer Co.",
            "autocomplete": "off",
        })
    )

    vat_no = forms.CharField(
        max_length=20,
        required=False,
        label="الرقم الضريبي",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "الرقم الضريبي المكون من 15 رقم",
            "autocomplete": "off",
        })
    )

    commercial_record = forms.CharField(
        max_length=50,
        required=False,
        label="السجل التجاري",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "رقم السجل التجاري",
            "autocomplete": "off",
        })
    )

    # ==========================================
    # 📍 بيانات الموقع والعنوان الوطني
    # ==========================================
    country = forms.CharField(
        max_length=100,
        initial="المملكة العربية السعودية",
        label="الدولة",
        widget=forms.TextInput(attrs={
            "class": "form-control",
        })
    )

    city = forms.CharField(
        max_length=100,
        required=False,
        label="المدينة",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "مثال: الرياض",
        })
    )

    district = forms.CharField(
        max_length=100,
        required=False,
        label="الحي",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "مثال: الصحافة",
        })
    )

    street = forms.CharField(
        max_length=200,
        required=False,
        label="الشارع",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "اسم الشارع الرئيسي",
        })
    )

    building_no = forms.CharField(
        max_length=20,
        required=False,
        label="رقم المبنى",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "مثال: 1234",
        })
    )

    postal_code = forms.CharField(
        max_length=20,
        required=False,
        label="الرمز البريدي",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "مثال: 11564",
        })
    )

    additional_no = forms.CharField(
        max_length=20,
        required=False,
        label="الرقم الإضافي",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "مثال: 5678",
        })
    )

    national_address = forms.CharField(
        required=False,
        label="العنوان الوطني الكامل",
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 2,
            "placeholder": "اكتب العنوان الوطني بالتفصيل هنا...",
        })
    )

    # ==========================================
    # 📞 وسائل التواصل
    # ==========================================
    phone = forms.CharField(
        max_length=30,
        required=False,
        label="الهاتف الثابت",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "011XXXXXXX",
        })
    )

    mobile = forms.CharField(
        max_length=30,
        required=False,
        label="جوال الشركة",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "05XXXXXXXX",
        })
    )

    email = forms.EmailField(
        required=False,
        label="البريد الإلكتروني للشركة",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "info@company.com",
        })
    )

    website = forms.URLField(
        required=False,
        label="الموقع الإلكتروني",
        widget=forms.URLInput(attrs={
            "class": "form-control",
            "placeholder": "https://example.com",
        })
    )

    # ==========================================
    # 🏦 الحساب البنكي
    # ==========================================
    bank_name = forms.CharField(
        max_length=150,
        required=False,
        label="اسم البنك",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "مثال: مصرف الراجحي",
        })
    )

    iban = forms.CharField(
        max_length=50,
        required=False,
        label="رقم الآيبان (IBAN)",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "SAXXXXXXXXXXXXXXXXXXXXXXXX",
        })
    )

    account_number = forms.CharField(
        max_length=50,
        required=False,
        label="رقم الحساب",
        widget=forms.TextInput(attrs={
            "class": "form-control",
        })
    )

    swift_code = forms.CharField(
        max_length=30,
        required=False,
        label="Swift Code",
        widget=forms.TextInput(attrs={
            "class": "form-control",
        })
    )

    notes = forms.CharField(
        required=False,
        label="ملاحظات إضافية",
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 2,
        })
    )

    # ==========================================
    # 👤 بيانات مدير النظام (Owner)
    # ==========================================
    owner_username = forms.CharField(
        max_length=150,
        label="اسم مستخدم المدير",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "مثال: admin",
            "autocomplete": "off",
        })
    )

    owner_email = forms.EmailField(
        label="البريد الإلكتروني للمدير",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "admin@email.com",
            "autocomplete": "off",
        })
    )

    password1 = forms.CharField(
        label="كلمة المرور",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "••••••••",
            "autocomplete": "new-password",
        }, render_value=False)
    )

    password2 = forms.CharField(
        label="تأكيد كلمة المرور",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "••••••••",
            "autocomplete": "new-password",
        }, render_value=False)
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # تعطيل التصحيح التلقائي لمنع مشاكل المتصفحات المزعجة
        for field_name, field in self.fields.items():
            if field_name not in ["notes", "national_address"]:
                field.widget.attrs.update({
                    "autocapitalize": "off",
                    "autocorrect": "off",
                    "spellcheck": "false",
                })

    def clean_owner_username(self):
        username = (self.cleaned_data.get("owner_username") or "").strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("اسم المستخدم مستخدم بالفعل، اختر اسمًا آخر.")
        return username

    def clean_owner_email(self):
        email = (self.cleaned_data.get("owner_email") or "").strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("البريد الإلكتروني مستخدم بالفعل، استخدم بريدًا آخر.")
        return email

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            self.add_error("password2", "كلمتا المرور غير متطابقتين")
        return cleaned

    @transaction.atomic
    def save(self):
        # 1. إنشاء الشركة وحفظ كافة البيانات المدخلة في الشاشة الرئيسية
        company = Company.objects.create(
            name=self.cleaned_data["company_name"],
            name_en=self.cleaned_data.get("company_name_en"),
            vat_no=self.cleaned_data.get("vat_no"),
            commercial_record=self.cleaned_data.get("commercial_record"),
            country=self.cleaned_data.get("country", "المملكة العربية السعودية"),
            city=self.cleaned_data.get("city"),
            district=self.cleaned_data.get("district"),
            street=self.cleaned_data.get("street"),
            building_no=self.cleaned_data.get("building_no"),
            postal_code=self.cleaned_data.get("postal_code"),
            additional_no=self.cleaned_data.get("additional_no"),
            national_address=self.cleaned_data.get("national_address"),
            phone=self.cleaned_data.get("phone"),
            mobile=self.cleaned_data.get("mobile"),
            email=self.cleaned_data.get("email"),
            website=self.cleaned_data.get("website"),
            bank_name=self.cleaned_data.get("bank_name"),
            iban=self.cleaned_data.get("iban"),
            account_number=self.cleaned_data.get("account_number"),
            swift_code=self.cleaned_data.get("swift_code"),
            notes=self.cleaned_data.get("notes"),
        )

        # 2. إنشاء الفرع الرئيسي للشركة تلقائياً
        main_branch = Branch.objects.create(
            company=company,
            name="الفرع الرئيسي"
        )

        # 3. إنشاء مستخدم مالك النظام
        user = User.objects.create_user(
            username=self.cleaned_data["owner_username"],
            email=self.cleaned_data["owner_email"],
            password=self.cleaned_data["password1"],
        )

        # 4. ربط وتحديث الـ Profile عن طريق السجنل المجهز في الموديل
        profile = user.profile
        profile.company = company
        profile.branch = main_branch
        profile.role = "owner"
        profile.save()

        return company, user