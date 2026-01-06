from django.conf import settings

def available_languages(request):
    return {
        "LANGUAGES": settings.LANGUAGES
    }
