from django import forms
from .models import Customer


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        exclude = ["company", "account"]

        widgets = {
            "customer_type": forms.Select(attrs={"class": "form-select", "id": "customer_type"}),
            "commercial_name": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "mobile": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "attachment": forms.ClearableFileInput(attrs={"class": "form-control"}),

# ... (باقي الكود كما هو)
            "address": forms.TextInput(attrs={"class": "form-control"}),
            # أضف هذا السطر أدناه:
            "address_en": forms.TextInput(attrs={"class": "form-control"}), 
            "street": forms.TextInput(attrs={"class": "form-control"}),
# ... (باقي الكود كما هو)
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "region": forms.TextInput(attrs={"class": "form-control"}),
            "postal_code": forms.TextInput(attrs={"class": "form-control"}),
            "country": forms.TextInput(attrs={"class": "form-control"}),

            "tax_number": forms.TextInput(attrs={"class": "form-control", "id": "tax_number"}),
            "cr_number": forms.TextInput(attrs={"class": "form-control", "id": "cr_number"}),

            "category": forms.TextInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }