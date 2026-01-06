from django import forms
from .models import JournalEntry, JournalLine
from accounting.models import Account


class JournalEntryForm(forms.ModelForm):
    class Meta:
        model = JournalEntry
        fields = ["date", "description"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "description": forms.TextInput(attrs={"class": "form-control"}),
        }


class JournalLineForm(forms.ModelForm):
    class Meta:
        model = JournalLine
        fields = ["account", "debit", "credit"]
        widgets = {
            "account": forms.Select(attrs={"class": "form-select"}),
            "debit": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "credit": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }
