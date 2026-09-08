import os

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "accounting_web_project.settings"
)

from django.core.asgi import get_asgi_application


# ==========================================================
# Django HTTP Application
# ==========================================================

django_asgi_app = get_asgi_application()


# ==========================================================
# النظام القديم لـ WebSocket
#
# معطل مؤقتًا — سيتم استبداله بخدمة بشر
#
# الكود محفوظ للرجوع إليه لاحقًا
# ==========================================================

# from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.auth import AuthMiddlewareStack
# import ecommerce.routing


# ==========================================================
# التطبيق الحالي
#
# HTTP يعمل بشكل طبيعي
# WebSocket القديم معطل
# ==========================================================

application = django_asgi_app


# ==========================================================
# النظام القديم — محفوظ للرجوع إليه لاحقًا
# ==========================================================

# application = ProtocolTypeRouter({
#
#     "http": django_asgi_app,
#
#     "websocket": AuthMiddlewareStack(
#
#         URLRouter(
#             ecommerce.routing.websocket_urlpatterns
#         )
#
#     ),
#
# })