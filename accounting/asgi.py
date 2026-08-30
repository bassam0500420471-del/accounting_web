import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application

import ecommerce.routing


os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "accounting_web_project.settings"
)


django_asgi_app = get_asgi_application()


application = ProtocolTypeRouter({

    "http": django_asgi_app,

    "websocket": AuthMiddlewareStack(

        URLRouter(
            ecommerce.routing.websocket_urlpatterns
        )

    ),

})