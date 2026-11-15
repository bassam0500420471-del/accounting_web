
from functools import lru_cache

from django import template
from django.utils.translation import get_language

register = template.Library()


@lru_cache(maxsize=1000)
def translate_supplier_name(name):
    """Translate supplier name locally and cache the result."""
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
        # Keep the original name if translation is unavailable.
        return name


@register.filter
def supplier_name(name):
    language = get_language() or "ar"

    if language.lower().startswith("en"):
        return translate_supplier_name(str(name))

    return name
