from modeltranslation.translator import register, TranslationOptions
from .models import Account


@register(Account)
class AccountTranslationOptions(TranslationOptions):
    fields = ("name",)