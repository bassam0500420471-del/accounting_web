
from functools import lru_cache

from django import template
from django.utils.translation import get_language

register = template.Library()


@lru_cache(maxsize=5000)
def translate_store_name(name):
    """Translate Arabic store names to English using Argos."""

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
def store_product_name(product):
    """Display the product name in the current language."""

    if not product:
        return ""

    language = (get_language() or "ar").lower()

    if language.startswith("ar"):
        return (
            getattr(product, "name_ar", None)
            or getattr(product, "name", None)
            or ""
        )

    english_name = getattr(product, "name_en", None)

    if english_name and english_name.strip():
        return english_name

    original_name = (
        getattr(product, "name_ar", None)
        or getattr(product, "name", None)
        or ""
    )

    return translate_store_name(original_name)


@register.filter
def store_category_name(category):
    """Display the category name in the current language."""

    if not category:
        return ""

    name = getattr(category, "name", "") or ""

    language = (get_language() or "ar").lower()

    if language.startswith("ar"):
        return name

    return translate_store_name(name)
