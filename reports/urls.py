from django.urls import path

from .views.dashboard import reports_dashboard
from .views.income_statement import income_statement
from .views.account_ledger import account_ledger
from .views.balance_sheet import balance_sheet
from .views.trial_balance import trial_balance
from .views.cash_flow import cash_flow

from .views.vat_report import vat_report                       # تقرير VAT (ملخص)
from .views.sales_vat_report import sales_vat_report           # تقرير المبيعات الضريبية
from .views.purchase_vat_report import purchase_vat_report     # تقرير المشتريات الضريبية
from .views.vat_rate_report import vat_rate_report             # 🆕 تقرير الضريبة حسب النسبة

app_name = "reports"

urlpatterns = [

    # 📊 لوحة التقارير
    path("", reports_dashboard, name="dashboard"),

    # 📄 قائمة الدخل
    path("income-statement/", income_statement, name="income_statement"),

    # 📘 كشف الحساب
    path("account-ledger/", account_ledger, name="account_ledger"),

    # 📊 الميزانية العمومية
    path("balance-sheet/", balance_sheet, name="balance_sheet"),

    # 📑 ميزان المراجعة
    path("trial-balance/", trial_balance, name="trial_balance"),

    # 💰 قائمة التدفقات النقدية
    path("cash-flow/", cash_flow, name="cash_flow"),

    # 🧾 تقرير ضريبة القيمة المضافة (ملخص نهائي)
    path("vat-report/", vat_report, name="vat_report"),

    # 📊 تقرير المبيعات الضريبية
    path(
        "sales-vat-report/",
        sales_vat_report,
        name="sales_vat_report"
    ),

    # 📊 تقرير المشتريات الضريبية
    path(
        "purchase-vat-report/",
        purchase_vat_report,
        name="purchase_vat_report"
    ),

    # 📊🆕 تقرير تفصيلي لضريبة القيمة المضافة حسب النسبة
    path(
        "vat-rate-report/",
        vat_rate_report,
        name="vat_rate_report"
    ),
]
