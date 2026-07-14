from django import forms
from django.contrib.auth.models import User
from django.db import transaction

# استيراد الموديلات الرسمية من تطبيق accounts
from accounts.models import Company, Branch  


# 1️⃣ فورم شاشة إعدادات الشركة (التعديل والتحديث بعد التسجيل)
class CompanySettingsUpdateForm(forms.ModelForm):
    # نقوم بربط مسميات الحقول برمجياً لتتوافق مع الـ HTML دون التسبب في خطأ بقاعدة البيانات
    tax_number = forms.CharField(label="الرقم الضريبي", required=False)
    commercial_number = forms.CharField(label="السجل التجاري", required=False)

    class Meta:
        model = Company  
        fields = [
            'name', 'name_en', 'country', 'city', 'district', 'street', 
            'building_no', 'postal_code', 'additional_no', 'national_address',
            'phone', 'mobile', 'email', 'website', 'logo',
            'bank_name', 'iban', 'account_number', 'swift_code', 'notes'
        ]
        widgets = {
            "national_address": forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "اكتب العنوان الوطني بالتفصيل هنا..."}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # تحميل البيانات من قاعدة البيانات إلى الحقول البديلة عند عرض الصفحة بشكل آمن ومحاذٍ داخلياً
        if self.instance and self.instance.pk:
            # نقوم بجلب القيمة الحقيقية للرقم الضريبي سواء كان الحقل اسمه vat_no أو tax_number
            self.fields['tax_number'].initial = getattr(self.instance, 'vat_no', getattr(self.instance, 'tax_number', ''))
            
            # نقوم بجلب القيمة الحقيقية للسجل التجاري سواء كان الحقل اسمه commercial_record أو commercial_number
            self.fields['commercial_number'].initial = getattr(self.instance, 'commercial_record', getattr(self.instance, 'commercial_number', ''))

        field_order = [
            'name', 'name_en', 'tax_number', 'commercial_number',
            'country', 'city', 'district', 'street', 'building_no', 'postal_code', 'additional_no', 'national_address',
            'phone', 'mobile', 'email', 'website', 'logo',
            'bank_name', 'iban', 'account_number', 'swift_code', 'notes'
        ]
        self.order_fields(field_order)

        for field_name, field in self.fields.items():
            existing_class = field.widget.attrs.get("class", "")
            if "form-control" not in existing_class:
                field.widget.attrs.update({"class": f"form-control {existing_class}".strip()})

            if field_name not in ["notes", "national_address"]:
                field.widget.attrs.update({
                    "autocapitalize": "off",
                    "autocorrect": "off",
                    "spellcheck": "false",
                })

    def save(self, commit=True):
        instance = super().save(commit=False)
        # نقل القيم المستقبلة من الـ HTML إلى الحقول الحقيقية في قاعدة البيانات قبل الحفظ
        instance.vat_no = self.cleaned_data.get('tax_number', '')
        instance.commercial_record = self.cleaned_data.get('commercial_number', '')
        if commit:
            instance.save()
        return instance


# 2️⃣ فورم شاشة التسجيل الأولي (عند إنشاء الحساب لأول مرة)
class CompanySettingsForm(forms.ModelForm):
    tax_number = forms.CharField(label="الرقم الضريبي", required=False)
    commercial_number = forms.CharField(label="السجل التجاري", required=False)
    
    owner_username = forms.CharField(max_length=150, label="اسم مستخدم المدير", widget=forms.TextInput(attrs={"placeholder": "مثال: admin"}))
    owner_email = forms.EmailField(label="البريد الإلكتروني للمدير", widget=forms.EmailInput(attrs={"placeholder": "admin@email.com"}))
    password1 = forms.CharField(label="كلمة المرور", widget=forms.PasswordInput(attrs={"placeholder": "••••••••"}))
    password2 = forms.CharField(label="تأكيد كلمة المرور", widget=forms.PasswordInput(attrs={"placeholder": "••••••••"}))

    class Meta:
        model = Company  
        # تم إزالة الحقول الإضافية من هنا لتفادي الـ FieldError القاتل
        fields = [
            'name', 'name_en', 'country'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # هنا يتم ترتيب الحقول لتظهر في الـ HTML بالتنسيق المطلوب كاملاً
        field_order = [
            'name', 'name_en', 'tax_number', 'commercial_number', 'country',
            'owner_username', 'owner_email', 'password1', 'password2'
        ]
        self.order_fields(field_order)
        
        for field_name, field in self.fields.items():
            existing_class = field.widget.attrs.get("class", "")
            if "form-control" not in existing_class:
                field.widget.attrs.update({"class": f"form-control {existing_class}".strip()})

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
    def save(self, commit=True):
        chosen_country = self.cleaned_data.get("country")
        if not chosen_country:
            chosen_country = "المملكة العربية السعودية"

        # إنشاء سجل الشركة وحفظ الحقول الحقيقية بدقة من البيانات الـ Cleaned
        company_instance = Company.objects.create(
            name=str(self.cleaned_data.get("name") or "شركة جديدة").strip(),
            name_en=str(self.cleaned_data.get("name_en", "")).strip(),
            vat_no=str(self.cleaned_data.get("tax_number", "")).strip(),
            commercial_record=str(self.cleaned_data.get("commercial_number", "")).strip(),
            country=str(chosen_country).strip()
        )

        main_branch = Branch.objects.create(company=company_instance, name="الفرع الرئيسي")
        
        user = User.objects.create_user(
            username=self.cleaned_data["owner_username"].strip(),
            email=self.cleaned_data["owner_email"].strip(),
            password=self.cleaned_data["password1"],
        )
        
        profile = user.profile
        profile.company = company_instance
        profile.branch = main_branch
        profile.role = "owner"
        profile.save()
        
        company_instance.created_user_cache = user
        
        return company_instance