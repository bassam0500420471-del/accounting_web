from django.urls import path
from . import views


urlpatterns = [

    # =========================================================
    # قائمة مراكز التكلفة
    # =========================================================
    path(
        "",
        views.cost_centers_list,
        name="cost_centers_list"
    ),

    # =========================================================
    # إضافة مركز تكلفة
    # =========================================================
    path(
        "add/",
        views.cost_center_add,
        name="cost_center_add"
    ),

    # =========================================================
    # شجرة مراكز التكلفة
    # =========================================================
    path(
        "tree/",
        views.cost_centers_tree,
        name="cost_centers_tree"
    ),

    # =========================================================
    # AJAX - إضافة مركز رئيسي
    # =========================================================
    path(
        "ajax/add-parent/",
        views.cost_center_add_ajax,
        name="cost_center_add_ajax"
    ),

    # =========================================================
    # AJAX - إضافة فرع
    # =========================================================
    path(
        "ajax/add-branch/",
        views.branch_add_ajax,
        name="branch_add_ajax"
    ),

    # =========================================================
    # APIs للفواتير
    # =========================================================
    path(
        "all/",
        views.cost_centers_all,
        name="cost_centers_all"
    ),

    path(
        "search/",
        views.cost_centers_search,
        name="cost_centers_search"
    ),

    # =========================================================
    # عرض مركز تكلفة
    # =========================================================
    path(
        "<int:cost_center_id>/",
        views.cost_center_detail,
        name="cost_center_detail"
    ),

    # =========================================================
    # تعديل مركز تكلفة
    # =========================================================
    path(
        "<int:cost_center_id>/edit/",
        views.cost_center_edit,
        name="cost_center_edit"
    ),

    # =========================================================
    # إضافة مركز تكلفة فرعي
    # =========================================================
    path(
        "<int:parent_id>/add-child/",
        views.cost_center_add_child,
        name="cost_center_add_child"
    ),
]