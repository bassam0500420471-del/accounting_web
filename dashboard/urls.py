from django.urls import path
from .views import home_dashboard

urlpatterns = [
    path("", home_dashboard, name="home"),
]
