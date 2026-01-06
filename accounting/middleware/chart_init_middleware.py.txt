from accounting.models import Account
from accounting.services.chart_builder import build_default_chart


class EnsureChartExistsMiddleware:
    """
    يتأكد أن شجرة الحسابات موجودة عند أول تشغيل للنظام
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not Account.objects.exists():
            build_default_chart()
        return self.get_response(request)
