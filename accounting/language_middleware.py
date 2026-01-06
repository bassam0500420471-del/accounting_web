from django.utils import translation
from app_settings.models import SystemSettings

class SettingsLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # محاولة جلب لغة النظام من قاعدة البيانات
        try:
            settings = SystemSettings.objects.first()
            if settings and settings.language:
                translation.activate(settings.language)
                request.LANGUAGE_CODE = settings.language
        except:
            pass

        response = self.get_response(request)
        return response
