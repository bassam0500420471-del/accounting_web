from django.urls import path
from . import views


urlpatterns = [
    path("chat/", views.chat, name="chat"),

    path(
        "conversations/",
        views.conversations,
        name="conversations",
    ),

    path(
        "conversations/<int:conversation_id>/",
        views.conversation_messages,
        name="conversation_messages",
    ),
]