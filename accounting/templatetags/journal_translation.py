import re

from django import template
from django.utils.translation import get_language

register = template.Library()


@register.filter
def journal_description(value):

    if not value:
        return ""

    language = (get_language() or "ar").lower()

    # لا نترجم الوصف عند اختيار العربية
    if not language.startswith("en"):
        return value

    text = str(value).strip()

    # قيد فاتورة POS
    match = re.fullmatch(
        r"قيد فاتورة POS رقم\s*(\d+)",
        text
    )

    if match:
        return f"POS Invoice Entry No. {match.group(1)}"

    # سند قبض
    match = re.fullmatch(
        r"سند قبض رقم\s*(\d+)\s*-\s*(.+)",
        text
    )

    if match:
        return (
            f"Receipt Voucher No. {match.group(1)}"
            f" - {match.group(2)}"
        )

    # أي وصف آخر يبقى كما هو
    return value