
from functools import lru_cache

from django import template
from django.utils.translation import get_language

register = template.Library()


@lru_cache(maxsize=2000)
def translate_product_text(name):
    """Translate Arabic product/category names locally and cache results."""

    if not name:
        return name

    try:
        import argostranslate.translate

        translated = argostranslate.translate.translate(
            str(name),
            "ar",
            "en",
        )

        return translated or name

    except Exception:
        return name


@register.filter
def product_display_name(product):
    """Display product name in the current language."""

    language = (get_language() or "ar").lower()

    if not product:
        return ""

    # إذا وصل نص عادي بدل كائن المنتج
    if isinstance(product, str):
        if language.startswith("ar"):
            return product

        return translate_product_text(product)

    # اللغة العربية
    if language.startswith("ar"):
        return (
            getattr(product, "name_ar", "")
            or getattr(product, "name", "")
            or ""
        )

    # استخدام الاسم الإنجليزي المحفوظ أولاً
    english_name = getattr(product, "name_en", "")

    if english_name:
        return english_name

    # إذا لم يوجد اسم إنجليزي، ترجمة الاسم العربي
    original_name = (
        getattr(product, "name_ar", "")
        or getattr(product, "name", "")
        or ""
    )

    return translate_product_text(str(original_name))


@register.filter
def category_display_name(name):
    """Display category, customer, or other text in current language."""

    language = (get_language() or "ar").lower()

    if not name:
        return ""

    if language.startswith("en"):
        return translate_product_text(str(name))

    return name
