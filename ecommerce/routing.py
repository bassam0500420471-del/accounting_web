from django.urls import re_path

from .consumers import StoreNotificationConsumer


websocket_urlpatterns = [

    re_path(
        r"ws/store/notifications/$",
        StoreNotificationConsumer.as_asgi(),
    ),

]