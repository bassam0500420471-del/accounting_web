from django import forms
from .models import Customer

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = "__all__"

        widgets = {
            'customer_type': forms.Select(attrs={'class': 'form-select', 'id': 'customer_type'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
'attachment': forms.ClearableFileInput(attrs={'class': 'form-control'}),

            'street1': forms.TextInput(attrs={'class': 'form-control'}),
            'street2': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'zipcode': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),

            'tax_number': forms.TextInput(attrs={'class': 'form-control', 'id': 'tax_number'}),
            'cr_number': forms.TextInput(attrs={'class': 'form-control', 'id': 'cr_number'}),

            'notes': forms.Textarea(attrs={'class': 'form-control'}),
        }
	