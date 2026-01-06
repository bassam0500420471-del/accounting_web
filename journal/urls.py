from django.urls import path
from . import views

urlpatterns = [
    path("", views.journal_list, name="journal_list"),
    path("add/", views.journal_add, name="journal_add"),
    path("<int:pk>/", views.journal_view, name="journal_view"),
    path("<int:pk>/edit/", views.journal_edit, name="journal_edit"),
    path("<int:pk>/delete/", views.journal_delete, name="journal_delete"),
]
