
from functools import lru_cache

from django import template
from django.utils.translation import get_language

register = template.Library()


def is_arabic_language():
    return (get_language() or "ar").lower().startswith("ar")


def detect_text_language(value):
    """Detect whether text contains Arabic characters."""

    for char in str(value):
        if (
            "\u0600" <= char <= "\u06FF"
            or "\u0750" <= char <= "\u077F"
            or "\u08A0" <= char <= "\u08FF"
        ):
            return "ar"

    return "en"


@lru_cache(maxsize=10000)
def translate_text_cached(value, source_language, target_language):
    """Translate and cache text in either direction."""

    try:
        import argostranslate.translate

        translated = argostranslate.translate.translate(
            value,
            source_language,
            target_language,
        )

        return translated.strip() if translated else value

    except Exception:
        return value


def translate_to_current_language(value):
    """Automatically translate text into the selected language."""

    if not value:
        return ""

    value = str(value).strip()

    if not value:
        return ""

    target_language = "ar" if is_arabic_language() else "en"
    source_language = detect_text_language(value)

    if source_language == target_language:
        return value

    return translate_text_cached(
        value,
        source_language,
        target_language,
    )


@lru_cache(maxsize=10000)
def translate_store_name(name):
    """Translate store names from Arabic to English."""

    if not name:
        return ""

    return translate_to_current_language(name)


@register.filter
def store_display_name(name):
    """Display the store name in the selected language."""

    if not name:
        return ""

    name = str(name).strip()

    if name.startswith("متجر "):
        name = name[5:].strip()

    return translate_to_current_language(name)


@register.filter
def store_product_name(product):
    """Translate product names automatically in both directions."""

    if not product:
        return ""

    name_ar = getattr(product, "name_ar", None)
    name_en = getattr(product, "name_en", None)
    name = getattr(product, "name", None)

    if is_arabic_language():
        original_name = name_ar or name or name_en
    else:
        original_name = name_en or name_ar or name

    return translate_to_current_language(original_name)


@register.filter
def store_category_name(category):
    """Translate category names automatically in both directions."""

    if not category:
        return ""

    name = getattr(category, "name", "") or ""

    return translate_to_current_language(name)


@register.filter
def store_translate(value):
    """Translate any dynamic text into the selected language."""

    return translate_to_current_language(value)
