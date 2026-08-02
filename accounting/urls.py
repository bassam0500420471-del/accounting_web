from django.urls import path

from accounting.views.chart_views import (
    chart_tree_page,
    chart_tree_api,
)

from accounting.views.account_views import (
    journals_list,
    journal_add,
    journal_view,
    journal_post,
    account_view,
    account_ledger,
    add_child_account,
    account_edit,
    account_delete,
)

app_name = "accounting"

urlpatterns = [

    # =========================
    # 🌳 شجرة الحسابات
    # =========================
    path("chart/", chart_tree_page, name="chart_tree"),
    path("api/chart/", chart_tree_api, name="chart_tree_api"),


    # =========================
    # 📘 القيود اليومية
    # =========================
    path("journals/", journals_list, name="journals_list"),
    path("journals/add/", journal_add, name="journal_add"),
    path("journals/<int:pk>/", journal_view, name="journal_view"),
    path("journals/<int:pk>/post/", journal_post, name="journal_post"),


    # =========================
    # 👁️ عرض الحساب
    # =========================
    path(
        "accounts/<int:pk>/view/",
        account_view,
        name="account_view",
    ),


    # =========================
    # ✏️ تعديل الحساب
    # =========================
    path(
        "accounts/<int:pk>/edit/",
        account_edit,
        name="account_edit",
    ),


    # =========================
    # 🗑️ حذف الحساب
    # =========================
    path(
        "accounts/<int:pk>/delete/",
        account_delete,
        name="account_delete",
    ),


    # =========================
    # 📊 حركة الحساب
    # =========================
    path(
        "accounts/<int:pk>/ledger/",
        account_ledger,
        name="account_ledger",
    ),


    # =========================
    # ➕ إضافة حساب فرعي
    # =========================
    path(
        "accounts/<int:pk>/add-child/",
        add_child_account,
        name="add_child_account",
    ),
]