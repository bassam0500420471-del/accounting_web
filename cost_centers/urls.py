from django.urls import path
from . import views

urlpatterns = [
    path("", views.cost_centers_list, name="cost_centers_list"),
    path("add/", views.cost_center_add, name="cost_center_add"),
    path("tree/", views.cost_centers_tree, name="cost_centers_tree"),

    path("ajax/add-parent/", views.cost_center_add_ajax, name="cost_center_add_ajax"),
    path("ajax/add-branch/", views.branch_add_ajax, name="branch_add_ajax"),

    # 🔍 APIs للفواتير
    path("all/", views.cost_centers_all, name="cost_centers_all"),
    path("search/", views.cost_centers_search, name="cost_centers_search"),
]
