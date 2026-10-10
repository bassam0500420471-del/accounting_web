"""
ZATCA Invoice Validator
=======================

فحص أساسي لملف XML الخاص بالفاتورة قبل إرساله إلى ZATCA.

هذا الملف لا يقوم بإرسال الفاتورة إلى الهيئة.
وظيفته التأكد من:
- وجود XML صالح
- وجود العناصر الأساسية
- عدم وجود بيانات فارغة مهمة
- إمكانية قراءة XML بدون أخطاء
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any
from xml.etree import ElementTree as ET


@dataclass
class ValidationResult:
    """
    نتيجة فحص الفاتورة.
    """

    valid: bool
    errors: list[str]
    warnings: list[str]

    def __bool__(self) -> bool:
        return self.valid

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def _local_name(tag: str) -> str:
    """
    إزالة namespace من اسم XML.
    مثال:
        {namespace}Invoice
    تصبح:
        Invoice
    """
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]

    return tag


def _find(root: ET.Element, name: str) -> ET.Element | None:
    """
    البحث عن عنصر XML بالاسم بدون الاعتماد على namespace.
    """
    for element in root.iter():
        if _local_name(element.tag) == name:
            return element

    return None


def _find_all(root: ET.Element, name: str) -> list[ET.Element]:
    """
    إرجاع جميع العناصر التي تحمل الاسم المطلوب.
    """
    return [
        element
        for element in root.iter()
        if _local_name(element.tag) == name
    ]


def _text(element: ET.Element | None) -> str:
    """
    استخراج النص من عنصر XML.
    """
    if element is None:
        return ""

    return (element.text or "").strip()


def _decimal(value: str) -> Decimal | None:
    """
    تحويل قيمة XML إلى Decimal.
    """
    if not value:
        return None

    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


def validate_invoice_xml(
    xml_content: str | bytes,
    *,
    strict: bool = False,
) -> ValidationResult:
    """
    فحص XML الخاص بالفاتورة.

    Args:
        xml_content:
            محتوى XML كنص أو bytes.

        strict:
            إذا كان True يتم التعامل مع بعض التحذيرات كأخطاء.

    Returns:
        ValidationResult
    """

    errors: list[str] = []
    warnings: list[str] = []

    if xml_content is None:
        return ValidationResult(
            valid=False,
            errors=["XML invoice is empty."],
            warnings=[],
        )

    if isinstance(xml_content, bytes):
        if not xml_content.strip():
            return ValidationResult(
                valid=False,
                errors=["XML invoice is empty."],
                warnings=[],
            )
    else:
        if not xml_content.strip():
            return ValidationResult(
                valid=False,
                errors=["XML invoice is empty."],
                warnings=[],
            )

    # =========================================================
    # قراءة XML
    # =========================================================

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        return ValidationResult(
            valid=False,
            errors=[f"Invalid XML: {exc}"],
            warnings=[],
        )

    # =========================================================
    # يجب أن تكون الفاتورة UBL Invoice
    # =========================================================

    root_name = _local_name(root.tag)

    if root_name != "Invoice":
        errors.append(
            f"Root XML element must be Invoice, found: {root_name}"
        )

    # =========================================================
    # UBLVersionID
    # =========================================================

    ubl_version = _find(root, "UBLVersionID")

    if ubl_version is None:
        warnings.append("UBLVersionID is missing.")
    elif not _text(ubl_version):
        errors.append("UBLVersionID is empty.")

    # =========================================================
    # CustomizationID
    # =========================================================

    customization = _find(root, "CustomizationID")

    if customization is None:
        warnings.append("CustomizationID is missing.")
    elif not _text(customization):
        errors.append("CustomizationID is empty.")

    # =========================================================
    # ProfileID
    # =========================================================

    profile = _find(root, "ProfileID")

    if profile is None:
        warnings.append("ProfileID is missing.")
    elif not _text(profile):
        errors.append("ProfileID is empty.")

    # =========================================================
    # Invoice ID
    # =========================================================

    invoice_id = _find(root, "ID")

    if invoice_id is None:
        errors.append("Invoice ID is missing.")
    elif not _text(invoice_id):
        errors.append("Invoice ID is empty.")

    # =========================================================
    # IssueDate
    # =========================================================

    issue_date = _find(root, "IssueDate")

    if issue_date is None:
        errors.append("IssueDate is missing.")
    elif not _text(issue_date):
        errors.append("IssueDate is empty.")

    # =========================================================
    # InvoiceTypeCode
    # =========================================================

    invoice_type = _find(root, "InvoiceTypeCode")

    if invoice_type is None:
        errors.append("InvoiceTypeCode is missing.")
    elif not _text(invoice_type):
        errors.append("InvoiceTypeCode is empty.")

    # =========================================================
    # DocumentCurrencyCode
    # =========================================================

    currency = _find(root, "DocumentCurrencyCode")

    if currency is None:
        warnings.append("DocumentCurrencyCode is missing.")
    elif not _text(currency):
        errors.append("DocumentCurrencyCode is empty.")

    # =========================================================
    # AccountingSupplierParty
    # =========================================================

    supplier = _find(root, "AccountingSupplierParty")

    if supplier is None:
        errors.append("AccountingSupplierParty is missing.")

    # =========================================================
    # AccountingCustomerParty
    # =========================================================

    customer = _find(root, "AccountingCustomerParty")

    if customer is None:
        warnings.append("AccountingCustomerParty is missing.")

    # =========================================================
    # TaxTotal
    # =========================================================

    tax_totals = _find_all(root, "TaxTotal")

    if not tax_totals:
        warnings.append("TaxTotal is missing.")

    # =========================================================
    # LegalMonetaryTotal
    # =========================================================

    monetary_total = _find(root, "LegalMonetaryTotal")

    if monetary_total is None:
        errors.append("LegalMonetaryTotal is missing.")

    # =========================================================
    # Invoice Lines
    # =========================================================

    invoice_lines = _find_all(root, "InvoiceLine")

    if not invoice_lines:
        errors.append("Invoice must contain at least one InvoiceLine.")

    # =========================================================
    # فحص كل InvoiceLine
    # =========================================================

    for index, line in enumerate(invoice_lines, start=1):

        line_id = _find(line, "ID")

        if line_id is None or not _text(line_id):
            warnings.append(
                f"InvoiceLine {index}: ID is missing."
            )

        quantity = _find(line, "InvoicedQuantity")

        if quantity is None:
            errors.append(
                f"InvoiceLine {index}: InvoicedQuantity is missing."
            )
        else:
            quantity_value = _decimal(_text(quantity))

            if quantity_value is None:
                errors.append(
                    f"InvoiceLine {index}: invalid quantity."
                )
            elif quantity_value <= Decimal("0"):
                errors.append(
                    f"InvoiceLine {index}: quantity must be greater than zero."
                )

        line_extension = _find(line, "LineExtensionAmount")

        if line_extension is None:
            warnings.append(
                f"InvoiceLine {index}: LineExtensionAmount is missing."
            )
        else:
            amount = _decimal(_text(line_extension))

            if amount is None:
                errors.append(
                    f"InvoiceLine {index}: invalid LineExtensionAmount."
                )

        item = _find(line, "Item")

        if item is None:
            errors.append(
                f"InvoiceLine {index}: Item is missing."
            )

        price = _find(line, "Price")

        if price is None:
            errors.append(
                f"InvoiceLine {index}: Price is missing."
            )

    # =========================================================
    # فحص إجمالي الفاتورة
    # =========================================================

    if monetary_total is not None:

        payable = _find(monetary_total, "PayableAmount")

        if payable is None:
            warnings.append(
                "PayableAmount is missing from LegalMonetaryTotal."
            )
        else:
            payable_value = _decimal(_text(payable))

            if payable_value is None:
                errors.append(
                    "PayableAmount contains an invalid decimal value."
                )
            elif payable_value < Decimal("0"):
                errors.append(
                    "PayableAmount cannot be negative."
                )

    # =========================================================
    # فحص VAT
    # =========================================================

    for tax_total in tax_totals:

        tax_amount = _find(tax_total, "TaxAmount")

        if tax_amount is not None:

            tax_value = _decimal(_text(tax_amount))

            if tax_value is None:
                errors.append(
                    "TaxAmount contains an invalid decimal value."
                )
            elif tax_value < Decimal("0"):
                errors.append(
                    "TaxAmount cannot be negative."
                )

    # =========================================================
    # Strict Mode
    # =========================================================

    if strict and warnings:
        errors.extend(
            f"Strict validation: {warning}"
            for warning in warnings
        )

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_xml(xml_content: str | bytes, strict: bool = False) -> bool:
    """
    دالة بسيطة للتوافق مع الاستدعاءات المباشرة.

    ترجع True إذا كان XML صالحاً،
    وFalse إذا كان يحتوي على أخطاء.
    """

    result = validate_invoice_xml(
        xml_content,
        strict=strict,
    )

    return result.valid


def validate_invoice(xml_content: str | bytes) -> ValidationResult:
    """
    Alias للاستخدام من بقية المشروع.
    """

    return validate_invoice_xml(xml_content)


def get_validation_errors(
    xml_content: str | bytes,
) -> list[str]:
    """
    إرجاع أخطاء الفحص فقط.
    """

    return validate_invoice_xml(xml_content).errors